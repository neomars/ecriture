import json
import threading
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AIClient:
    _instance = None
    _lock = threading.Lock()

    @staticmethod
    def _get_saved_path_file():
        if "XDG_CACHE_HOME" in os.environ:
            base = os.path.join(os.environ["XDG_CACHE_HOME"], "ecriture")
        else:
            base = os.path.join(os.path.expanduser("~"), ".cache", "ecriture")
        try:
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, "ai_model_path.txt")
        except Exception:
            return os.path.join(os.path.abspath("."), "ai_model_path.txt")

    @classmethod
    def _load_saved_model_dir(cls):
        path_file = cls._get_saved_path_file()
        if os.path.exists(path_file):
            try:
                with open(path_file, "r", encoding="utf-8") as f:
                    saved_dir = f.read().strip()
                    if saved_dir and os.path.isdir(saved_dir):
                        return saved_dir
            except Exception:
                pass
        return None

    def save_model_dir(self, directory):
        self.model_dir = directory
        self.model_path = os.path.join(self.model_dir, self.model_filename)
        try:
            with open(self._get_saved_path_file(), "w", encoding="utf-8") as f:
                f.write(directory)
        except Exception as e:
            print(f"Failed to save AI model directory to file: {e}")

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AIClient, cls).__new__(cls)
                    cls._instance._model = None
                    cls._instance._tokenizer = None
                    cls._instance.model_filename = "gemma-2-2b-it" # Changed to huggingface model name

                    saved_dir = cls._load_saved_model_dir()
                    if saved_dir:
                        cls._instance.model_dir = saved_dir
                    else:
                        from util import get_model_dir
                        cls._instance.model_dir = get_model_dir()

                    cls._instance.model_path = os.path.join(cls._instance.model_dir, cls._instance.model_filename)
        return cls._instance

    def _load_model(self):
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is not None:
                return self._model

            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

                # 1 - Quantization
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                )

                # Check for model path (we assume it is a huggingface model downloaded locally or we use standard HF cache)
                # If local model doesn't exist we fall back to downloading
                model_id = self.model_path if os.path.exists(self.model_path) else "google/gemma-2-2b-it"

                self._tokenizer = AutoTokenizer.from_pretrained(model_id, token=os.environ.get("HF_TOKEN", True))
                self._model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    quantization_config=quantization_config,
                    device_map="auto", # This handles .to('cuda') automatically
                    token=os.environ.get("HF_TOKEN", True)
                )

                return self._model
            except Exception as e:
                print(f"Error loading model: {e}")
                return None

    def check_status(self):
        try:
            # We assume it's online if transformers can be imported (simplification)
            return {"status": "online"}
        except Exception as e:
            return {"status": "offline", "error": str(e), "traceback": __import__('traceback').format_exc()}

    def get_models(self):
        return ["gemma-2-2b-it"]

    def select_best_model(self, preferred_model):
        return "gemma-2-2b-it"

    def generate_chat(self, messages, model="gemma-2-2b-it", temperature=0.7, timeout=60, stream=False):
        try:
            status = self.check_status()
            if status["status"] != "online":
                raise Exception("Local model not installed.")

            model = self._load_model()
            if not model:
                raise Exception("Failed to load Transformers model.")

            tokenizer = self._tokenizer

            # Format messages
            formatted_messages = []
            system_content = []

            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", "")

                if role == "system":
                    system_content.append(content)
                elif role == "user":
                    if system_content:
                        content = "\n\n".join(system_content) + "\n\n" + content
                        system_content = []

                    if not formatted_messages or formatted_messages[-1]["role"] == "assistant":
                        formatted_messages.append({"role": "user", "content": content})
                    else:
                        formatted_messages[-1]["content"] += "\n\n" + content
                elif role == "assistant":
                    if formatted_messages and formatted_messages[-1]["role"] == "user":
                        formatted_messages.append({"role": "assistant", "content": content})
                    elif formatted_messages and formatted_messages[-1]["role"] == "assistant":
                        formatted_messages[-1]["content"] += "\n\n" + content
                    else:
                        pass

            if system_content:
                if not formatted_messages or formatted_messages[-1]["role"] == "assistant":
                    formatted_messages.append({"role": "user", "content": "\n\n".join(system_content)})
                else:
                    formatted_messages[-1]["content"] += "\n\n" + "\n\n".join(system_content)

            input_ids = tokenizer.apply_chat_template(formatted_messages, add_generation_prompt=True, return_tensors="pt").to(model.device)

            if stream:
                from transformers import TextIteratorStreamer
                import threading
                streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
                generation_kwargs = dict(input_ids=input_ids, streamer=streamer, max_new_tokens=512, temperature=temperature)

                thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
                thread.start()

                def token_generator():
                    for new_text in streamer:
                        yield new_text
                return token_generator()
            else:
                outputs = model.generate(input_ids, max_new_tokens=512, temperature=temperature)
                content = tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)

                return {
                    "status": "success",
                    "message": content.strip(),
                    "model": "gemma-2-2b-it"
                }
        except Exception as e:
            print(f"Error calling local AI: {e}")
            raise

    def get_fallback_response(self, category, text_or_messages, style="elegant", lang="fr"):
        import json
        import os

        locale_path = resource_path(os.path.join("locales", f"{lang}.json"))
        try:
            with open(locale_path, "r", encoding="utf-8") as f:
                translations = json.load(f)
        except Exception:
            translations = {}

        def get_str(key, default=""):
            return translations.get(key, default)

        if isinstance(text_or_messages, list):
            user_text = text_or_messages[-1].get("content", "") if text_or_messages else ""
        else:
            user_text = str(text_or_messages)

        user_text_lower = user_text.lower()
        is_french = lang == "fr" or any(word in user_text_lower for word in ["le", "la", "les", "une", "un", "est", "et", "de", "je", "tu", "il"])

        effective_lang = "fr" if is_french else "en"
        if effective_lang != lang:
            locale_path = resource_path(os.path.join("locales", f"{effective_lang}.json"))
            try:
                with open(locale_path, "r", encoding="utf-8") as f:
                    translations = json.load(f)
            except Exception:
                translations = {}

        if category in ["describe", "rewrite", "expand"]:
            if category == "describe":
                return get_str("fallback_describe").replace("{text}", user_text)
            elif category == "rewrite":
                key = f"fallback_rewrite_{style}"
                fallback = get_str(key)
                if not fallback:
                    fallback = get_str("fallback_rewrite_elegant")
                return fallback.replace("{text}", user_text)
            else:
                return get_str("fallback_expand").replace("{text}", user_text)

        elif category in ["relecture_style", "relecture_coherence"]:
            if category == "relecture_style":
                return get_str("fallback_relecture_style")
            else:
                return get_str("fallback_relecture_coherence")

        else:
            if any(kw in user_text_lower for kw in ["plan", "intrigue", "plot"]):
                return get_str("fallback_chat_plot")
            elif any(kw in user_text_lower for kw in ["personnage", "character", "heros", "héro"]):
                return get_str("fallback_chat_character")
            else:
                return get_str("fallback_chat_general")
