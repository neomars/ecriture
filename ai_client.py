import json

import threading
import json
import os

class OllamaClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(OllamaClient, cls).__new__(cls)
                    cls._instance._llm = None
                    cls._instance.model_repo = "bartowski/gemma-2-2b-it-GGUF"
                    cls._instance.model_filename = "gemma-2-2b-it-Q4_K_M.gguf"
        return cls._instance


    def _get_str(self, lang, key):
        import json
        if lang == "en":
            with open("locales/en.json", "r", encoding="utf-8") as f:
                return json.load(f).get(key, key)
        else:
            with open("locales/fr.json", "r", encoding="utf-8") as f:
                return json.load(f).get(key, key)

    def _load_model(self):
        if self._llm is not None:
            return self._llm

        with self._lock:
            if self._llm is not None:
                return self._llm

            try:
                from huggingface_hub import hf_hub_download
                model_path = hf_hub_download(
                    repo_id=self.model_repo,
                    filename=self.model_filename,
                    local_files_only=True
                )

                from llama_cpp import Llama
                self._llm = Llama(
                    model_path=model_path,
                    n_ctx=2048,
                    n_threads=4,
                    verbose=False
                )
                return self._llm
            except Exception as e:
                print(f"Error loading model: {e}")
                return None

    def check_status(self):
        import traceback
        try:
            from huggingface_hub import hf_hub_download
            model_path = hf_hub_download(
                repo_id=self.model_repo,
                filename=self.model_filename,
                local_files_only=True
            )
            return {"status": "online"}
        except Exception as e:
            print("[DEBUG] check_status failed:")
            traceback.print_exc()
            return {"status": "offline"}

    def get_models(self):
        status = self.check_status()
        if status["status"] == "online":
            return ["gemma-2-2b-it"]
        return []

    def select_best_model(self, preferred_model):
        return "gemma-2-2b-it"


    def generate_chat(self, messages, model="gemma-2-2b-it", temperature=0.7, timeout=60):
        import traceback
        try:
            status = self.check_status()
            if status["status"] != "online":
                raise Exception("Local model not installed.")

            llm = self._load_model()
            if not llm:
                raise Exception("Failed to load Llama engine.")

            response = llm.create_chat_completion(
                messages=messages,
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
            print(f"[DEBUG] generate_chat failed: {e}")
            traceback.print_exc()
            raise
    def get_fallback_response(self, category, text_or_messages, style="elegant", lang="fr"):
        """
        Generates simulated fallback responses when Ollama is offline.
        """
        # Extract last user message if a list was passed
        if isinstance(text_or_messages, list):
            user_text = text_or_messages[-1].get("content", "") if text_or_messages else ""
        else:
            user_text = str(text_or_messages)

        user_text_lower = user_text.lower()
        is_french = lang == "fr" or any(word in user_text_lower for word in ["le", "la", "les", "une", "un", "est", "et", "de", "je", "tu", "il"])

        # 1. Handle tool fallback (Describe, Rewrite, Expand)
        if category in ["describe", "rewrite", "expand"]:
            if category == "describe":
                if is_french:
                    return f"Une description riche et sensorielle de « {user_text} » : Des nuances subtiles se détachent, capturant la lumière changeante avec une précision artistique, éveillant un sentiment profond d'émerveillement et de mystère."
                else:
                    return f"A rich and sensory description of '{user_text}': Subtle textures and fine details catch the ambient light, casting delicate shadows that evoke a deep sense of atmospheric presence and quiet contemplation."
            elif category == "rewrite":
                if is_french:
                    style_fr = {
                        "elegant": f"Version élégante de « {user_text} » : Une formulation raffinée, drapée de tournures mélodieuses et d'un vocabulaire choisi avec le plus grand soin.",
                        "dramatic": f"Version dramatique de « {user_text} » : Soudain, l'air devint lourd de menaces. Chaque mot résonnait comme un coup de tonnerre sur le point d'éclater, scellant à jamais leur destin tragique.",
                        "poetic": f"Version poétique de « {user_text} » : Comme un murmure d'étoiles filantes glissant sur le velours de la nuit, les mots dansent et s'envolent au gré des songes.",
                        "humorous": f"Version humoristique de « {user_text} » : Bon, d'accord, « {user_text} »... Mais en plus rigolo, avec un zeste d'ironie et deux cuillères à soupe d'auto-dérision !",
                        "action": f"Version action de « {user_text} » : Impact immédiat. Le souffle court. Pas un instant à perdre. Tout s'accélère à un rythme effréné !"
                    }
                    return style_fr.get(style, style_fr["elegant"])
                else:
                    style_en = {
                        "elegant": f"Elegant version of '{user_text}': A polished expression, woven with sophisticated syntax and literary precision.",
                        "dramatic": f"Dramatic version of '{user_text}': Suddenly, a suffocating tension filled the room, matching the perilous stakes of this critical hour.",
                        "poetic": f"Poetic version of '{user_text}': Like starlight kissing the dark surface of a sleeping lake, the words shimmer with ethereal grace.",
                        "humorous": f"Humorous version of '{user_text}': Well, let's add a playful twist to '{user_text}'—with a dash of wit and a side of healthy sarcasm!",
                        "action": f"Action version of '{user_text}': High-octane response. Heart pounding. Every second counted. Move or die!"
                    }
                    return style_en.get(style, style_en["elegant"])
            else: # expand
                if is_french:
                    return f"« {user_text} » de manière plus développée : Nous pouvons explorer l'arrière-plan avec soin, en ajoutant des détails descriptifs substantiels, en ralentissant le rythme et en enrichissant les émotions intérieures des personnages présents."
                else:
                    return f"Expanded version of '{user_text}': Elaborating further on this moment, we unfold layers of quiet thoughts and sensory nuances, breathing full dimension into the atmosphere and pacing of the narrative."

        # 2. Handle Relecture fallbacks (Style & Prose or Coherence)
        elif category in ["relecture_style", "relecture_coherence"]:
            if category == "relecture_style":
                if is_french:
                    return (
                        "**Analyse de Style & Prose (Simulation hors ligne) :**\n\n"
                        "1. **Richesse du vocabulaire :** Votre prose présente une belle fluidité, mais certains verbes ternes "
                        "(comme *faire*, *dire*, *regarder*) gagneraient à être remplacés par des synonymes plus imagés "
                        "(comme *concevoir*, *déclarer*, *contempler*).\n"
                        "2. **Rythme et musicalité :** Les phrases ont des longueurs variées, créant une cadence agréable. "
                        "Essayez de resserrer la ponctuation dans les moments de tension pour accentuer le suspense.\n"
                        "3. **Suggestions de style :** Évitez les adverbes redondants (ex: *marcher lentement* peut devenir *flâner*)."
                    )
                else:
                    return (
                        "**Style & Prose Analysis (Offline Simulation):**\n\n"
                        "1. **Vocabulary richness:** Your prose flow is excellent, but several common verbs "
                        "(like *do*, *say*, *look*) could be replaced with more evocative synonyms "
                        "(like *craft*, *declare*, *gaze*).\n"
                        "2. **Pacing & Cadence:** The sentence lengths are well-balanced. Try shortening clauses "
                        "during highly dramatic action beats to enhance momentum.\n"
                        "3. **Style Suggestions:** Cut down on unnecessary adverbs (e.g., *walking slowly* can be *sauntering*)."
                    )
            else: # coherence
                if is_french:
                    return (
                        "**Analyse de Cohérence (Simulation hors ligne) :**\n\n"
                        "1. **Cohérence des actions :** Aucun anachronisme ou contradiction majeure n'a été détecté dans le déroulement de la scène.\n"
                        "2. **Comportement des personnages :** Les réactions psychologiques des personnages sont plausibles et alignées "
                        "avec le lore et les traits définis dans leurs fiches.\n"
                        "3. **Logique spatio-temporelle :** Les déplacements des protagonistes dans le décor restent fluides et logiques."
                    )
                else:
                    return (
                        "**Coherence Analysis (Offline Simulation):**\n\n"
                        "1. **Action Consistency:** No narrative anachronisms or glaring contradictions detected in this scene.\n"
                        "2. **Character Motivations:** Character decisions and physical actions align well "
                        "with their established lore and traits.\n"
                        "3. **Spatial & Temporal Logic:** The sequence of movements and descriptions of scenery maintain a solid sense of space."
                    )

        # 3. Handle Chat assistant fallback
        else:
            if any(kw in user_text_lower for kw in ["plan", "intrigue", "plot"]):
                return (
                    self._get_str(lang, "gemma_simulation_title") + "\n" +
                    "Pour structurer votre intrigue, je vous suggère de suivre le schéma narratif :\n" +
                    "1. Situation initiale : Présentation du protagoniste et du cadre.\n" +
                    "2. Élément déclencheur : Un bouleversement majeur.\n" +
                    "3. Péripéties : Obstacles et évolution des personnages.\n" +
                    "4. Climax : Le point de tension maximale.\n" +
                    "5. Dénouement : Résolution de l'intrigue."
                )
            elif any(kw in user_text_lower for kw in ["personnage", "character", "heros", "héro"]):
                return (
                    self._get_str(lang, "gemma_simulation_title") + "\n" +
                    "Voici quelques idées pour approfondir un personnage :\n" +
                    "- Quel est son plus grand secret ?\n" +
                    "- Quelle est sa motivation principale (désir profond vs. besoin inconscient) ?\n" +
                    "- Ajoutez un défaut physique ou une habitude unique pour le rendre mémorable."
                )
            else:
                return (
                    self._get_str(lang, "gemma_simulation_title") + "\n" +
                    self._get_str(lang, "gemma_simulation_hello") + "\n" +
                    self._get_str(lang, "gemma_error_loading") + "\n" +
                    self._get_str(lang, "gemma_simulation_suggestion")
                )
