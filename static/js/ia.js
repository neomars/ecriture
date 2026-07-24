        // CONTEXTUAL AI TOOLS (Describe, Rewrite, Expand)
        let activeSelection = { start: 0, end: 0, text: "" };
        let lastAiToolCall = { tool: "", style: "", text: "" };

        function handleTextSelection(e) {
            const editor = document.getElementById('editor-content');
            const menu = document.getElementById('ai-selection-menu');
            if (!editor || !menu) return;

            // If project is locked, do not offer AI tools
            if (projectData && projectData.settings && projectData.settings.locked) {
                menu.classList.add('hidden');
                return;
            }

            const start = editor.selectionStart;
            const end = editor.selectionEnd;
            const text = editor.value.substring(start, end).trim();

            if (start !== end && text.length > 0) {
                activeSelection = { start, end, text: editor.value.substring(start, end) };

                // Calculate position relative to editor contents
                const caretCoords = getCaretCoordinates(editor, start);

                // Offset calculation relative to the editor's bounding box and scroll offset
                const rect = editor.getBoundingClientRect();
                const container = editor.closest('main');
                const containerRect = container.getBoundingClientRect();

                // Compute exact absolute coordinates within the main workspace container
                const menuLeft = rect.left - containerRect.left + caretCoords.left - editor.scrollLeft;
                const menuTop = rect.top - containerRect.top + caretCoords.top + caretCoords.height - editor.scrollTop + 8; // placed perfectly below selection

                menu.style.left = `${Math.max(10, Math.min(menuLeft, containerRect.width - 250))}px`;
                menu.style.top = `${menuTop}px`;
                menu.classList.remove('hidden');
            } else {
                // Wait slightly to verify click target to prevent immediate hide on click
                setTimeout(() => {
                    const activeEl = document.activeElement;
                    if (e && e.target && (e.target.closest('#ai-selection-menu') || e.target.closest('#ai-preview-card'))) {
                        return;
                    }
                    if (activeEl && (activeEl.closest('#ai-selection-menu') || activeEl.closest('#ai-preview-card'))) {
                        return;
                    }
                    menu.classList.add('hidden');
                    const rewriteMenu = document.getElementById('ai-rewrite-dropdown-menu');
                    if (rewriteMenu) rewriteMenu.classList.add('hidden');
                    const synonymsMenu = document.getElementById('synonyms-dropdown-menu');
                    if (synonymsMenu) synonymsMenu.classList.add('hidden');
                }, 150);
            }
        }

        function closeAiPreview() {
            document.getElementById('ai-preview-card').classList.add('hidden');
        }

        function toggleRewriteDropdown(event) {
            event.stopPropagation();
            const menu = document.getElementById('ai-rewrite-dropdown-menu');
            if (menu) {
                menu.classList.toggle('hidden');
            }
        }
        async function triggerContextAI(tool, style = "") {
            const menu = document.getElementById('ai-selection-menu');
            const rewriteMenu = document.getElementById('ai-rewrite-dropdown-menu');
            const card = document.getElementById('ai-preview-card');
            if (menu) menu.classList.add('hidden');
            if (rewriteMenu) rewriteMenu.classList.add('hidden');
            if (!card) return;

            // Save last call params
            lastAiToolCall = { tool, style, text: activeSelection.text };

            // Position card near selection menu
            if (menu) {
                card.style.left = menu.style.left;
                card.style.top = menu.style.top;
            }
            card.classList.remove('hidden');

            // Setup loading state
            document.getElementById('ai-preview-loading').classList.remove('hidden');
            document.getElementById('ai-preview-result-container').classList.add('hidden');
            document.getElementById('ai-preview-actions').classList.add('hidden');

            // Set Title
            let titleText = "Assistant IA";
            if (tool === "describe") {
                titleText = formatTranslation("ai_describe") || "Décrire";
            } else if (tool === "rewrite") {
                const styleName = style.charAt(0).toUpperCase() + style.slice(1);
                titleText = `${formatTranslation("ai_rewrite") || "Réécrire"} (${styleName})`;
            } else if (tool === "expand") {
                titleText = formatTranslation("ai_expand") || "Développer";
            }
            document.getElementById('ai-preview-tool-title').innerText = titleText;

            try {
                const injectLore = (projectData.settings.inject_lore_context !== undefined) ? projectData.settings.inject_lore_context : true;
                const sceneId = (activeNodeType === "scene") ? activeNodeId : null;
                const response = await fetch('/api/ai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tool: tool,
                        style: style,
                        text: activeSelection.text,
                        temperature: (projectData.settings.ai_temperature !== undefined) ? projectData.settings.ai_temperature : 0.7,
                        model: projectData.settings.ai_model || "llama3",
                        inject_lore_context: injectLore,
                        scene_id: sceneId
                    })
                });

                const data = await response.json();
                document.getElementById('ai-preview-loading').classList.add('hidden');

                if (response.ok) {
                    const resultContainer = document.getElementById('ai-preview-result-container');
                    resultContainer.innerText = data.message;
                    resultContainer.classList.remove('hidden');
                    document.getElementById('ai-preview-actions').classList.remove('hidden');
                } else {
                    alert("AI error: " + (data.error || "Failed to generate"));
                    closeAiPreview();
                }
            } catch (err) {
                console.error("AI Context error:", err);
                document.getElementById('ai-preview-loading').classList.add('hidden');
                alert("Failed to connect to AI service.");
                closeAiPreview();
            }
        }

        function regenerateAI() {
            if (lastAiToolCall.text) {
                triggerContextAI(lastAiToolCall.tool, lastAiToolCall.style);
            }
        }

        function applyAiSuggestion() {
            const editor = document.getElementById('editor-content');
            const resultContainer = document.getElementById('ai-preview-result-container');
            if (!editor || !resultContainer) return;

            const val = editor.value;
            const start = activeSelection.start;
            const end = activeSelection.end;
            const suggestion = resultContainer.innerText;

            // Perform clean replacement
            editor.value = val.substring(0, start) + suggestion + val.substring(end);

            // Reposition cursor
            const newCursorPos = start + suggestion.length;
            editor.setSelectionRange(newCursorPos, newCursorPos);
            editor.focus();

            // Trigger updates and persistence
            onEditorInput('content', editor.value);
            closeAiPreview();
        }

        async function runAiRelecture() {
            const feedbackEl = document.getElementById('relecture-ai-feedback');
            if (!feedbackEl) return;

            let text = "";
            if (activeRelectureScope === "scene") {
                const editor = document.getElementById('editor-content');
                text = editor ? editor.value : "";
            } else {
                text = getChapterText();
            }

            if (!text || !text.trim()) {
                feedbackEl.innerText = activeLang === 'fr' ? "Texte vide ou introuvable pour lancer l'analyse." : "Empty or missing text to analyze.";
                return;
            }

            feedbackEl.innerText = activeLang === 'fr' ? "Analyse en cours par l'IA... Veuillez patienter." : "AI analysis in progress... Please wait.";

            try {
                const response = await fetch('/api/relecture/ai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        category: activeRelectureCategory, // "style" or "coherence"
                        text: text,
                        temperature: (projectData.settings.ai_temperature !== undefined) ? projectData.settings.ai_temperature : 0.7,
                        model: projectData.settings.ai_model || "llama3",
                        lang: activeLang
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    feedbackEl.innerText = data.feedback;
                } else {
                    feedbackEl.innerText = activeLang === 'fr' ? "Erreur : Impossible d'obtenir un retour de l'IA." : "Error: Could not retrieve feedback from AI.";
                }
            } catch (err) {
                feedbackEl.innerText = activeLang === 'fr' ? "Erreur de connexion réseau." : "Network connection error.";
            }
        }

        // AI Chat history state
        let chatMessages = [];

        function updateChatWelcomeMessage() {
            const welcomeText = translations["chat_welcome"] || "Bonjour ! Je suis votre assistant Écriture. Posez-moi des questions sur vos personnages, l'intrigue ou demandez-moi des idées pour votre scène en cours.";
            if (chatMessages.length === 0) {
                chatMessages.push({ role: "assistant", content: welcomeText });
            } else if (chatMessages.length === 1 && chatMessages[0].role === "assistant") {
                chatMessages[0].content = welcomeText;
            }
            renderChat();
        }

        function clearChat() {
            const welcomeText = translations["chat_welcome"] || "Bonjour ! Je suis votre assistant Écriture. Posez-moi des questions sur vos personnages, l'intrigue ou demandez-moi des idées pour votre scène en cours.";
            chatMessages = [
                { role: "assistant", content: welcomeText }
            ];
            renderChat();
        }

        function renderChat() {
            const container = document.getElementById('chat-messages');
            if (!container) return;
            container.innerHTML = "";

            chatMessages.forEach(msg => {
                const bubble = document.createElement('div');
                if (msg.role === "user") {
                    bubble.className = "bg-indigo-50 text-indigo-950 p-2.5 rounded-lg border border-indigo-100 ml-6 self-end shadow-2xs max-w-[85%]";
                } else {
                    bubble.className = "bg-slate-50 text-slate-800 p-2.5 rounded-lg border border-slate-100 mr-6 self-start shadow-2xs max-w-[85%] whitespace-pre-line";
                }
                bubble.innerText = msg.content;
                container.appendChild(bubble);
            });

            container.scrollTop = container.scrollHeight;
        }

        async function sendChatMessage() {
            const input = document.getElementById('chat-input');
            const content = input.value.trim();
            if (!content) return;

            input.value = "";

            chatMessages.push({ role: "user", content });
            renderChat();

            const loadingIndex = chatMessages.length;
            chatMessages.push({ role: "assistant", content: "..." });
            renderChat();

            try {
                const injectLore = (projectData.settings.inject_lore_context !== undefined) ? projectData.settings.inject_lore_context : true;
                const sceneId = (activeNodeType === "scene") ? activeNodeId : null;
                const res = await fetch('/api/ai/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: chatMessages.slice(0, loadingIndex),
                        temperature: (projectData.settings.ai_temperature !== undefined) ? projectData.settings.ai_temperature : 0.7,
                        model: projectData.settings.ai_model || "llama3",
                        inject_lore_context: injectLore,
                        scene_id: sceneId
                    })
                });

                if (res.ok) {
                    const data = await res.json();
                    chatMessages[loadingIndex] = { role: "assistant", content: data.message };
                } else {
                    chatMessages[loadingIndex] = { role: "assistant", content: "Error: Could not retrieve response from Ollama." };
                }
            } catch (err) {
                chatMessages[loadingIndex] = { role: "assistant", content: "Error: Network connection failed." };
            }

            renderChat();
        }
