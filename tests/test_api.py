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

    def make(self, name="Solaire", cls="knight"):
        return self.client.post("/api/characters", json={"name": name, "class": cls}).get_json()


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
        self.make()
        db.init(self.path)
        self.assertEqual(len(self.client.get("/api/areas").get_json()), 22)
        self.assertEqual(len(self.client.get("/api/characters").get_json()), 1)

    def test_unknown_endpoint_and_method_answer_json(self):
        self.assertEqual(self.client.get("/api/nope").status_code, 404)
        response = self.client.put("/api/bosses")
        self.assertEqual(response.status_code, 405)
        self.assertIn("errors", response.get_json())


class CharacterTest(ApiTest):
    def test_create_starts_at_the_class_level(self):
        response = self.client.post("/api/characters", json={"name": "  Siegmeyer ", "class": "knight"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["Location"], "/api/characters/1")
        data = response.get_json()
        self.assertEqual((data["name"], data["level"]), ("Siegmeyer", 5))

    def test_create_lists_every_problem(self):
        response = self.client.post("/api/characters", json={"name": "x" * 31, "class": "bard"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.get_json()["errors"]), 2)

    def test_create_needs_a_json_object(self):
        self.assertEqual(self.client.post("/api/characters", data="hello").status_code, 400)
        self.assertEqual(self.client.post("/api/characters", json=[1, 2]).status_code, 400)

    def test_patch_changes_only_what_is_sent(self):
        self.make(cls="pyromancer")
        response = self.client.patch("/api/characters/1", json={"level": 40})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.get_json()["name"], response.get_json()["level"]), ("Solaire", 40))

    def test_patch_checks_level_and_fields(self):
        self.make(cls="deprived")
        bad = [{"level": 5}, {"level": 714}, {"level": True}, {"level": "9"}, {"souls": 9999}, {}]
        for change in bad:
            with self.subTest(change=change):
                self.assertEqual(self.client.patch("/api/characters/1", json=change).status_code, 400)

    def test_missing_character_is_404_everywhere(self):
        for method, path in [("get", "/api/characters/9"), ("patch", "/api/characters/9"),
                             ("delete", "/api/characters/9"), ("get", "/api/characters/9/progress"),
                             ("get", "/api/characters/9/deaths"),
                             ("post", "/api/characters/9/victories"), ("post", "/api/characters/9/deaths")]:
            with self.subTest(path=path, method=method):
                self.assertEqual(getattr(self.client, method)(path, json={}).status_code, 404)

    def test_delete_removes_victories_and_deaths(self):
        self.make()
        self.client.post("/api/characters/1/victories", json={"boss": "asylum-demon"})
        self.client.post("/api/characters/1/deaths", json={"area": "undead-burg"})
        self.assertEqual(self.client.delete("/api/characters/1").status_code, 204)
        conn = db.connect(self.path)
        counts = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("victories", "deaths")]
        conn.close()
        self.assertEqual(counts, [0, 0])


class ProgressTest(ApiTest):
    def test_victory_201_then_409(self):
        self.make()
        first = self.client.post("/api/characters/1/victories", json={"boss": "taurus-demon"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.get_json()["bosses_beaten"], 1)
        again = self.client.post("/api/characters/1/victories", json={"boss": "taurus-demon"})
        self.assertEqual(again.status_code, 409)

    def test_unknown_boss_and_missing_boss(self):
        self.make()
        self.assertEqual(self.client.post("/api/characters/1/victories", json={"boss": "nameless-king"}).status_code, 404)
        self.assertEqual(self.client.post("/api/characters/1/victories", json={}).status_code, 400)

    def test_undo_a_victory(self):
        self.make()
        self.client.post("/api/characters/1/victories", json={"boss": "pinwheel"})
        self.assertEqual(self.client.delete("/api/characters/1/victories/pinwheel").status_code, 204)
        self.assertEqual(self.client.delete("/api/characters/1/victories/pinwheel").status_code, 404)

    def test_kiln_opens_with_four_lord_souls(self):
        self.make()
        for boss in ["gravelord-nito", "seath-the-scaleless", "four-kings"]:
            self.client.post("/api/characters/1/victories", json={"boss": boss})
        self.assertFalse(self.client.get("/api/characters/1/progress").get_json()["kiln_open"])
        self.client.post("/api/characters/1/victories", json={"boss": "bed-of-chaos"})
        progress = self.client.get("/api/characters/1/progress").get_json()
        self.assertEqual((progress["lord_souls"], progress["kiln_open"]), (4, True))
        self.assertNotIn("bed-of-chaos", progress["required_remaining"])

    def test_deaths_by_area(self):
        self.make()
        for area in ["blighttown", "blighttown", "sens-fortress"]:
            r = self.client.post("/api/characters/1/deaths", json={"area": area, "cause": "fell"})
            self.assertEqual(r.status_code, 201)
        deaths = self.client.get("/api/characters/1/deaths").get_json()
        self.assertEqual([(d["area"], d["deaths"]) for d in deaths], [("blighttown", 2), ("sens-fortress", 1)])
        progress = self.client.get("/api/characters/1/progress").get_json()
        self.assertEqual((progress["deaths"], progress["deadliest_area"]), (3, "blighttown"))

    def test_bad_death(self):
        self.make()
        r = self.client.post("/api/characters/1/deaths", json={"area": "lordran", "cause": 5})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(r.get_json()["errors"]), 2)


if __name__ == "__main__":
    unittest.main()
