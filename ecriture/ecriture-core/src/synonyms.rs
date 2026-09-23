//! Synonym lookup.
//!
//! - French: the same `lexique.db` SQLite database the Python app ships
//!   (WOLF synonym pairs + the "Lexique" French lemma table), see
//!   [`SynonymDb`]. Ports `main.py::get_synonyms` for the `fr` case.
//! - English: `thesaurus_en.db`, built from Princeton WordNet 3.0 by
//!   `scripts/build_thesaurus_en.py` (the data the Python app used through
//!   NLTK), see [`EnglishThesaurus`].
//!
//! Spanish and Russian have no bundled data yet and return an empty list.

use rusqlite::Connection;
use std::path::Path;

#[derive(Debug, thiserror::Error)]
pub enum SynonymError {
    #[error("database error: {0}")]
    Db(#[from] rusqlite::Error),
}

pub type Result<T> = std::result::Result<T, SynonymError>;

pub struct SynonymDb {
    conn: Connection,
}

const MAX_RESULTS: usize = 20;

impl SynonymDb {
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let conn = Connection::open(path)?;
        Ok(Self { conn })
    }

    pub fn open_in_memory_for_tests() -> Self {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute_batch(
            "CREATE TABLE synonyms (word TEXT, synonym TEXT);
             CREATE TABLE lexique (ortho TEXT, phon TEXT, lemme TEXT, cgram TEXT, genre TEXT, nombre TEXT, freqlemlivres REAL, freqlivres REAL, infover TEXT);",
        )
        .unwrap();
        Self { conn }
    }

    #[cfg(test)]
    fn seed(&self, word: &str, synonym: &str) {
        self.conn
            .execute(
                "INSERT INTO synonyms (word, synonym) VALUES (?1, ?2)",
                rusqlite::params![word, synonym],
            )
            .unwrap();
    }

    #[cfg(test)]
    fn seed_lemma(&self, ortho: &str, lemme: &str) {
        self.conn
            .execute(
                "INSERT INTO lexique (ortho, lemme) VALUES (?1, ?2)",
                rusqlite::params![ortho, lemme],
            )
            .unwrap();
    }

    /// Looks up synonyms for `word` in the given `lang`. Currently only
    /// `fr` is backed by real data; any other language yields an empty
    /// list (see module docs).
    pub fn lookup(&self, word: &str, lang: &str) -> Result<Vec<String>> {
        if lang != "fr" {
            return Ok(Vec::new());
        }

        let cleaned = clean_word(word);
        if cleaned.is_empty() {
            return Ok(Vec::new());
        }

        let mut synonyms = self.synonyms_for(&cleaned)?;

        // Fall back through the word's lemma, exactly like the Python
        // implementation: if "mangeait" has no direct synonym row but its
        // lemma "manger" does, surface those too.
        if let Some(lemma) = self.lemma_for(&cleaned)? {
            if lemma != cleaned {
                for syn in self.synonyms_for(&lemma)? {
                    if syn != cleaned && !synonyms.contains(&syn) {
                        synonyms.push(syn);
                    }
                }
            }
        }

        synonyms.truncate(MAX_RESULTS);
        Ok(synonyms)
    }

    fn synonyms_for(&self, word: &str) -> Result<Vec<String>> {
        let mut stmt = self
            .conn
            .prepare("SELECT DISTINCT synonym FROM synonyms WHERE word = ?1 LIMIT ?2")?;
        let rows = stmt.query_map(rusqlite::params![word, MAX_RESULTS as i64], |row| {
            row.get::<_, String>(0)
        })?;
        let mut out = Vec::new();
        for r in rows {
            let s = r?;
            if !s.is_empty() {
                out.push(s);
            }
        }
        Ok(out)
    }

    fn lemma_for(&self, word: &str) -> Result<Option<String>> {
        let mut stmt = self
            .conn
            .prepare("SELECT lemme FROM lexique WHERE ortho = ?1 LIMIT 1")?;
        let mut rows = stmt.query(rusqlite::params![word])?;
        if let Some(row) = rows.next()? {
            let lemme: Option<String> = row.get(0)?;
            return Ok(lemme.map(|l| l.to_lowercase().trim().to_string()));
        }
        Ok(None)
    }
}

/// English synonyms from WordNet (`thesaurus_en.db`, see module docs).
pub struct EnglishThesaurus {
    conn: Connection,
}

/// Parts of speech, as encoded in synset ids (`synset / 100_000_000`).
const NOUN: i64 = 1;
const VERB: i64 = 2;
const ADJ: i64 = 3;

/// WordNet's "morphy" detachment rules: (part of speech, suffix,
/// replacement), applied to find the base form of an inflected word.
const MORPHY_RULES: &[(i64, &str, &str)] = &[
    (NOUN, "s", ""), (NOUN, "ses", "s"), (NOUN, "xes", "x"), (NOUN, "zes", "z"),
    (NOUN, "ches", "ch"), (NOUN, "shes", "sh"), (NOUN, "men", "man"), (NOUN, "ies", "y"),
    (VERB, "s", ""), (VERB, "ies", "y"), (VERB, "es", "e"), (VERB, "es", ""),
    (VERB, "ed", "e"), (VERB, "ed", ""), (VERB, "ing", "e"), (VERB, "ing", ""),
    (ADJ, "er", ""), (ADJ, "est", ""), (ADJ, "er", "e"), (ADJ, "est", "e"),
];

impl EnglishThesaurus {
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let conn = Connection::open_with_flags(path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
        Ok(Self { conn })
    }

    /// An empty in-memory thesaurus with the real schema, for tests.
    pub fn open_in_memory_for_tests() -> Self {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute_batch(
            "CREATE TABLE senses (word TEXT, rank INTEGER, synset INTEGER, freq INTEGER DEFAULT 0, PRIMARY KEY (word, rank, synset));
             CREATE TABLE members (synset INTEGER, rank INTEGER, lemma TEXT, PRIMARY KEY (synset, rank));
             CREATE TABLE similar (synset INTEGER, target INTEGER);
             CREATE TABLE exceptions (form TEXT, base TEXT, pos INTEGER);",
        )
        .unwrap();
        Self { conn }
    }

    /// Up to 20 synonyms of `word`, most common senses first (by WordNet's
    /// corpus frequency, across nouns, verbs and adjectives): the words
    /// sharing a WordNet synset with it (or with its base form - "walked"
    /// looks up "walk"), then, for adjectives, words from "similar to"
    /// synsets ("beautiful" -> "gorgeous", "lovely"...).
    pub fn lookup(&self, word: &str) -> Result<Vec<String>> {
        let mut cleaned = clean_word(word);
        for possessive in ["'s", "\u{2019}s"] {
            if let Some(stripped) = cleaned.strip_suffix(possessive) {
                cleaned = stripped.to_string();
            }
        }
        if cleaned.is_empty() {
            return Ok(Vec::new());
        }

        let bases = self.base_forms(&cleaned)?;
        let mut synsets: Vec<i64> = Vec::new();
        for (base, pos) in &bases {
            let mut stmt = self.conn.prepare_cached(
                "SELECT synset FROM senses WHERE word = ?1 AND (?2 IS NULL OR synset / 100000000 = ?2)
                 ORDER BY freq DESC, rank, synset",
            )?;
            for synset in stmt.query_map(rusqlite::params![base, pos], |row| row.get::<_, i64>(0))? {
                let synset = synset?;
                if !synsets.contains(&synset) {
                    synsets.push(synset);
                }
            }
        }
        let bases: Vec<String> = bases.into_iter().map(|(base, _)| base).collect();
        let mut similar = Vec::new();
        for synset in &synsets {
            let mut stmt = self
                .conn
                .prepare_cached("SELECT target FROM similar WHERE synset = ?1 ORDER BY target")?;
            for target in stmt.query_map([synset], |row| row.get::<_, i64>(0))? {
                similar.push(target?);
            }
        }

        let mut out: Vec<String> = Vec::new();
        for synset in synsets.iter().chain(similar.iter()) {
            let mut stmt = self
                .conn
                .prepare_cached("SELECT lemma FROM members WHERE synset = ?1 ORDER BY rank")?;
            for lemma in stmt.query_map([synset], |row| row.get::<_, String>(0))? {
                let lemma = lemma?;
                let lower = lemma.to_lowercase();
                if lower == cleaned || bases.contains(&lower) || out.iter().any(|o| o.to_lowercase() == lower) {
                    continue;
                }
                out.push(lemma);
                if out.len() == MAX_RESULTS {
                    return Ok(out);
                }
            }
        }
        Ok(out)
    }

    /// The word itself (any part of speech) and/or its base forms with the
    /// part of speech they were derived for - "went" is only the verb "go",
    /// not the game of go - keeping only those WordNet knows: irregular
    /// forms first (from the exception lists), then the suffix rules.
    fn base_forms(&self, word: &str) -> Result<Vec<(String, Option<i64>)>> {
        let mut candidates: Vec<(String, Option<i64>)> = vec![(word.to_string(), None)];
        let mut stmt = self
            .conn
            .prepare_cached("SELECT base, pos FROM exceptions WHERE form = ?1")?;
        for row in stmt.query_map([word], |row| Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?)))? {
            let (base, pos) = row?;
            candidates.push((base, Some(pos)));
        }
        for (pos, suffix, replacement) in MORPHY_RULES {
            if let Some(stem) = word.strip_suffix(suffix) {
                if !stem.is_empty() {
                    candidates.push((format!("{stem}{replacement}"), Some(*pos)));
                }
            }
        }

        let mut known = Vec::new();
        let mut stmt = self.conn.prepare_cached(
            "SELECT 1 FROM senses WHERE word = ?1 AND (?2 IS NULL OR synset / 100000000 = ?2) LIMIT 1",
        )?;
        for candidate in candidates {
            if !known.contains(&candidate) && stmt.exists(rusqlite::params![candidate.0, candidate.1])? {
                known.push(candidate);
            }
        }
        Ok(known)
    }

    #[cfg(test)]
    fn seed_synset(&self, synset: i64, lemmas: &[&str]) {
        for (rank, lemma) in lemmas.iter().enumerate() {
            self.conn
                .execute("INSERT INTO members VALUES (?1, ?2, ?3)", rusqlite::params![synset, rank as i64, lemma])
                .unwrap();
            self.conn
                .execute(
                    "INSERT OR IGNORE INTO senses (word, rank, synset)
                     VALUES (?1, (SELECT COUNT(*) FROM senses WHERE word = ?1), ?2)",
                    rusqlite::params![lemma.to_lowercase(), synset],
                )
                .unwrap();
        }
    }
}

/// Lowercases and strips surrounding punctuation, mirroring the Python
/// `word.lower().strip().strip(".,!?;:\"'()[]{}«»").strip()` chain.
fn clean_word(word: &str) -> String {
    const PUNCT: &[char] = &['.', ',', '!', '?', ';', ':', '"', '\'', '(', ')', '[', ']', '{', '}', '«', '»'];
    word.trim()
        .to_lowercase()
        .trim_matches(|c| PUNCT.contains(&c) || c.is_whitespace())
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn english_lookup_returns_synset_members_without_the_word_itself() {
        let db = EnglishThesaurus::open_in_memory_for_tests();
        db.seed_synset(300_000_001, &["glad", "happy"]);
        db.seed_synset(300_000_002, &["felicitous", "happy"]);
        assert_eq!(db.lookup("Happy!").unwrap(), vec!["glad".to_string(), "felicitous".to_string()]);
    }

    #[test]
    fn english_lookup_follows_inflections_and_irregular_forms() {
        let db = EnglishThesaurus::open_in_memory_for_tests();
        db.seed_synset(200_000_001, &["walk", "stroll"]);
        db.seed_synset(200_000_002, &["go", "travel"]);
        db.seed_synset(100_000_003, &["lady", "dame"]);
        db.seed_synset(100_000_004, &["go", "game of go"]);
        db.conn.execute("INSERT INTO exceptions VALUES ('went', 'go', 2)", []).unwrap();

        assert_eq!(db.lookup("walked").unwrap(), vec!["stroll".to_string()]);
        assert_eq!(db.lookup("walking").unwrap(), vec!["stroll".to_string()]);
        assert_eq!(db.lookup("went").unwrap(), vec!["travel".to_string()]);
        assert_eq!(db.lookup("lady's").unwrap(), vec!["dame".to_string()]);
    }

    #[test]
    fn english_lookup_puts_the_most_frequent_sense_first() {
        let db = EnglishThesaurus::open_in_memory_for_tests();
        db.seed_synset(100_000_020, &["better", "bettor"]);
        db.seed_synset(300_000_021, &["better", "improved"]);
        db.conn.execute("UPDATE senses SET freq = 50 WHERE synset = 300000021", []).unwrap();
        assert_eq!(db.lookup("better").unwrap(), vec!["improved", "bettor"]);
    }

    #[test]
    fn english_lookup_adds_similar_adjectives_after_direct_synonyms() {
        let db = EnglishThesaurus::open_in_memory_for_tests();
        db.seed_synset(300_000_010, &["beautiful"]);
        db.seed_synset(300_000_011, &["gorgeous"]);
        db.seed_synset(300_000_012, &["lovely", "endearing"]);
        db.conn.execute("INSERT INTO similar VALUES (300000010, 300000011), (300000010, 300000012)", []).unwrap();
        assert_eq!(db.lookup("beautiful").unwrap(), vec!["gorgeous", "lovely", "endearing"]);
    }

    #[test]
    fn english_lookup_dedupes_and_caps_results() {
        let db = EnglishThesaurus::open_in_memory_for_tests();
        let many: Vec<String> = (0..30).map(|i| format!("syn{i}")).collect();
        let mut lemmas: Vec<&str> = vec!["word"];
        lemmas.extend(many.iter().map(String::as_str));
        db.seed_synset(100_000_001, &lemmas);
        db.seed_synset(100_000_002, &["word", "Syn0"]);
        let syns = db.lookup("word").unwrap();
        assert_eq!(syns.len(), 20);
        assert_eq!(syns.iter().filter(|s| s.to_lowercase() == "syn0").count(), 1);
    }

    #[test]
    fn bundled_english_thesaurus_has_real_synonyms() {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/resources/thesaurus_en.db");
        let db = EnglishThesaurus::open(path).expect("bundled thesaurus_en.db should open");
        let beautiful = db.lookup("beautiful").unwrap();
        assert!(beautiful.contains(&"lovely".to_string()), "{beautiful:?}");
        let walked = db.lookup("walked").unwrap();
        assert!(!walked.is_empty() && !walked.contains(&"walk".to_string()), "{walked:?}");
        let prejudices = db.lookup("prejudices").unwrap();
        assert!(prejudices.contains(&"bias".to_string()), "{prejudices:?}");
        let went = db.lookup("went").unwrap();
        assert!(went.contains(&"travel".to_string()) && !went.contains(&"ecstasy".to_string()), "{went:?}");
        assert!(db.lookup("xyzzyq").unwrap().is_empty());
    }

    #[test]
    fn clean_word_strips_punctuation_and_lowercases() {
        assert_eq!(clean_word("  Bonjour! "), "bonjour");
        assert_eq!(clean_word("«Salut»"), "salut");
        assert_eq!(clean_word(""), "");
    }

    #[test]
    fn lookup_returns_direct_synonyms() {
        let db = SynonymDb::open_in_memory_for_tests();
        db.seed("bonjour", "salut");
        db.seed("bonjour", "salutations");

        let syns = db.lookup("Bonjour!", "fr").unwrap();
        assert!(syns.contains(&"salut".to_string()));
        assert!(syns.contains(&"salutations".to_string()));
    }

    #[test]
    fn lookup_falls_back_to_lemma_synonyms() {
        let db = SynonymDb::open_in_memory_for_tests();
        db.seed_lemma("mangeait", "manger");
        db.seed("manger", "dévorer");

        let syns = db.lookup("mangeait", "fr").unwrap();
        assert_eq!(syns, vec!["dévorer".to_string()]);
    }

    #[test]
    fn lookup_merges_direct_and_lemma_results_without_duplicates() {
        let db = SynonymDb::open_in_memory_for_tests();
        db.seed("belle", "jolie");
        db.seed_lemma("belle", "beau");
        db.seed("beau", "jolie"); // duplicate across direct + lemma
        db.seed("beau", "magnifique");

        let syns = db.lookup("belle", "fr").unwrap();
        assert_eq!(syns.iter().filter(|s| *s == "jolie").count(), 1);
        assert!(syns.contains(&"magnifique".to_string()));
    }

    #[test]
    fn lookup_returns_empty_for_unsupported_languages() {
        let db = SynonymDb::open_in_memory_for_tests();
        db.seed("hello", "hi");
        assert_eq!(db.lookup("hello", "en").unwrap(), Vec::<String>::new());
        assert_eq!(db.lookup("hola", "es").unwrap(), Vec::<String>::new());
    }

    #[test]
    fn lookup_returns_empty_for_blank_word() {
        let db = SynonymDb::open_in_memory_for_tests();
        assert_eq!(db.lookup("   ", "fr").unwrap(), Vec::<String>::new());
    }

    #[test]
    fn lookup_caps_results_at_twenty() {
        let db = SynonymDb::open_in_memory_for_tests();
        for i in 0..30 {
            db.seed("mot", &format!("syn{i}"));
        }
        assert_eq!(db.lookup("mot", "fr").unwrap().len(), 20);
    }
}
