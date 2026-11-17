import os
import tempfile
import unittest

from souls import create_app, db


class ApiTest(unittest.TestCase):
    def setUp(self):
        # ignore_cleanup_errors: Windows can't delete a file another handle still has open
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = os.path.join(self.tmp.name, "test.db")
        self.client = create_app(self.path).test_client()

    def tearDown(self):
        self.tmp.cleanup()


class GameDataTest(ApiTest):
    def test_health(self):
        self.assertEqual(self.client.get("/api/health").get_json(), {"status": "ok"})

    def test_areas_count_their_bosses(self):
        areas = {a["slug"]: a for a in self.client.get("/api/areas").get_json()}
        self.assertEqual(len(areas), 22)
        self.assertEqual(areas["demon-ruins"]["bosses"], 3)
        self.assertEqual(areas["firelink-shrine"]["bosses"], 0)

    def test_one_area_lists_its_bosses_in_order(self):
        area = self.client.get("/api/areas/anor-londo").get_json()
        self.assertEqual([b["slug"] for b in area["bosses"]], ["ornstein-and-smough", "dark-sun-gwyndolin"])

    def test_unknown_area_is_404(self):
        response = self.client.get("/api/areas/drangleic")
        self.assertEqual(response.status_code, 404)
        self.assertIn("errors", response.get_json())

    def test_bosses_filter_and_pages(self):
        data = self.client.get("/api/bosses?required=true&per_page=5&page=3").get_json()
        self.assertEqual((data["total"], data["pages"], len(data["results"])), (12, 3, 2))
        self.assertEqual(data["results"][-1]["slug"], "gwyn-lord-of-cinder")

    def test_bosses_search_by_name_and_area(self):
        data = self.client.get("/api/bosses?q=demon&area=demon-ruins").get_json()
        self.assertEqual([b["slug"] for b in data["results"]], ["demon-firesage", "centipede-demon"])

    def test_search_treats_percent_as_text(self):
        self.assertEqual(self.client.get("/api/bosses?q=%25").get_json()["total"], 0)

    def test_bad_query_lists_every_problem(self):
        response = self.client.get("/api/bosses?page=0&per_page=500&required=maybe&area=nowhere")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.get_json()["errors"]), 4)

    def test_four_lord_souls(self):
        bosses = self.client.get("/api/bosses?per_page=100").get_json()["results"]
        self.assertEqual(sorted(b["slug"] for b in bosses if b["lord_soul"]),
                         ["bed-of-chaos", "four-kings", "gravelord-nito", "seath-the-scaleless"])

    def test_classes(self):
        classes = {c["slug"]: c["level"] for c in self.client.get("/api/classes").get_json()}
        self.assertEqual(len(classes), 10)
        self.assertEqual((classes["pyromancer"], classes["deprived"]), (1, 6))

    def test_loading_twice_changes_nothing(self):
        db.init(self.path)
        self.assertEqual(len(self.client.get("/api/areas").get_json()), 22)
        self.assertEqual(self.client.get("/api/bosses").get_json()["total"], 22)

    def test_unknown_endpoint_and_method_answer_json(self):
        self.assertEqual(self.client.get("/api/nope").status_code, 404)
        response = self.client.put("/api/bosses")
        self.assertEqual(response.status_code, 405)
        self.assertIn("errors", response.get_json())


if __name__ == "__main__":
    unittest.main()
