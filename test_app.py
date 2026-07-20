import unittest
import json
import os
from main import app

class TestEcritureWebApp(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        self.client = app.test_client()
        # Save initial active project
        res = self.client.get('/api/projects/active')
        self.initial_active = json.loads(res.data).get('active_filename')

    def tearDown(self):
        # Restore initial active project
        if hasattr(self, 'initial_active') and self.initial_active:
            self.client.post('/api/projects/active',
                             data=json.dumps({"filename": self.initial_active}),
                             content_type='application/json')

    def test_home_page(self):
        """Test that the index route loads the SPA HTML correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'DOCTYPE html', response.data)
        self.assertIn(b'tailwind', response.data)

    def test_get_project_api(self):
        """Test getting current project data from JSON."""
        response = self.client.get('/api/project')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('settings', data)
        self.assertIn('manuscript', data)
        self.assertIn('plot', data)

    def test_save_project_api(self):
        """Test posting updated project data to save it."""
        # Get current project state
        res_get = self.client.get('/api/project')
        project_data = json.loads(res_get.data)

        # Modify some value
        original_title = project_data['settings']['title']
        project_data['settings']['title'] = "Test Novel Title"

        # Post change
        res_post = self.client.post('/api/project',
                                    data=json.dumps(project_data),
                                    content_type='application/json')
        self.assertEqual(res_post.status_code, 200)
        post_result = json.loads(res_post.data)
        self.assertEqual(post_result['status'], 'success')
        self.assertEqual(post_result['data']['settings']['title'], "Test Novel Title")

        # Revert change to preserve state
        project_data['settings']['title'] = original_title
        self.client.post('/api/project',
                         data=json.dumps(project_data),
                         content_type='application/json')

    def test_get_locale_api(self):
        """Test loading translation dynamic mappings."""
        # French translation
        res_fr = self.client.get('/api/locale/fr')
        self.assertEqual(res_fr.status_code, 200)
        fr_data = json.loads(res_fr.data)
        self.assertIn('app_title', fr_data)
        self.assertEqual(fr_data['app_title'], 'Écriture')

        # English translation
        res_en = self.client.get('/api/locale/en')
        self.assertEqual(res_en.status_code, 200)
        en_data = json.loads(res_en.data)
        self.assertIn('app_title', en_data)
        self.assertEqual(en_data['app_title'], 'Ecriture')

        # Fallback to English for invalid locales
        res_invalid = self.client.get('/api/locale/xyz')
        self.assertEqual(res_invalid.status_code, 200)
        invalid_data = json.loads(res_invalid.data)
        self.assertEqual(invalid_data['app_title'], 'Ecriture')

    def test_export_api(self):
        """Test exporting text draft of manuscript."""
        response = self.client.post('/api/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/plain')
        self.assertTrue(response.data.startswith(b'==='))

    def test_export_formats(self):
        """Test exporting other formats."""
        for fmt, mimetype in [
            ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            ('pdf', 'application/pdf'),
            ('odt', 'application/vnd.oasis.opendocument.text'),
            ('epub', 'application/epub+zip'),
            ('mobi', 'application/x-mobipocket-ebook')
        ]:
            response = self.client.post('/api/export', json={'format': fmt})
            self.assertEqual(response.status_code, 200, f"Failed for format: {fmt}")
            self.assertEqual(response.mimetype, mimetype, f"Mimetype mismatch for: {fmt}")
            self.assertTrue(len(response.data) > 0, f"Empty response data for: {fmt}")

    def test_ai_tools_api(self):
        """Test contextual AI tools endpoints (Describe, Rewrite, Expand)."""
        # Test Describe
        resp = self.client.post('/api/ai', json={'tool': 'describe', 'text': 'Un sombre château'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('message', data)
        self.assertIn('Une description', data['message'])

        # Test Rewrite
        resp = self.client.post('/api/ai', json={'tool': 'rewrite', 'style': 'dramatic', 'text': 'Il pleut'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('tragique', data['message'])

        # Test Expand
        resp = self.client.post('/api/ai', json={'tool': 'expand', 'text': 'The door opened'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('Expanded', data['message'])

        # Test Error on empty text
        resp = self.client.post('/api/ai', json={'tool': 'describe', 'text': ''})
        self.assertEqual(resp.status_code, 400)

    def test_list_projects_api(self):
        """Test getting lists of projects."""
        response = self.client.get('/api/projects')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)

    def test_get_active_project_api(self):
        """Test getting active project filename."""
        response = self.client.get('/api/projects/active')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('active_filename', data)

    def test_create_project_api(self):
        """Test creating a new project."""
        payload = {"title": "Test Creation Novel"}
        response = self.client.post('/api/projects/create',
                                    data=json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('filename', data)
        self.assertEqual(data['data']['settings']['title'], "Test Creation Novel")

    def test_delete_project_api(self):
        """Test deleting a project."""
        payload = {"title": "Project to Delete"}
        res_create = self.client.post('/api/projects/create',
                                      data=json.dumps(payload),
                                      content_type='application/json')
        data_create = json.loads(res_create.data)
        filename = data_create['filename']

        res_delete = self.client.post('/api/projects/delete',
                                      data=json.dumps({"filename": filename}),
                                      content_type='application/json')
        self.assertEqual(res_delete.status_code, 200)
        data_delete = json.loads(res_delete.data)
        self.assertEqual(data_delete['status'], 'success')

    def test_ai_chat_api(self):
        """Test the AI Chat offline fallback."""
        payload = {
            "messages": [
                {"role": "user", "content": "Peux-tu m'aider à faire un plan ?"}
            ],
            "model": "llama3"
        }
        response = self.client.post('/api/ai/chat',
                                    data=json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('message', data)
        self.assertIn('model', data)

    def test_ai_custom_params(self):
        """Test that /api/ai and /api/ai/chat accept temperature and custom model parameters."""
        # /api/ai custom parameters
        resp = self.client.post('/api/ai', json={
            'tool': 'describe',
            'text': 'Un sombre château',
            'temperature': 0.3,
            'model': 'gemma2'
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('status', data)
        self.assertIn('message', data)

        # /api/ai/chat custom parameters
        payload = {
            "messages": [
                {"role": "user", "content": "Peux-tu m'aider ?"}
            ],
            "model": "mistral",
            "temperature": 0.9
        }
        response = self.client.post('/api/ai/chat',
                                    data=json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('message', data)

    def test_ai_models_endpoint(self):
        """Test that the /api/ai/models endpoint returns the expected model status/list."""
        response = self.client.get('/api/ai/models')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('models', data)
        self.assertIsInstance(data['models'], list)

    def test_synonyms_endpoint(self):
        """Test the synonyms endpoint which integrates lexique.sql lemmatization."""
        # Empty input
        resp = self.client.post('/api/synonyms', json={'word': '', 'lang': 'fr'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['synonyms'], [])

        # Verb in conjugated form (e.g., 'contemplait' -> 'contempler')
        resp = self.client.post('/api/synonyms', json={'word': 'contemplait', 'lang': 'fr'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('regarder', data['synonyms'])
        self.assertIn('observer', data['synonyms'])
        self.assertTrue(len(data['details']) > 0)
        self.assertEqual(data['details'][0]['lemme'], 'contempler')
        self.assertEqual(data['details'][0]['cgram'], 'VER')

        # English lookup
        resp = self.client.post('/api/synonyms', json={'word': 'happy', 'lang': 'en'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('joyful', data['synonyms'])

if __name__ == '__main__':
    unittest.main()
