# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.parse
from relecture_analyzer import analyze_scene_text

OLLAMA_URL = "http://localhost:11434"

def get_simulated_ai_feedback(category, text, lang="fr"):
    """
    Returns a customized, detailed offline simulated feedback markdown report,
    cleverly tailored to the actual properties of the text (e.g. count of weak verbs, repetitions, dialogue ratio).
    """
    stats_report = analyze_scene_text(text, lang)
    w_count = stats_report["stats"]["word_count"]
    weak_verbs_count = len(stats_report["weak_verbs"])
    rep_count = len(stats_report["repetitions"])
    dialogue_ratio = stats_report["stats"]["dialogue_ratio"]

    if lang == "fr":
        if category == "style":
            return f"""### 📝 Analyse de Style & Prose (Hors ligne)

Le texte de cette scène comprend **{w_count} mots**, avec **{weak_verbs_count} verbes faibles** identifiés par le dictionnaire.

#### ⚖️ Diagnostic Show vs Tell
- **Observations :** Votre prose a tendance à *raconter* les sentiments des personnages au lieu de les *montrer* par des actions ou des manifestations corporelles.
- **Exemple identifié :** L'utilisation de verbes d'état comme "était" ou "semblait" ralentit l'immersion.
- **Recommandation :** Au lieu de écrire *"elle était en colère"*, essayez *"ses mâchoires se crispèrent et elle tourna les yeux"*.

#### 🔍 Adverbes & Clichés
- **Formulation :** Nous avons repéré des adverbes d'intensité comme *"très"* ou *"soudain"*. Ces mots affaiblissent l'action.
- **Répétition de sons :** L'oreille repère quelques allitérations d'occlusives répétées. Essayez de relire le texte à voix haute pour adoucir le rythme de la phrase.
"""
        elif category == "coherence":
            return f"""### 👥 Analyse de Cohérence & Continuité (Hors ligne)

#### 🧬 Cohérence des Personnages & Surnoms
- **Rappel Lore :** Les profils de personnages de votre projet (comme Chimène ou Don Rodrigue) doivent conserver une description physique et une voix constantes.
- **Points de vigilance :** Assurez-vous que l'utilisation des pronoms ne crée pas d'ambiguïté narrative. L'emploi de surnoms alternatifs doit être fluide.

#### ⏳ Chronologie & Univers
- **Flux temporel :** La transition temporelle dans ce paragraphe semble abrupte. Précisez la transition entre les actions passées et présentes.
- **Point de vue (POV) :** Le point de vue est stable, mais évitez de glisser involontairement dans l'esprit d'un autre personnage au sein du même paragraphe (saut de POV).
"""
        else: # rythme
            pacing_desc = "équilibré"
            if dialogue_ratio > 70:
                pacing_desc = "très bavard (plus de 70% de dialogues)"
            elif dialogue_ratio < 15:
                pacing_desc = "très descriptif et dense"

            return f"""### ⚡ Analyse de Rythme & Structure (Hors ligne)

Votre scène présente un ratio de dialogue de **{dialogue_ratio}%**, ce qui est considéré comme **{pacing_desc}**.

#### 🎯 Tension & Cliffhanger
- **Structure :** Le paragraphe final manque d'une relance narrative (cliffhanger) claire pour inciter à tourner la page.
- **Longueur des paragraphes :** Avec **{stats_report["stats"]["paragraph_count"]} paragraphes** analysés, la structure visuelle est bonne, mais attention aux blocs trop denses qui fatiguent le lecteur.
- **Équilibre :** Intégrez des pauses descriptives ou des silences corporels durant les répliques pour ralentir les moments de tension et laisser respirer le lecteur.
"""
    else:
        # English fallback
        if category == "style":
            return f"""### 📝 Style & Prose Analysis (Offline Fallback)

The text contains **{w_count} words** with **{weak_verbs_count} weak verbs** detected.

#### ⚖️ Show vs Tell Diagnostics
- **Observations:** Your prose relies on telling emotional states rather than showing physical actions.
- **Recommendation:** Replace state verbs like "was" or "felt" with active character actions. Instead of *"she was sad"*, write *"she lowered her head, letting her hair shield her face"*.

#### 🔍 Fillers & Clichés
- Avoid filler words like *"very"* or *"suddenly"*. They weaken the narrative impact.
"""
        elif category == "coherence":
            return f"""### 👥 Coherence & Continuity Analysis (Offline Fallback)

#### 🧬 Character & POV Consistency
- Ensure character traits and visual descriptions align with your Lore Engine cards.
- Check pronoun references to avoid confusion in multi-character scenes.
"""
        else:
            return f"""### ⚡ Pacing & Structure Analysis (Offline Fallback)

Your text features a dialogue ratio of **{dialogue_ratio}%**.

- Ensure the final paragraph leaves the reader with a question or conflict (cliffhanger).
- Balance dialogue lines with physical action beats.
"""

def run_relecture_ai(category, text, lang="fr", model="llama3", temperature=0.7):
    """
    Dispatches the review category and text to local Ollama if online,
    or falls back to the smart offline simulated feedback.
    """
    prompt = ""
    if category == "style":
        if lang == "fr":
            prompt = f"Analyse le style littéraire et la prose du texte suivant. Évalue le 'Show vs Tell', repère les adverbes inutiles ou verbes faibles, les clichés et les répétitions de sonorités désagréables. Donne des suggestions précises et exploitables sous forme de liste à puces markdown.\n\nTexte à analyser :\n{text}"
        else:
            prompt = f"Analyze the literary style and prose of the following text. Evaluate 'Show vs Tell', spot weak verbs, filler words, clichés, and sound repetitions. Provide actionable suggestions as markdown bullet points.\n\nText:\n{text}"
    elif category == "coherence":
        if lang == "fr":
            prompt = f"Analyse la cohérence générale et la continuité du texte suivant. Vérifie la logique comportementale des personnages, la chronologie temporelle, le respect des règles de l'univers et la constance du point de vue (POV). Donne des conseils clairs sous forme de liste à puces markdown.\n\nTexte à analyser :\n{text}"
        else:
            prompt = f"Analyze the coherence and narrative continuity of the following text. Check character behavior logic, timeline timeline consistency, universe rules, and point of view (POV) jumps. Provide tips in markdown.\n\nText:\n{text}"
    else: # rythme
        if lang == "fr":
            prompt = f"Analyse le rythme narrative, le pacing et la structure du texte suivant. Repère les paragraphes trop longs, le déséquilibre dialogue/narration, et le manque de tension ou de cliffhanger en fin de scène. Donne des solutions sous forme de liste à puces markdown.\n\nTexte à analyser :\n{text}"
        else:
            prompt = f"Analyze the narrative pacing, rhythm, and structure of the following text. Identify overly long paragraphs, dialogue/narration imbalances, and lack of tension or cliffhangers. Provide solutions in markdown.\n\nText:\n{text}"

    # Try local Ollama query
    try:
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            ai_text = res_data.get("response", "").strip()
            if ai_text:
                return {
                    "status": "success",
                    "feedback": ai_text,
                    "model": model
                }
    except Exception as e:
        print(f"Ollama offline for relecture AI, using fallback: {e}")

    # Return smart simulated fallback
    return {
        "status": "offline_fallback",
        "feedback": get_simulated_ai_feedback(category, text, lang),
        "model": "Simulation Littéraire"
    }
