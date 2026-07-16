import unittest
import os
import json
from project_manager import NovelProject

class TestNovelProject(unittest.TestCase):
    def setUp(self):
        self.test_filename = "test_novel_project_temp.json"
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)
        self.project = NovelProject(self.test_filename)

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_default_data(self):
        # Verify that default data contains manuscript and plot setup
        data = self.project.data
        self.assertIn("settings", data)
        self.assertIn("manuscript", data)
        self.assertIn("plot", data)
        self.assertEqual(data["settings"]["title"], "Pride & Prejudice (Copy)")

    def test_recalculate_word_counts(self):
        self.project.data["manuscript"] = [
            {
                "id": "chap_1",
                "type": "chapter",
                "title": "Chapter 1",
                "children": [
                    {
                        "id": "scene_1",
                        "type": "scene",
                        "title": "Scene 1",
                        "content": "Hello world! This is a test of the word count."
                    }
                ]
            }
        ]
        self.project.recalculate_word_counts()
        self.assertEqual(self.project.data["settings"]["overall_written"], 10)

    def test_find_node(self):
        # Find existing scene node
        node = self.project.find_node("scene_1_1")
        self.assertIsNotNone(node)
        self.assertEqual(node["title"], "Netherfield Park is let at last")

        # Find non-existent node
        node = self.project.find_node("non_existent_node")
        self.assertIsNone(node)

    def test_add_chapter(self):
        new_chap = self.project.add_chapter("Chapter 3")
        self.assertIsNotNone(new_chap)
        self.assertTrue(new_chap["id"].startswith("chap_"))
        self.assertEqual(new_chap["title"], "Chapter 3")

        # Verify it was added to the manuscript
        found_node = self.project.find_node(new_chap["id"])
        self.assertIsNotNone(found_node)
        self.assertEqual(found_node["title"], "Chapter 3")

    def test_add_scene(self):
        # Adding to existing chapter
        new_scene = self.project.add_scene("chap_1", "A New Scene")
        self.assertIsNotNone(new_scene)
        self.assertTrue(new_scene["id"].startswith("scene_"))
        self.assertEqual(new_scene["title"], "A New Scene")

        # Adding to non-existent chapter
        failed_scene = self.project.add_scene("invalid_chap_id", "Failed Scene")
        self.assertIsNone(failed_scene)

    def test_delete_node(self):
        # Test deleting scene
        # Verify plot card exists first
        self.assertTrue(any(c["scene_id"] == "scene_1_1" for c in self.project.data["plot"]["cards"]))

        success = self.project.delete_node("scene_1_1")
        self.assertTrue(success)

        # Verify scene node is gone
        self.assertIsNone(self.project.find_node("scene_1_1"))

        # Verify associated plot cards are gone
        self.assertFalse(any(c["scene_id"] == "scene_1_1" for c in self.project.data["plot"]["cards"]))

    def test_save_and_load(self):
        self.project.data["settings"]["title"] = "Persuasion"
        self.project.save()

        # Check file was written
        self.assertTrue(os.path.exists(self.test_filename))

        # Load file in another project instance
        new_project = NovelProject(self.test_filename)
        self.assertEqual(new_project.data["settings"]["title"], "Persuasion")

    def test_custom_plot_card_fields(self):
        # Verify characters and links associations are correctly retained on save and load
        card = self.project.data["plot"]["cards"][0]
        card["characters"] = ["char_1", "char_3"]
        card["links"] = ["card_2"]

        self.project.save()

        new_project = NovelProject(self.test_filename)
        loaded_card = new_project.data["plot"]["cards"][0]
        self.assertIn("characters", loaded_card)
        self.assertEqual(loaded_card["characters"], ["char_1", "char_3"])
        self.assertIn("links", loaded_card)
        self.assertEqual(loaded_card["links"], ["card_2"])

if __name__ == "__main__":
    unittest.main()
