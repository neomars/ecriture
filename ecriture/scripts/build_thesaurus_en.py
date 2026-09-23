#!/usr/bin/env python3
"""Builds the English thesaurus (ecriture-core/resources/thesaurus_en.db)
from Princeton WordNet 3.0 - the same data the Python version of Écriture
used through NLTK.

Usage:
    python3 scripts/build_thesaurus_en.py path/to/wordnet-dict-dir

The directory is WordNet's `dict` folder (data.*, index.*, *.exc), e.g. the
one in NLTK's `corpora/wordnet.zip`. Its LICENSE must ship with the app:
it is copied next to the database as WORDNET_LICENSE.txt.

Tables:
    senses(word, rank, synset, freq) - every sense of a word; rank is WordNet's
                                  per-part-of-speech order, freq its corpus
                                  frequency (tag count, used to rank across
                                  parts of speech)
    members(synset, rank, lemma)  - the words of each synset, in WordNet order
    similar(synset, target)       - adjective "similar to" links
    exceptions(form, base, pos)   - irregular forms (went -> go, mice -> mouse)

Synset ids are pos * 100_000_000 + WordNet offset (1 noun, 2 verb, 3 adj,
4 adv), so the part of speech is `synset / 100_000_000`.
"""
import shutil
import sqlite3
import sys
from pathlib import Path

RESOURCES = Path(__file__).resolve().parent.parent / "ecriture-core/resources"
OUT = RESOURCES / "thesaurus_en.db"
POS = {"noun": 1, "verb": 2, "adj": 3, "adv": 4}


def synset_id(pos_file, offset):
    return POS[pos_file] * 100_000_000 + int(offset)


def clean(lemma):
    lemma = lemma.split("(")[0]  # adjective markers: "galore(ip)"
    return lemma.replace("_", " ")


def parse_data(dict_dir, pos_file, members, similar):
    for line in (dict_dir / f"data.{pos_file}").read_text(encoding="latin-1").splitlines():
        if line.startswith("  "):
            continue  # license header
        fields = line.split(" | ")[0].split()
        sid = synset_id(pos_file, fields[0])
        w_cnt = int(fields[3], 16)
        words = fields[4:4 + 2 * w_cnt:2]
        for rank, word in enumerate(words):
            members.append((sid, clean(word), rank))
        p_cnt_index = 4 + 2 * w_cnt
        p_cnt = int(fields[p_cnt_index])
        for i in range(p_cnt):
            symbol, offset, pos = fields[p_cnt_index + 1 + 4 * i: p_cnt_index + 4 + 4 * i]
            if symbol == "&" and pos_file == "adj":
                similar.append((sid, synset_id("adj", offset)))


SS_TYPE_POS = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 3}  # 5 = adjective satellite


def sense_frequencies(dict_dir):
    """(word, synset) -> tag count, from index.sense."""
    freq = {}
    for line in (dict_dir / "index.sense").read_text(encoding="latin-1").splitlines():
        key, offset, _sense_number, tag_cnt = line.split()
        lemma, lex_sense = key.split("%")
        pos = SS_TYPE_POS[lex_sense[0]]
        freq[(clean(lemma).lower(), pos * 100_000_000 + int(offset))] = int(tag_cnt)
    return freq


def parse_index(dict_dir, pos_file, senses):
    for line in (dict_dir / f"index.{pos_file}").read_text(encoding="latin-1").splitlines():
        if line.startswith("  "):
            continue
        fields = line.split()
        word = clean(fields[0]).lower()
        synset_cnt = int(fields[2])
        offsets = fields[-synset_cnt:]
        for rank, offset in enumerate(offsets):
            senses.append((word, synset_id(pos_file, offset), rank))


def parse_exceptions(dict_dir):
    rows = []
    for pos_file in ("noun", "verb", "adj", "adv"):
        for line in (dict_dir / f"{pos_file}.exc").read_text(encoding="latin-1").splitlines():
            form, *bases = line.split()
            rows.extend((clean(form).lower(), clean(base).lower(), POS[pos_file]) for base in bases)
    return sorted(set(rows))


def main(dict_dir):
    dict_dir = Path(dict_dir)
    members, similar, senses = [], [], []
    for pos_file in POS:
        parse_data(dict_dir, pos_file, members, similar)
        parse_index(dict_dir, pos_file, senses)

    OUT.unlink(missing_ok=True)
    db = sqlite3.connect(OUT)
    # WITHOUT ROWID + composite primary keys: the key is the lookup index,
    # so words aren't stored twice (table + index).
    db.executescript("""
        CREATE TABLE senses (word TEXT NOT NULL, rank INTEGER NOT NULL, synset INTEGER NOT NULL,
                             freq INTEGER NOT NULL, PRIMARY KEY (word, rank, synset)) WITHOUT ROWID;
        CREATE TABLE members (synset INTEGER NOT NULL, rank INTEGER NOT NULL, lemma TEXT NOT NULL,
                              PRIMARY KEY (synset, rank)) WITHOUT ROWID;
        CREATE TABLE similar (synset INTEGER NOT NULL, target INTEGER NOT NULL,
                              PRIMARY KEY (synset, target)) WITHOUT ROWID;
        CREATE TABLE exceptions (form TEXT NOT NULL, base TEXT NOT NULL, pos INTEGER NOT NULL,
                                 PRIMARY KEY (form, base, pos)) WITHOUT ROWID;
    """)
    freq = sense_frequencies(dict_dir)
    db.executemany("INSERT OR IGNORE INTO senses VALUES (?, ?, ?, ?)",
                   [(w, r, sid, freq.get((w, sid), 0)) for w, sid, r in senses])
    db.executemany("INSERT INTO members VALUES (?, ?, ?)", [(sid, r, l) for sid, l, r in members])
    db.executemany("INSERT OR IGNORE INTO similar VALUES (?, ?)", similar)
    db.executemany("INSERT INTO exceptions VALUES (?, ?, ?)", parse_exceptions(dict_dir))
    db.commit()
    db.execute("VACUUM")
    db.close()
    shutil.copyfile(dict_dir / "LICENSE", RESOURCES / "WORDNET_LICENSE.txt")
    print(f"{OUT}: {len(senses)} senses, {len(members)} members, {len(similar)} similar links, "
          f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1])
