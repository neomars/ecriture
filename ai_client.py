import json

import threading
import json
import os

class AIClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AIClient, cls).__new__(cls)
                    cls._instance._llm = None
                    cls._instance.model_filename = "gemma-2-2b-it-Q8_0.gguf"
                    cls._instance.model_dir = os.path.join(os.path.expanduser("~"), ".cache", "ecriture")
                    cls._instance.model_path = os.path.join(cls._instance.model_dir, cls._instance.model_filename)
        return cls._instance

    def _load_model(self):
        if self._llm is not None:
            return self._llm

        with self._lock:
            if self._llm is not None:
                return self._llm

            try:
                if not os.path.exists(self.model_path):
                    raise Exception(f"Model file not found at {self.model_path}")

                from llama_cpp import Llama
                self._llm = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,
                    n_threads=4,
                    verbose=False
                )
                return self._llm
            except Exception as e:
                print(f"Error loading model: {e}")
                return None

    def check_status(self):
        try:
            if os.path.exists(self.model_path):
                return {"status": "online"}
            else:
                return {"status": "offline", "error": "Model file not found"}
        except Exception as e:
            return {"status": "offline", "error": str(e), "traceback": __import__('traceback').format_exc()}

    def get_models(self):
        return ["gemma-2-2b-it"]

    def select_best_model(self, preferred_model):
        return "gemma-2-2b-it"


    def generate_chat(self, messages, model="gemma-2-2b-it", temperature=0.7, timeout=60):
        try:
            status = self.check_status()
            if status["status"] != "online":
                raise Exception("Local model not installed.")

            llm = self._load_model()
            if not llm:
                raise Exception("Failed to load Llama engine.")

            # Gemma 2 templates do not support the 'system' role natively in their chat_template.
            # We must merge any 'system' messages into the first 'user' message, or change their role to 'user'.
            formatted_messages = []
            system_content = []

            for msg in messages:
                if msg.get("role") == "system":
                    system_content.append(msg.get("content", ""))
                else:
                    if msg.get("role") == "user" and system_content:
                        combined_content = "\n\n".join(system_content) + "\n\n" + msg.get("content", "")
                        formatted_messages.append({"role": "user", "content": combined_content})
                        system_content = []
                    else:
                        formatted_messages.append(msg)

            # If there are trailing system messages without a user message (unlikely), append as user
            if system_content:
                formatted_messages.append({"role": "user", "content": "\n\n".join(system_content)})

            response = llm.create_chat_completion(
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=512
            )

            content = response["choices"][0]["message"]["content"]
            return {
                "status": "success",
                "message": content.strip(),
                "model": "gemma-2-2b-it"
            }
        except Exception as e:
            print(f"Error calling local AI: {e}")
            raise
    def get_fallback_response(self, category, text_or_messages, style="elegant", lang="fr"):
        """
        Generates simulated fallback responses when AI is offline.
        """
        # We need to fetch the strings from the locales
        import json
        import os

        locale_path = os.path.join(os.path.dirname(__file__), "locales", f"{lang}.json")
        try:
            with open(locale_path, "r", encoding="utf-8") as f:
                translations = json.load(f)
        except Exception:
            translations = {}

        def get_str(key, default=""):
            return translations.get(key, default)

        # Extract last user message if a list was passed
        if isinstance(text_or_messages, list):
            user_text = text_or_messages[-1].get("content", "") if text_or_messages else ""
        else:
            user_text = str(text_or_messages)

        user_text_lower = user_text.lower()
        is_french = lang == "fr" or any(word in user_text_lower for word in ["le", "la", "les", "une", "un", "est", "et", "de", "je", "tu", "il"])

        # Determine effective lang if it wasn't passed accurately
        effective_lang = "fr" if is_french else "en"
        if effective_lang != lang:
            locale_path = os.path.join(os.path.dirname(__file__), "locales", f"{effective_lang}.json")
            try:
                with open(locale_path, "r", encoding="utf-8") as f:
                    translations = json.load(f)
            except Exception:
                translations = {}

        # 1. Handle tool fallback (Describe, Rewrite, Expand)
        if category in ["describe", "rewrite", "expand"]:
            if category == "describe":
                return get_str("fallback_describe").replace("{text}", user_text)
            elif category == "rewrite":
                key = f"fallback_rewrite_{style}"
                fallback = get_str(key)
                if not fallback: # default to elegant
                    fallback = get_str("fallback_rewrite_elegant")
                return fallback.replace("{text}", user_text)
            else: # expand
                return get_str("fallback_expand").replace("{text}", user_text)

        # 2. Handle Relecture fallbacks (Style & Prose or Coherence)
        elif category in ["relecture_style", "relecture_coherence"]:
            if category == "relecture_style":
                return get_str("fallback_relecture_style")
            else: # coherence
                return get_str("fallback_relecture_coherence")

        # 3. Handle Chat assistant fallback
        else:
            if any(kw in user_text_lower for kw in ["plan", "intrigue", "plot"]):
                return get_str("fallback_chat_plot")
            elif any(kw in user_text_lower for kw in ["personnage", "character", "heros", "héro"]):
                return get_str("fallback_chat_character")
            else:
                return get_str("fallback_chat_general")
