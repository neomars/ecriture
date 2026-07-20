# -*- coding: utf-8 -*-
import re
import os
import sqlite3

WEAK_VERBS = {"être", "avoir", "aller", "faire", "dire", "voir", "savoir", "be", "have", "go", "do", "say", "see", "know"}

FILLER_WORDS_FR = [
    "un peu", "assez", "genre", "voilà", "très", "vraiment", "soudain",
    "en fait", "du coup", "en gros", "tout à fait", "quelque peu", "rapidement"
]
FILLER_WORDS_EN = [
    "really", "very", "suddenly", "actually", "basically", "a bit", "quite",
    "somewhat", "like", "kind of"
]

DIALOGUE_TAGS_FR = [
    "dit-il", "dit-elle", "répondit-il", "répondit-elle", "demanda-t-il",
    "demanda-t-elle", "s'écria-t-il", "s'écria-t-elle", "rétorqua-t-il", "rétorqua-t-elle"
]
DIALOGUE_TAGS_EN = [
    "he said", "she said", "he replied", "she replied", "he asked",
    "she asked", "he retorted", "she retorted"
]

def tokenize(text):
    """Split text into lowercase alphanumeric words."""
    # Strip apostrophes cleanly (e.g., l'amour -> l, amour)
    words = re.findall(r'\b\w+\b', text.lower())
    return words

def get_word_lemmas_batch(words):
    """
    Given a list of words, query lexique.db in a single batch to extract lemmas.
    Returns a dict mapping word_form -> (lemma, cgram)
    """
    if not words:
        return {}

    db_path = "lexique.db"
    if not os.path.exists(db_path):
        return {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Unique and sanitized words
        unique_words = list(set([w.strip().lower() for w in words]))

        # SQLite maximum parameters is 999, so we chunk it just in case
        results = {}
        chunk_size = 900
        for i in range(0, len(unique_words), chunk_size):
            chunk = unique_words[i:i+chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            cursor.execute(f"""
                SELECT ortho, lemme, cgram
                FROM lexique
                WHERE ortho IN ({placeholders})
            """, chunk)
            rows = cursor.fetchall()
            for r in rows:
                ortho, lemme, cgram = r[0], r[1], r[2]
                if ortho not in results:
                    results[ortho] = []
                results[ortho].append((lemme, cgram))

        conn.close()
        return results
    except Exception as e:
        print(f"Error in batch lemma lookup: {e}")
        return {}

def analyze_scene_text(text, lang="fr"):
    """
    Performs rich lexical and narrative review of the text.
    Returns a structured dictionary with statistics and specific flags/suggestions.
    """
    if not text:
        return {
            "stats": {"word_count": 0, "paragraph_count": 0, "dialogue_ratio": 0, "vocabulary_richness": 0},
            "repetitions": [],
            "ment_adverbs": [],
            "weak_verbs": [],
            "fillers": [],
            "dialogue_tags": [],
            "pacing_flags": [],
            "grammar_flags": []
        }

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    # Stats basic
    all_words = tokenize(text)
    total_words = len(all_words)
    unique_words = len(set(all_words))
    vocab_richness = round((unique_words / total_words * 100), 1) if total_words > 0 else 0

    # Batch resolve lemmas to detect weak verbs
    lemma_cache = get_word_lemmas_batch(all_words) if lang == "fr" else {}

    repetitions = []
    ment_adverbs = []
    weak_verbs = []
    fillers = []
    dialogue_tags = []
    pacing_flags = []
    grammar_flags = []

    # 1. Repetitions per paragraph (local analysis)
    for p_idx, p in enumerate(paragraphs):
        p_words = tokenize(p)
        word_counts = {}
        for w in p_words:
            if len(w) > 3:  # Only flag words of length > 3
                word_counts[w] = word_counts.get(w, 0) + 1

        for w, count in word_counts.items():
            if count > 1:
                repetitions.append({
                    "paragraph_index": p_idx,
                    "word": w,
                    "count": count,
                    "context": f"... {w} ...",
                    "suggestion": f"Le mot '{w}' est répété {count} fois dans ce paragraphe. Utilisez un synonyme pour alléger la prose."
                })

    # 2. Scanning word-by-word for ment_adverbs, weak verbs, dialogue tags
    for p_idx, p in enumerate(paragraphs):
        p_lower = p.lower()

        # Punctuation / Spacing Checks
        # Double spaces
        if "  " in p:
            grammar_flags.append({
                "paragraph_index": p_idx,
                "text": "Espaces doubles",
                "suggestion": "Ce paragraphe contient des espaces doubles consécutifs."
            })
        # Starts with capital
        if p and p[0].isalpha() and not p[0].isupper():
            grammar_flags.append({
                "paragraph_index": p_idx,
                "text": "Majuscule manquante",
                "suggestion": "Le paragraphe semble commencer par une lettre minuscule."
            })

        # Dialogue tags
        tags_to_check = DIALOGUE_TAGS_FR if lang == "fr" else DIALOGUE_TAGS_EN
        for tag in tags_to_check:
            # Check if tag is in paragraph
            if tag in p_lower:
                dialogue_tags.append({
                    "paragraph_index": p_idx,
                    "tag": tag,
                    "suggestion": f"Incorporez des actions de personnages au lieu de répéter le verbe de parole '{tag}'."
                })

        # Filler words
        fillers_to_check = FILLER_WORDS_FR if lang == "fr" else FILLER_WORDS_EN
        for filler in fillers_to_check:
            # Use regex with word boundary to match exact filler word/phrase
            matches = re.finditer(rf"\b{re.escape(filler)}\b", p_lower)
            for m in matches:
                fillers.append({
                    "paragraph_index": p_idx,
                    "word": filler,
                    "suggestion": f"Le mot/expression remplisseur '{filler}' affaiblit le rythme. Essayez de le supprimer."
                })

        # Word-by-word check (Adverbs in -ment, weak verbs)
        p_words = tokenize(p)
        for w in p_words:
            # Adverbs ending in -ment (French)
            if lang == "fr" and w.endswith("ment") and len(w) > 5:
                # Exclude nouns ending in -ment like "moment", "gouvernement", "appartement", etc. using lexique.db if possible
                is_adv = True
                if w in lemma_cache:
                    # check if any category is NOM
                    if any(c[1] == 'NOM' for c in lemma_cache[w]):
                        is_adv = False
                if is_adv:
                    ment_adverbs.append({
                        "paragraph_index": p_idx,
                        "word": w,
                        "suggestion": f"L'adverbe en -ment '{w}' peut souvent être supprimé ou remplacé par une formulation plus forte."
                    })

            # Weak verbs
            if lang == "fr" and w in lemma_cache:
                for lem, cgram in lemma_cache[w]:
                    if lem in WEAK_VERBS and cgram == 'VER':
                        weak_verbs.append({
                            "paragraph_index": p_idx,
                            "word": w,
                            "lemma": lem,
                            "suggestion": f"Le verbe faible '{w}' (lemme: {lem}) gagnerait à être remplacé par un verbe d'action plus évocateur."
                        })
                        break
            elif lang != "fr" and w in WEAK_VERBS:
                weak_verbs.append({
                    "paragraph_index": p_idx,
                    "word": w,
                    "lemma": w,
                    "suggestion": f"The weak verb '{w}' could be replaced with a more descriptive action verb."
                })

    # Dialogue vs Narration stats
    dialogue_lines = 0
    total_lines = len(paragraphs)
    for p in paragraphs:
        # Dialogue indicators: starts with em-dash or quotation mark
        if p.startswith("—") or p.startswith("-") or p.startswith('"') or p.startswith('«'):
            dialogue_lines += 1

    dialogue_ratio = round((dialogue_lines / total_lines * 100), 1) if total_lines > 0 else 0

    # 3. Pacing Flags (Paragraph lengths and balance)
    for p_idx, p in enumerate(paragraphs):
        p_wcount = len(tokenize(p))
        if p_wcount > 150:
            pacing_flags.append({
                "paragraph_index": p_idx,
                "type": "long",
                "suggestion": f"Paragraphe très long ({p_wcount} mots). Pensez à le diviser pour aérer la lecture."
            })

    if dialogue_ratio > 70:
        pacing_flags.append({
            "paragraph_index": -1,
            "type": "chatty",
            "suggestion": "Scène très bavarde (plus de 70% de dialogues). Ajoutez des descriptions ou des actions physiques pour rythmer le dialogue."
        })
    elif dialogue_ratio < 15 and total_lines > 4:
        pacing_flags.append({
            "paragraph_index": -1,
            "type": "dense",
            "suggestion": "Scène très dense en narration (moins de 15% de dialogues). Pensez à introduire un échange parlé pour dynamiser le rythme."
        })

    return {
        "stats": {
            "word_count": total_words,
            "paragraph_count": total_lines,
            "dialogue_ratio": dialogue_ratio,
            "vocabulary_richness": vocab_richness
        },
        "repetitions": repetitions,
        "ment_adverbs": ment_adverbs,
        "weak_verbs": weak_verbs,
        "fillers": fillers,
        "dialogue_tags": dialogue_tags,
        "pacing_flags": pacing_flags,
        "grammar_flags": grammar_flags
    }
