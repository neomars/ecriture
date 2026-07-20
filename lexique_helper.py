# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = "lexique.db"

def get_word_details(word):
    """
    Retrieve all details for a given word form from lexique.db.
    Returns a list of dicts because a word can have multiple meanings/categories (e.g., 'coucher').
    """
    if not os.path.exists(DB_PATH):
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ortho, phon, lemme, cgram, genre, nombre, freqlemlivres, freqlivres, infover
            FROM lexique
            WHERE ortho = ?
        """, (word.strip().lower(),))
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append({
                "ortho": r[0],
                "phon": r[1],
                "lemme": r[2],
                "cgram": r[3],
                "genre": r[4],
                "nombre": r[5],
                "freqlemlivres": r[6],
                "freqlivres": r[7],
                "infover": r[8]
            })
        return results
    except Exception as e:
        print(f"Error querying lexique.db for details of '{word}': {e}")
        return []

def get_lemma(word):
    """
    Get the dictionary lemma of a word. If there are multiple, returns the most frequent one.
    Returns None if the word is not in the database.
    """
    details = get_word_details(word)
    if not details:
        return None

    # Sort by book frequency (freqlemlivres) descending to pick the most common lemma
    details_sorted = sorted(details, key=lambda x: x.get("freqlemlivres", 0.0), reverse=True)
    return details_sorted[0]["lemme"]

def get_synonyms_of_lemma_or_word(word, lang="fr"):
    """
    Extended search:
    1. Look up lemma of the word from lexique.db (if French).
    2. Retrieve synonyms for both the word and its lemma.
    3. Return consolidated list of unique synonyms.
    """
    from synonyms_db import get_synonyms

    # Simple fallback clean-up
    w_clean = word.lower().strip(".,!?;:\"'()[]{}«»")

    synonyms = set()

    # First, get basic synonyms
    for syn in get_synonyms(w_clean, lang=lang):
        synonyms.add(syn)

    if lang == "fr":
        lemma = get_lemma(w_clean)
        if lemma and lemma != w_clean:
            # Query synonyms of the lemma
            for syn in get_synonyms(lemma, lang=lang):
                synonyms.add(syn)

            # Query bidirectional synonyms for the lemma
            from synonyms_db import SYNONYMS_DATA
            lang_key = "fr"
            for key, values in SYNONYMS_DATA[lang_key].items():
                normalized_values = [v.lower().strip(".,!?;:\"'()[]{}«»") for v in values]
                if lemma in normalized_values:
                    if key != w_clean and key != lemma:
                        synonyms.add(key)
                    for val in values:
                        if val != w_clean and val != lemma:
                            synonyms.add(val)

    return sorted(list(synonyms))
