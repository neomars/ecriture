import json
import os

class NovelProject:
    """
    Manages the novel project structure, loading and saving, and provides interface
    to interact with the manuscript, plot, characters, and story notes.
    """
    def __init__(self, filepath=None):
        self.filepath = filepath
        self.data = self.get_default_data()
        if filepath and os.path.exists(filepath):
            self.load()

    def get_default_data(self):
        return {
            "settings": {
                "title": "Pride & Prejudice (Copy)",
                "daily_goal": 500,
                "overall_goal": 50000,
                "overall_written": 0,
                "daily_written": 0
            },
            "manuscript": [
                {
                    "id": "chap_1",
                    "type": "chapter",
                    "title": "Chapter 1",
                    "summary": "Mr. Bingley, a wealthy single gentleman, rents Netherfield Park, exciting Mrs. Bennet who hopes he will marry one of her five daughters.",
                    "children": [
                        {
                            "id": "scene_1_1",
                            "type": "scene",
                            "title": "Netherfield Park is let at last",
                            "content": "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.\n\nHowever little known the feelings or views of such a man may be on his first entering a neighborhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters."
                        }
                    ]
                },
                {
                    "id": "chap_2",
                    "type": "chapter",
                    "title": "Chapter 2",
                    "summary": "Mr. Bennet visits Mr. Bingley in secret, surprising his family and demonstrating his affection for them.",
                    "children": [
                        {
                            "id": "scene_2_1",
                            "type": "scene",
                            "title": "We cannot escape the subject",
                            "content": "Mr. Bennet was among the earliest of those who waited on Mr. Bingley. He had always intended to visit him, though to the last always assuring his wife that he should not go; and till the evening after the visit was paid she had no knowledge of it."
                        }
                    ]
                }
            ],
            "plot": {
                "plotlines": [
                    {"id": "pl_1", "title": "Scenes"},
                    {"id": "pl_2", "title": "Romance"},
                    {"id": "pl_3", "title": "Scandal"},
                    {"id": "pl_4", "title": "Class"}
                ],
                "cards": [
                    {"id": "card_1", "plotline_id": "pl_1", "scene_id": "scene_1_1", "title": "Bingley Arrives", "content": "Bingley rents Netherfield Park, exciting Mrs. Bennet."},
                    {"id": "card_2", "plotline_id": "pl_2", "scene_id": "scene_1_1", "title": "First Spark", "content": "Jane and Bingley meet and there's immediate mutual interest."},
                    {"id": "card_3", "plotline_id": "pl_1", "scene_id": "scene_2_1", "title": "Mr. Bennet's Visit", "content": "Mr. Bennet reveals he has visited Bingley, surprising the family."}
                ]
            },
            "characters": [
                {
                    "id": "char_1",
                    "name": "Elizabeth Bennet",
                    "role": "Protagonist",
                    "description": "The second of the Bennet daughters. She is intelligent, lively, and quick-witted, but prone to forming quick judgments."
                },
                {
                    "id": "char_2",
                    "name": "Jane Bennet",
                    "role": "Supporting Character",
                    "description": "The eldest Bennet sister, sweet-tempered and beautiful, always thinking the best of everyone."
                },
                {
                    "id": "char_3",
                    "name": "Mr. Darcy",
                    "role": "Love Interest",
                    "description": "A wealthy gentleman, proud and socially awkward initially, but highly honorable."
                }
            ],
            "story_notes": [
                {
                    "id": "note_1",
                    "title": "Hertfordshire",
                    "type": "Location",
                    "content": "The county in Southern England where the Bennets and Bingleys live."
                },
                {
                    "id": "note_2",
                    "title": "Longbourn",
                    "type": "Location",
                    "content": "The Bennet family estate, entailed to Mr. Collins."
                }
            ],
            "key_events": [
                {
                    "id": "evt_1",
                    "title": "Mr. Bingley Rents Netherfield",
                    "description": "The news of Netherfield being let to a wealthy bachelor spreads across Hertfordshire.",
                    "chapter_id": "chap_1",
                    "characters": []
                }
            ]
        }

    def load(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            # Normalize loaded data to ensure backward compatibility
            if "key_events" not in self.data:
                self.data["key_events"] = []
            for chap in self.data.get("manuscript", []):
                if "summary" not in chap:
                    chap["summary"] = ""
        except Exception as e:
            print(f"Error loading project: {e}")

    def save(self):
        if not self.filepath:
            self.filepath = "my_novel_project.json"
        try:
            # Recalculate word counts
            self.recalculate_word_counts()
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving project: {e}")

    def recalculate_word_counts(self):
        total = 0
        def count_words(node):
            cnt = 0
            if "content" in node:
                cnt += len(node["content"].split())
            if "children" in node:
                for child in node["children"]:
                    cnt += count_words(child)
            return cnt

        for item in self.data["manuscript"]:
            total += count_words(item)
        self.data["settings"]["overall_written"] = total

    def find_node(self, node_id, list_to_search=None):
        if list_to_search is None:
            list_to_search = self.data["manuscript"]

        for item in list_to_search:
            if item["id"] == node_id:
                return item
            if "children" in item:
                found = self.find_node(node_id, item["children"])
                if found:
                    return found
        return None

    def add_chapter(self, title="New Chapter"):
        new_id = f"chap_{len(self.data['manuscript']) + 1}_{int(os.urandom(2).hex(), 16)}"
        new_chap = {
            "id": new_id,
            "type": "chapter",
            "title": title,
            "summary": "",
            "children": []
        }
        self.data["manuscript"].append(new_chap)
        return new_chap

    def add_scene(self, parent_chap_id, title="New Scene"):
        parent = self.find_node(parent_chap_id)
        if parent and parent["type"] == "chapter":
            new_id = f"scene_{len(parent['children']) + 1}_{int(os.urandom(2).hex(), 16)}"
            new_scene = {
                "id": new_id,
                "type": "scene",
                "title": title,
                "content": ""
            }
            parent["children"].append(new_scene)
            return new_scene
        return None

    def delete_node(self, node_id, list_to_search=None):
        if list_to_search is None:
            list_to_search = self.data["manuscript"]

        for idx, item in enumerate(list_to_search):
            if item["id"] == node_id:
                # Also delete associated plot cards if it's a scene
                if item["type"] == "scene":
                    self.data["plot"]["cards"] = [c for c in self.data["plot"]["cards"] if c["scene_id"] != node_id]
                list_to_search.pop(idx)
                return True
            if "children" in item:
                if self.delete_node(node_id, item["children"]):
                    return True
        return False
