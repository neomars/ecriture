# -*- coding: utf-8 -*-

SYNONYMS_DATA = {
    "fr": {
        "dire": ["murmurer", "chuchoter", "déclarer", "affirmer", "prononcer", "articuler", "s'exclamer", "répliquer", "s'écrier", "rétorquer", "confier", "avouer", "admettre"],
        "dis": ["murmure", "chuchote", "déclare", "affirme", "prononce", "réplique", "rétorque", "confie", "avoue"],
        "dit": ["murmure", "chuchote", "déclare", "affirme", "prononce", "réplique", "rétorque", "confie", "avoue"],
        "parler": ["discuter", "converser", "s'entretenir", "deviser", "bavarder", "discourir", "s'exprimer", "bafouiller"],
        "faire": ["accomplir", "réaliser", "concevoir", "créer", "fabriquer", "façonner", "exécuter", "produire", "bâtir", "élaborer"],
        "aller": ["se rendre", "se diriger", "marcher", "s'acheminer", "courir", "s'élancer", "filer", "se propulser"],
        "regarder": ["observer", "contempler", "dévisager", "fixer", "scruter", "mirer", "toiser", "examiner", "épier", "guetter"],
        "contempler": ["regarder", "observer", "dévisager", "fixer", "scruter", "mirer", "toiser", "examiner", "épier", "guetter"],
        "voir": ["apercevoir", "distinguer", "discerner", "remarquer", "constater", "observer", "repérer", "entrevoir"],
        "prendre": ["saisir", "empoigner", "capturer", "dérober", "s'emparer de", "acquérir", "confisquer", "attraper"],
        "donner": ["offrir", "accorder", "octroyer", "conférer", "remettre", "léguer", "distribuer", "procurer", "céder"],
        "grand": ["immense", "gigantesque", "colossal", "vaste", "imposant", "majestueux", "démesuré", "gigantesque", "glorieux"],
        "petit": ["minuscule", "infime", "exigu", "modeste", "imperceptible", "restreint", "étroit", "lilliputien"],
        "beau": ["magnifique", "superbe", "splendide", "ravissant", "joli", "gracieux", "esthétique", "somptueux", "admirable"],
        "belle": ["magnifique", "superbe", "splendide", "ravissante", "jolie", "gracieuse", "esthétique", "somptueuse", "admirable"],
        "laid": ["affreux", "hideux", "disgracieux", "monstrueux", "répugnant", "vilain", "difforme"],
        "triste": ["mélancolique", "affligé", "chagriné", "sombre", "abattu", "éploré", "nostalgique", "morose", "déprimé", "accablé"],
        "joyeux": ["gai", "ravi", "enchanté", "enthousiaste", "jubilant", "jovial", "radieux", "enjoué", "allègre", "heureux"],
        "heureux": ["ravi", "enchanté", "enthousiaste", "jubilant", "jovial", "radieux", "enjoué", "joyeux", "comblé"],
        "colère": ["fureur", "courroux", "rage", "indignation", "irritation", "emportement", "exaspération"],
        "fâché": ["irrité", "furieux", "en colère", "indigné", "outré", "courroucé", "agacé"],
        "peur": ["effroi", "terreur", "angoisse", "panique", "appréhension", "inquiétude", "frayeur", "anxiété", "crainte"],
        "sombre": ["obscur", "ténébreux", "opaque", "terne", "lugubre", "sinistre", "ténébreuse", "ombrageux"],
        "froid": ["glacial", "gelé", "frais", "rigoureux", "distant", "insensible", "frigide", "impassible"],
        "chaud": ["brûlant", "torride", "tiède", "chaleureux", "ardent", "passionné", "bouillant"],
        "vieux": ["ancien", "âgé", "séculaire", "antique", "usé", "vétuste", "ancestral", "immémorial"],
        "jeune": ["adolescent", "juvénile", "vigoureux", "novice", "frais", "pubère"],
        "rapide": ["véloce", "prompt", "agile", "fulgurant", "expéditif", "hâtif", "rapide", "soudain"],
        "lent": ["tardif", "paresseux", "lourd", "nonchalant", "posé", "indolent"],
        "amour": ["passion", "affection", "tendresse", "attachement", "adoration", "penchant", "idylle", "flamme"]
    },
    "en": {
        "say": ["whisper", "mutter", "declare", "state", "utter", "exclaim", "reply", "retort", "assert", "remark", "announce"],
        "said": ["whispered", "muttered", "declared", "stated", "uttered", "exclaimed", "replied", "retorted", "asserted"],
        "tell": ["inform", "narrate", "relate", "reveal", "disclose", "explain", "recount", "notify", "advise"],
        "ask": ["inquire", "query", "question", "demand", "request", "beg", "implore", "petition"],
        "yell": ["shout", "scream", "screech", "bellow", "howl", "cry out", "shriek", "roar"],
        "whisper": ["mutter", "mumble", "breathe", "murmur", "hiss"],
        "run": ["sprint", "dash", "race", "scurry", "flee", "bolt", "hasten", "scamper", "gallop"],
        "walk": ["stroll", "amble", "march", "pace", "wander", "saunter", "hike", "tread"],
        "look": ["gaze", "stare", "glance", "peer", "squint", "observe", "scan", "behold", "gawk"],
        "see": ["behold", "perceive", "spot", "notice", "observe", "glimpse", "discern", "witness", "view"],
        "take": ["grab", "size", "grasp", "snatch", "capture", "acquire", "seize", "steal"],
        "give": ["offer", "bestow", "grant", "present", "hand over", "donate", "provide", "yield"],
        "make": ["create", "craft", "build", "construct", "produce", "fashion", "generate", "compose"],
        "go": ["travel", "depart", "proceed", "head", "move", "venture", "journey", "advance"],
        "happy": ["joyful", "cheerful", "delighted", "ecstatic", "jubilant", "thrilled", "merry", "glad", "elated"],
        "sad": ["melancholy", "gloomy", "sorrowful", "dejected", "blue", "heartbroken", "downcast", "despondent"],
        "angry": ["furious", "enraged", "irritated", "wrathful", "resentful", "indignant", "pissed", "irate"],
        "scared": ["terrified", "frightened", "afraid", "anxious", "panicked", "fearful", "petrified", "startled"],
        "beautiful": ["gorgeous", "lovely", "stunning", "attractive", "exquisite", "pretty", "handsome", "magnificent"],
        "ugly": ["hideous", "unsightly", "grotesque", "repulsive", "unattractive", "homely", "grim"],
        "great": ["wonderful", "fantastic", "marvelous", "outstanding", "superb", "immense", "terrific", "splendid"],
        "bad": ["terrible", "awful", "dreadful", "poor", "wicked", "harmful", "nasty", "vile"],
        "small": ["tiny", "minuscule", "miniature", "petite", "microscopic", "insignificant", "minute", "slight"],
        "big": ["huge", "large", "massive", "gigantic", "colossal", "immense", "enormous", "tremendous"],
        "dark": ["shadowy", "dim", "gloomy", "obscure", "black", "somber", "murky"],
        "cold": ["chilly", "freezing", "icy", "frigid", "detached", "indifferent", "frosty", "bleak"],
        "hot": ["burning", "scorching", "boiling", "fiery", "warm", "passionate", "sizzling", "humid"],
        "old": ["ancient", "elderly", "aged", "antique", "outdated", "archaic", "venerable"],
        "young": ["youthful", "juvenile", "fresh", "immature", "inexperienced", "adolescent"],
        "fast": ["quick", "rapid", "swift", "fleet", "hasty", "brisk", "speedy", "accelerated"],
        "slow": ["sluggish", "unhurried", "leisurely", "steady", "delayed", "ponderous", "slack"],
        "love": ["passion", "affection", "adoration", "devotion", "fondness", "infatuation", "attachment"]
    }
}

import os

def normalize_word(word, lang):
    """Normalized conversion (lemmatization) to query key."""
    if not word:
        return ""

    # Lowercase and strip whitespace/punctuation
    w = word.lower().strip(".,!?;:\"'()[]{}«»")

    if lang == "fr":
        # Try querying the sqlite lexique database first
        db_path = "lexique.db"
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT lemme FROM lexique WHERE ortho = ? LIMIT 1", (w,))
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    return row[0].lower().strip()
            except Exception:
                pass

        # Handle simple plural ending 's' or 'x'
        if w.endswith("s") and len(w) > 3:
            if w[:-1] in SYNONYMS_DATA["fr"]:
                return w[:-1]
            if w.endswith("es") and len(w) > 4:
                if w[:-2] + "er" in SYNONYMS_DATA["fr"]:
                    return w[:-2] + "er"
            if w.endswith("ais") and len(w) > 5:
                if w[:-3] + "er" in SYNONYMS_DATA["fr"]:
                    return w[:-3] + "er"
        if w.endswith("x") and len(w) > 3:
            if w[:-1] in SYNONYMS_DATA["fr"]:
                return w[:-1]

        # Handle feminine or verb endings
        if w.endswith("ent") and len(w) > 5:
            if w[:-3] + "er" in SYNONYMS_DATA["fr"]:
                return w[:-3] + "er"
        if w.endswith("ait") and len(w) > 5:
            if w[:-3] + "er" in SYNONYMS_DATA["fr"]:
                return w[:-3] + "er"
        if w.endswith("ant") and len(w) > 5:
            if w[:-3] + "er" in SYNONYMS_DATA["fr"]:
                return w[:-3] + "er"
        if w.endswith("ez") and len(w) > 4:
            if w[:-2] + "er" in SYNONYMS_DATA["fr"]:
                return w[:-2] + "er"
        if w.endswith("e") and len(w) > 3:
            if w[:-1] + "er" in SYNONYMS_DATA["fr"]:
                return w[:-1] + "er"
            if w[:-1] in SYNONYMS_DATA["fr"]:
                return w[:-1]
    else:
        # Handle English simple plurals or verb endings (e.g., 'says' -> 'say', 'runs' -> 'run', 'looking' -> 'look')
        if w.endswith("s") and len(w) > 3:
            if w[:-1] in SYNONYMS_DATA["en"]:
                return w[:-1]
        if w.endswith("ing") and len(w) > 4:
            if w[:-3] in SYNONYMS_DATA["en"]:
                return w[:-3]
            if w[:-3] + "e" in SYNONYMS_DATA["en"]:
                return w[:-3] + "e"
        if w.endswith("ed") and len(w) > 4:
            if w[:-2] in SYNONYMS_DATA["en"]:
                return w[:-2]
            if w[:-1] in SYNONYMS_DATA["en"]:
                return w[:-1]

    return w

def get_synonyms(word, lang="fr"):
    """Lookup and return synonyms list for a word, or empty list if none found."""
    lang_key = "fr" if lang == "fr" else "en"

    w_clean = word.lower().strip(".,!?;:\"'()[]{}«»")
    norm = normalize_word(word, lang_key)

    results = []

    # 1. Direct or normalized match in keys
    if w_clean in SYNONYMS_DATA[lang_key]:
        results.extend(SYNONYMS_DATA[lang_key][w_clean])
    elif norm in SYNONYMS_DATA[lang_key]:
        results.extend(SYNONYMS_DATA[lang_key][norm])

    # 2. Bidirectional match (check if word is a value in any list of synonyms)
    for key, values in SYNONYMS_DATA[lang_key].items():
        # Match either exact or normalized representation in lists of synonyms
        normalized_values = [v.lower().strip(".,!?;:\"'()[]{}«»") for v in values]
        if w_clean in normalized_values or norm in normalized_values:
            # Add the key itself if it is not the searched word
            if key not in results and key != w_clean and key != norm:
                results.append(key)
            # Add other synonyms from this list
            for val in values:
                val_clean = val.lower().strip(".,!?;:\"'()[]{}«»")
                if val not in results and val_clean != w_clean and val_clean != norm:
                    results.append(val)

    return results
