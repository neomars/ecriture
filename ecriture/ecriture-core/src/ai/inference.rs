//! Real local inference via llama.cpp, through the `llama-cpp-2` bindings -
//! the same underlying engine the original Python app drives via
//! `llama-cpp-python`.
//!
//! `LlamaBackend` and `LlamaContext` are not `Send`, and llama.cpp only
//! supports initializing its backend once per process, so all of this
//! module's actual llama.cpp calls happen on one dedicated worker thread
//! that lives for as long as the engine does. [`LlamaEngine`] is just a
//! `Sender` handle other threads can clone/share freely; [`LlamaEngine::load`]
//! spawns the worker and waits for the initial model load to report success
//! or failure before returning, so a bad model file surfaces immediately
//! rather than on the first chat request.
//!
//! See `crate::ai` module docs for why this file's logic could not be
//! exercised against a real model in this environment: the low-level
//! llama.cpp call sequence (tokenize → batch → decode → sample loop) is
//! copied from `llama-cpp-2`'s own official `examples/simple`, and the
//! chat-formatting step uses the model's own embedded GGUF chat template
//! via `LlamaModel::apply_chat_template` rather than a hand-rolled Gemma
//! prompt format, specifically to lean on llama.cpp's own tested behavior
//! wherever possible.

use crate::ai::{AiBackend, ChatMessage};
use llama_cpp_2::context::params::LlamaContextParams;
use llama_cpp_2::llama_backend::LlamaBackend;
use llama_cpp_2::llama_batch::LlamaBatch;
use llama_cpp_2::model::params::LlamaModelParams;
use llama_cpp_2::model::{AddBos, LlamaChatMessage, LlamaModel};
use llama_cpp_2::sampling::LlamaSampler;
use llama_cpp_2::token::LlamaToken;
use std::num::NonZeroU32;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{Receiver, Sender};

#[derive(Debug, thiserror::Error)]
pub enum InferenceError {
    #[error("failed to initialize the llama.cpp backend: {0}")]
    Backend(String),
    #[error("failed to load model '{path}': {reason}")]
    ModelLoad { path: PathBuf, reason: String },
    #[error("failed to create an inference context: {0}")]
    ContextInit(String),
    #[error("tokenization failed: {0}")]
    Tokenize(String),
    #[error("chat template error: {0}")]
    ChatTemplate(String),
    #[error("decode failed: {0}")]
    Decode(String),
    #[error("the inference worker thread is no longer running")]
    WorkerGone,
}

struct GenerateRequest {
    messages: Vec<ChatMessage>,
    temperature: f32,
    max_tokens: i32,
    respond_to: Sender<Result<String, InferenceError>>,
}

/// A handle to a running local Gemma engine. Cloning is cheap (it's just a
/// channel sender) and safe to share across threads/store in shared app
/// state; every clone talks to the same single worker thread.
#[derive(Clone)]
pub struct LlamaEngine {
    request_tx: Sender<GenerateRequest>,
}

impl LlamaEngine {
    /// Spawns the dedicated worker thread, loads `model_path` with a
    /// context window of `n_ctx` tokens, and blocks until that load
    /// finishes (successfully or not).
    pub fn load(model_path: impl AsRef<Path>, n_ctx: u32) -> Result<Self, InferenceError> {
        let model_path = model_path.as_ref().to_path_buf();
        let (ready_tx, ready_rx) = std::sync::mpsc::channel::<Result<(), InferenceError>>();
        let (request_tx, request_rx) = std::sync::mpsc::channel::<GenerateRequest>();

        std::thread::Builder::new()
            .name("ecriture-llama-engine".into())
            .spawn(move || run_engine_thread(model_path, n_ctx, &ready_tx, request_rx))
            .map_err(|e| InferenceError::Backend(e.to_string()))?;

        ready_rx.recv().map_err(|_| InferenceError::WorkerGone)??;
        Ok(Self { request_tx })
    }
}

impl AiBackend for LlamaEngine {
    fn generate_chat(&self, messages: &[ChatMessage], temperature: f32) -> Result<String, String> {
        let (respond_to, response_rx) = std::sync::mpsc::channel();
        self.request_tx
            .send(GenerateRequest {
                messages: messages.to_vec(),
                temperature,
                max_tokens: 512, // matches ai_client.py's create_chat_completion max_tokens
                respond_to,
            })
            .map_err(|_| "inference worker is not running".to_string())?;

        response_rx
            .recv()
            .map_err(|_| "inference worker dropped the response channel".to_string())?
            .map_err(|e| e.to_string())
    }
}

/// Requests as many transformer layers as possible be offloaded to a GPU.
/// This is harmless on a CPU-only build (no `cuda`/`rocm`/`metal`/`vulkan`
/// Cargo feature enabled): with no GPU backend compiled in, llama.cpp finds
/// no GPU device to offload to and silently runs entirely on CPU regardless
/// of this value. Gemma-2-2b has far fewer than 1000 layers, so this
/// offloads the whole model whenever a big-enough GPU *is* available (see
/// [`gpu_memory_needed`]).
const GPU_LAYERS_ALL: u32 = 1000;

const MIB: usize = 1024 * 1024;

/// GPU memory, in bytes, needed to run the whole model on a GPU: the model
/// weights plus the context - KV cache (Gemma-2-2b: 26 layers x 4 KV heads
/// x 256 dims x K+V x f16 = ~104 KiB per token, rounded up to 128 KiB) and
/// ~512 MiB of compute buffers and driver overhead. Running out of GPU
/// memory mid-generation makes the GPU driver abort the whole process, so
/// a GPU that can't fit all of this is not used at all (CPU is slower but
/// doesn't crash).
fn gpu_memory_needed(model_bytes: u64, n_ctx: u32) -> usize {
    model_bytes as usize + n_ctx as usize * 128 * 1024 + 512 * MIB
}

fn is_gpu(device_type: llama_cpp_2::LlamaBackendDeviceType) -> bool {
    matches!(
        device_type,
        llama_cpp_2::LlamaBackendDeviceType::Gpu | llama_cpp_2::LlamaBackendDeviceType::IntegratedGpu
    )
}

/// Memory actually available on a device: what's free right now (the
/// desktop and other apps already use part of it), or the total if the
/// driver doesn't report free memory.
fn available_memory(device: &llama_cpp_2::LlamaBackendDevice) -> usize {
    if device.memory_free > 0 {
        device.memory_free
    } else {
        device.memory_total
    }
}

/// ggml device indices of the GPUs with at least `needed` bytes available,
/// to be passed to [`LlamaModelParams::with_devices`].
fn qualifying_gpus(devices: &[llama_cpp_2::LlamaBackendDevice], needed: usize) -> Vec<usize> {
    devices
        .iter()
        .filter(|d| is_gpu(d.device_type) && available_memory(d) >= needed)
        .map(|d| d.index)
        .collect()
}

/// Logs every ggml backend device found (see the README's GPU
/// acceleration section) and returns the GPUs to offload the model to (see
/// [`qualifying_gpus`]). An empty list leaves the model on CPU.
fn log_backend_devices_and_pick_gpus(needed: usize) -> Vec<usize> {
    let devices = llama_cpp_2::list_llama_ggml_backend_devices();
    let gpu_count = devices.iter().filter(|d| is_gpu(d.device_type)).count();
    let qualifying = qualifying_gpus(&devices, needed);

    eprintln!(
        "[ai] ggml backend devices ({} found, {gpu_count} GPU); the model needs {} MiB of GPU memory:",
        devices.len(),
        needed / MIB
    );
    for d in &devices {
        let too_small = is_gpu(d.device_type) && available_memory(d) < needed;
        eprintln!(
            "[ai]   [{}] {} ({}) via {} - {:?}, {} MiB free / {} MiB total{}",
            d.index,
            d.name,
            d.description,
            d.backend,
            d.device_type,
            d.memory_free / MIB,
            d.memory_total / MIB,
            if too_small { " (not enough free memory - will not be used)" } else { "" },
        );
    }
    if gpu_count == 0 {
        eprintln!(
            "[ai] no GPU backend compiled in (or no GPU detected) - running on CPU. \
             See README for how to enable GPU acceleration for your hardware."
        );
    } else if qualifying.is_empty() {
        eprintln!("[ai] no GPU has enough free memory for the model and its context - running on CPU instead.");
    } else {
        eprintln!("[ai] running on GPU device(s) {qualifying:?}");
    }
    qualifying
}

fn run_engine_thread(
    model_path: PathBuf,
    n_ctx: u32,
    ready_tx: &Sender<Result<(), InferenceError>>,
    request_rx: Receiver<GenerateRequest>,
) {
    let loaded = LlamaBackend::init()
        .map_err(|e| InferenceError::Backend(e.to_string()))
        .and_then(|backend| {
            let model_bytes = std::fs::metadata(&model_path).map(|m| m.len()).unwrap_or(0);
            let qualifying_gpus = log_backend_devices_and_pick_gpus(gpu_memory_needed(model_bytes, n_ctx));
            let n_gpu_layers = if qualifying_gpus.is_empty() { 0 } else { GPU_LAYERS_ALL };
            let mut model_params = LlamaModelParams::default().with_n_gpu_layers(n_gpu_layers);
            if !qualifying_gpus.is_empty() {
                // Restrict offload to the GPUs that actually passed the
                // memory check - without this, llama.cpp would still be
                // free to also try splitting across any GPU present
                // (including ones we just excluded for being too small).
                model_params = model_params
                    .with_devices(&qualifying_gpus)
                    .map_err(|e| InferenceError::Backend(e.to_string()))?;
            }
            let model = LlamaModel::load_from_file(&backend, &model_path, &model_params).map_err(|e| {
                InferenceError::ModelLoad {
                    path: model_path.clone(),
                    reason: e.to_string(),
                }
            })?;
            Ok((backend, model))
        });

    let (backend, model) = match loaded {
        Ok(pair) => {
            let _ = ready_tx.send(Ok(()));
            pair
        }
        Err(e) => {
            let _ = ready_tx.send(Err(e));
            return;
        }
    };

    for request in request_rx {
        let result = generate_once(
            &backend,
            &model,
            n_ctx,
            &request.messages,
            request.temperature,
            request.max_tokens,
        );
        let _ = request.respond_to.send(result);
    }
}

fn generate_once(
    backend: &LlamaBackend,
    model: &LlamaModel,
    n_ctx: u32,
    messages: &[ChatMessage],
    temperature: f32,
    max_tokens: i32,
) -> Result<String, InferenceError> {
    let ctx_params = LlamaContextParams::default().with_n_ctx(NonZeroU32::new(n_ctx));
    let mut ctx = model
        .new_context(backend, ctx_params)
        .map_err(|e| InferenceError::ContextInit(e.to_string()))?;

    // The prompt plus the answer must fit in the context window: shorten
    // the longest texts (a whole chapter, a long chat history...) until it
    // does. Without this, llama.cpp aborts the whole process.
    let prompt_budget = prompt_token_budget(n_ctx, max_tokens);
    let tokenize = |messages: &[ChatMessage]| -> Result<Vec<LlamaToken>, InferenceError> {
        let prompt = render_chat_prompt(model, messages)?;
        model
            .str_to_token(&prompt, AddBos::Always)
            .map_err(|e| InferenceError::Tokenize(e.to_string()))
    };
    let started = std::time::Instant::now();
    let tokens = fit_to_budget(messages, prompt_budget, tokenize)?;
    if tokens.is_empty() {
        return Ok(String::new());
    }
    eprintln!(
        "[ai] prompt: {} tokens (limit {prompt_budget}), answer: up to {max_tokens} tokens",
        tokens.len()
    );

    // llama.cpp also aborts if a single decode call gets more than n_batch
    // tokens, so feed the prompt in n_batch-sized chunks.
    let n_batch = ctx.n_batch().max(1) as usize;
    let mut batch = LlamaBatch::new(n_batch.max(1), 1);
    let last_index = (tokens.len() - 1) as i32;
    for (chunk_index, chunk) in tokens.chunks(n_batch).enumerate() {
        batch.clear();
        let start = (chunk_index * n_batch) as i32;
        for (i, token) in (start..).zip(chunk.iter().copied()) {
            batch
                .add(token, i, &[0], i == last_index)
                .map_err(|e| InferenceError::Decode(e.to_string()))?;
        }
        ctx.decode(&mut batch)
            .map_err(|e| InferenceError::Decode(e.to_string()))?;
    }

    let mut sampler = LlamaSampler::chain_simple([
        LlamaSampler::temp(temperature.max(0.01)),
        LlamaSampler::dist(rand::random()),
    ]);

    let mut n_cur = tokens.len() as i32;
    let end = n_cur + max_tokens;
    let mut decoder = encoding_rs::UTF_8.new_decoder();
    let mut output = String::new();

    while n_cur < end {
        let token = sampler.sample(&ctx, batch.n_tokens() - 1);
        sampler.accept(token);

        if model.is_eog_token(token) {
            break;
        }

        let piece = model
            .token_to_piece(token, &mut decoder, true, None)
            .map_err(|e| InferenceError::Decode(e.to_string()))?;
        output.push_str(&piece);

        batch.clear();
        batch
            .add(token, n_cur, &[0], true)
            .map_err(|e| InferenceError::Decode(e.to_string()))?;
        n_cur += 1;
        ctx.decode(&mut batch)
            .map_err(|e| InferenceError::Decode(e.to_string()))?;
    }

    eprintln!(
        "[ai] generated {} tokens in {:.1} s",
        n_cur - tokens.len() as i32,
        started.elapsed().as_secs_f32()
    );
    Ok(output.trim().to_string())
}

/// Renders the chat history into the final prompt string using the chat
/// template embedded in the GGUF file itself (Gemma's own
/// `<start_of_turn>`/`<end_of_turn>` format), rather than a hand-rolled
/// template - this is llama.cpp's own recommended approach and avoids
/// silently drifting from whatever template the specific downloaded
/// checkpoint actually expects.
fn render_chat_prompt(model: &LlamaModel, messages: &[ChatMessage]) -> Result<String, InferenceError> {
    let template = model
        .chat_template(None)
        .map_err(|e| InferenceError::ChatTemplate(e.to_string()))?;

    let llama_messages = messages
        .iter()
        .map(|m| LlamaChatMessage::new(m.role.clone(), m.content.clone()))
        .collect::<std::result::Result<Vec<_>, _>>()
        .map_err(|e| InferenceError::ChatTemplate(e.to_string()))?;

    model
        .apply_chat_template(&template, &llama_messages, true)
        .map_err(|e| InferenceError::ChatTemplate(e.to_string()))
}

/// Tokens left for the prompt once the answer (`max_tokens`) and a small
/// safety margin are reserved in the `n_ctx` context window.
fn prompt_token_budget(n_ctx: u32, max_tokens: i32) -> usize {
    (n_ctx as usize).saturating_sub(max_tokens.max(0) as usize + 32).max(64)
}

/// Marks the place where text was cut to fit the context window.
const ELISION: &str = "\n[…]\n";

/// Tokenizes `messages` with `tokenize`, shortening them until the result
/// fits in `budget` tokens: each round cuts the middle out of the longest
/// message (keeping its beginning and end, which usually carry the most
/// context - a scene's setup and its latest lines). Gives up shortening
/// after a few rounds and hard-truncates, so this always terminates with at
/// most `budget` tokens.
fn fit_to_budget<T, E>(
    messages: &[ChatMessage],
    budget: usize,
    tokenize: impl Fn(&[ChatMessage]) -> Result<Vec<T>, E>,
) -> Result<Vec<T>, E> {
    let mut messages = messages.to_vec();
    let mut tokens = tokenize(&messages)?;
    for _ in 0..8 {
        if tokens.len() <= budget {
            return Ok(tokens);
        }
        let total_chars: usize = messages.iter().map(|m| m.content.chars().count()).sum();
        let Some(longest) = messages.iter_mut().max_by_key(|m| m.content.chars().count()) else {
            break;
        };
        let len = longest.content.chars().count();
        // Estimate characters per token over the whole prompt and keep 5%
        // less than the estimate allows, so one or two rounds are usually
        // enough.
        let chars_per_token = total_chars.max(1) as f64 / tokens.len().max(1) as f64;
        let excess_chars = ((tokens.len() - budget) as f64 * chars_per_token).ceil() as usize + ELISION.len();
        if excess_chars >= len {
            longest.content = String::new();
        } else {
            let keep = ((len - excess_chars) as f64 * 0.95) as usize;
            let head: String = longest.content.chars().take(keep / 2).collect();
            let tail: String = longest.content.chars().skip(len - (keep - keep / 2)).collect();
            longest.content = format!("{head}{ELISION}{tail}");
        }
        tokens = tokenize(&messages)?;
    }
    if tokens.len() > budget {
        tokens.truncate(budget);
    }
    Ok(tokens)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn msg(role: &str, content: &str) -> ChatMessage {
        ChatMessage { role: role.into(), content: content.into() }
    }

    /// A stand-in tokenizer: one token per 4 characters, plus a few for
    /// the chat template around each message.
    fn fake_tokenize(messages: &[ChatMessage]) -> Result<Vec<u32>, ()> {
        let n: usize = messages.iter().map(|m| m.content.chars().count().div_ceil(4) + 5).sum();
        Ok(vec![0; n])
    }

    #[test]
    fn short_prompts_are_left_untouched() {
        let messages = [msg("system", "Be helpful."), msg("user", "Hello")];
        assert_eq!(fit_to_budget(&messages, 100, fake_tokenize).unwrap().len(), fake_tokenize(&messages).unwrap().len());
    }

    #[test]
    fn a_whole_novel_is_shortened_to_fit_the_budget() {
        let novel = "Il était une fois. ".repeat(200_000); // ~3.8 M characters
        let messages = [msg("system", "Propose three complications."), msg("user", &novel)];
        let budget = prompt_token_budget(crate::ai::model_store::N_CTX, 512);
        let tokens = fit_to_budget(&messages, budget, fake_tokenize).unwrap();
        assert!(tokens.len() <= budget, "{} > {budget}", tokens.len());
        assert!(tokens.len() > budget / 2, "should keep as much text as fits, kept {}", tokens.len());
    }

    #[test]
    fn shortening_keeps_the_beginning_and_end_and_the_small_messages() {
        let text = format!("START {} END", "x".repeat(10_000));
        let seen = std::cell::RefCell::new(Vec::new());
        let tokenize = |m: &[ChatMessage]| {
            seen.borrow_mut().push(m.to_vec());
            fake_tokenize(m)
        };
        fit_to_budget(&[msg("system", "Keep me intact."), msg("user", &text)], 500, tokenize).unwrap();
        let last = seen.borrow().last().unwrap().clone();
        assert_eq!(last[0].content, "Keep me intact.");
        assert!(last[1].content.starts_with("START ") && last[1].content.ends_with(" END"));
        assert!(last[1].content.contains("[…]"));
    }

    #[test]
    fn multibyte_text_is_cut_on_character_boundaries() {
        let text = "é€🙂".repeat(5_000);
        let tokens = fit_to_budget(&[msg("user", &text)], 300, fake_tokenize).unwrap();
        assert!(tokens.len() <= 300);
    }

    fn device(index: usize, device_type: llama_cpp_2::LlamaBackendDeviceType, free_mib: usize, total_mib: usize) -> llama_cpp_2::LlamaBackendDevice {
        llama_cpp_2::LlamaBackendDevice {
            index,
            name: format!("dev{index}"),
            description: String::new(),
            backend: "Vulkan".into(),
            memory_total: total_mib * MIB,
            memory_free: free_mib * MIB,
            device_type,
        }
    }

    #[test]
    fn gemma_needs_about_a_gigabyte_on_top_of_the_model_at_4096_tokens() {
        let model = 2_700_000_000u64; // gemma-2-2b-it-Q8_0.gguf
        let needed = gpu_memory_needed(model, 4096);
        assert_eq!(needed - model as usize, 1024 * MIB);
        assert_eq!(gpu_memory_needed(model, 8192) - model as usize, 1536 * MIB);
    }

    #[test]
    fn only_gpus_with_enough_free_memory_are_used() {
        use llama_cpp_2::LlamaBackendDeviceType::{Cpu, Gpu, IntegratedGpu};
        let needed = gpu_memory_needed(2_700_000_000, 4096); // ~3.5 GiB
        let devices = [
            device(0, Cpu, 16_000, 16_000),
            device(1, Gpu, 3_000, 4_096),         // 4 GB card, desktop using 1 GB: too tight
            device(2, Gpu, 7_500, 8_192),         // 8 GB card: fine
            device(3, IntegratedGpu, 0, 6_000),   // free memory not reported: use the total
        ];
        assert_eq!(qualifying_gpus(&devices, needed), vec![2, 3]);
    }

    #[test]
    fn budget_reserves_room_for_the_answer() {
        assert_eq!(prompt_token_budget(8192, 512), 8192 - 512 - 32);
        assert_eq!(prompt_token_budget(100, 512), 64);
    }
}
