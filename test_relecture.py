# -*- coding: utf-8 -*-
import unittest
import json
import os
from main import app
from relecture_analyzer import analyze_scene_text

class TestRelectureWorkspace(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_local_analyzer(self):
        """Test local rule-based relecture analysis functions."""
        text = "Elle aimait contempler le coucher de soleil.  Soudain, elle dit de manière extrêmement rapide et elle était un peu fatiguée."
        report = analyze_scene_text(text, lang="fr")

        # Verify stats
        self.assertIn("stats", report)
        self.assertEqual(report["stats"]["paragraph_count"], 1)

        # Verify repetitions of word "elle"
        reps = [r["word"] for r in report["repetitions"]]
        self.assertIn("elle", reps)

        # Verify adverb en -ment
        ments = [m["word"] for m in report["ment_adverbs"]]
        self.assertIn("extrêmement", ments)

        # Verify weak verbs (dit, était)
        weak_lemmas = [w["lemma"] for w in report["weak_verbs"]]
        self.assertIn("être", weak_lemmas)
        self.assertIn("dire", weak_lemmas)

        # Verify fillers
        fillers = [f["word"] for f in report["fillers"]]
        self.assertIn("un peu", fillers)
        self.assertIn("soudain", fillers)

        # Verify typography double spaces flag
        grammar = [g["text"] for g in report["grammar_flags"]]
        self.assertIn("Espaces doubles", grammar)

    def test_api_relecture_analyze(self):
        """Test the Flask /api/relecture/analyze endpoint."""
        # Querying with a valid scene id from Corneille's Le Cid
        resp = self.client.post('/api/relecture/analyze', json={
            "scene_id": "scene_acte1_1",
            "lang": "fr"
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("stats", data)
        self.assertIn("repetitions", data)
        self.assertIn("weak_verbs", data)

    def test_api_relecture_ai(self):
        """Test the Flask /api/relecture/ai endpoint and offline fallback routing."""
        # Style category review
        resp = self.client.post('/api/relecture/ai', json={
            "scene_id": "scene_acte1_1",
            "category": "style",
            "lang": "fr"
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("status", data)
        self.assertIn("feedback", data)
        self.assertIn("Show vs Tell", data["feedback"])

        # Coherence category review
        resp = self.client.post('/api/relecture/ai', json={
            "scene_id": "scene_acte1_1",
            "category": "coherence",
            "lang": "fr"
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("Cohérence", data["feedback"])

        # Pacing category review
        resp = self.client.post('/api/relecture/ai', json={
            "scene_id": "scene_acte1_1",
            "category": "rythme",
            "lang": "fr"
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("Rythme", data["feedback"])

if __name__ == "__main__":
    unittest.main()
