import unittest
import json
import os
from main import app, PROJECT_FILE

class TestEcritureWebApp(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        self.client = app.test_client()

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
        self.assertIn(b'=== Pride & Prejudice', response.data)

if __name__ == '__main__':
    unittest.main()
