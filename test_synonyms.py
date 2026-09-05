import unittest
import json
from main import app, get_synonyms

class TestSynonyms(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_get_synonyms_fr(self):
        # test the python function
        res = get_synonyms("bonjour", "fr")
        self.assertIn("salut", res)

    def test_api_synonyms_fr(self):
        # test the api endpoint
        response = self.client.post('/api/synonyms',
            data=json.dumps({"word": "bonjour", "lang": "fr"}),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("synonyms", data)
        self.assertIn("salut", data["synonyms"])

    def test_api_synonyms_en(self):
        # test the api endpoint
        response = self.client.post('/api/synonyms',
            data=json.dumps({"word": "hello", "lang": "en"}),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("synonyms", data)
        self.assertIn("hi", data["synonyms"])

if __name__ == '__main__':
    unittest.main()
