import json
import urllib.request
import urllib.error

class OllamaClient:
    """
    Reusable, thread-safe client object to communicate with local Ollama instances.
    Provides standard tag checking, chat query wrappers, and detailed offline fallbacks.
    """
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url.rstrip('/')

    def get_available_models(self):
        """
        Queries the Ollama instance to list all installed models.
        Returns a list of model names (strings), or empty list if offline.
        """
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                tags_data = json.loads(response.read().decode('utf-8'))
                return [m["name"] for m in tags_data.get("models", [])]
        except Exception:
            return []

    def select_best_model(self, requested_model):
        """
        Validates the requested model against currently installed ones.
        Falls back to the first available model if the requested one is not found.
        """
        available = self.get_available_models()
        if not available:
            return requested_model

        # Check direct or :latest match
        if requested_model in available or f"{requested_model}:latest" in available:
            return requested_model

        # Fallback to first available model
        return available[0]

    def chat(self, messages, model="llama3", temperature=0.7, timeout=25):
        """
        Sends a list of message dictionaries to the Ollama chat endpoint.
        Returns a dictionary indicating status, message content, and model used.
        Raises an exception if the HTTP call fails.
        """
        resolved_model = self.select_best_model(model)
        chat_payload = {
            "model": resolved_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(chat_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            chat_response = json.loads(response.read().decode('utf-8'))
            content = chat_response.get("message", {}).get("content", "").strip()
            return {
                "status": "success",
                "message": content,
                "model": resolved_model
            }

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
                    "[Assistant IA (Ollama Simulation - Hors ligne)]\n"
                    "Pour structurer votre intrigue, je vous suggère de suivre le schéma narratif :\n"
                    "1. Situation initiale : Présentation du protagoniste et du cadre.\n"
                    "2. Élément déclencheur : Un bouleversement majeur.\n"
                    "3. Péripéties : Obstacles et évolution des personnages.\n"
                    "4. Climax : Le point de tension maximale.\n"
                    "5. Dénouement : Résolution de l'intrigue."
                )
            elif any(kw in user_text_lower for kw in ["personnage", "character", "heros", "héro"]):
                return (
                    "[Assistant IA (Ollama Simulation - Hors ligne)]\n"
                    "Voici quelques idées pour approfondir un personnage :\n"
                    "- Quel est son plus grand secret ?\n"
                    "- Quelle est sa motivation principale (désir profond vs. besoin inconscient) ?\n"
                    "- Ajoutez un défaut physique ou une habitude unique pour le rendre mémorable."
                )
            else:
                return (
                    "[Assistant IA (Ollama Simulation - Hors ligne)]\n"
                    "Bonjour ! Je suis votre assistant d'écriture Écriture.\n"
                    "Ollama semble être hors ligne sur http://localhost:11434.\n"
                    "Voici une suggestion pour continuer : déterminez l'enjeu principal de votre scène actuelle !"
                )
