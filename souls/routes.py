"""The endpoints. Each one reads the request, asks validate.py for problems, calls store.py, and picks
the status code."""
from flask import Blueprint, current_app, g, jsonify, request

from . import db, store, validate

api = Blueprint("api", __name__)


def conn():
    if "conn" not in g:
        g.conn = db.connect(current_app.config["DATABASE"])
    return g.conn


def errors(status, *messages):
    return jsonify({"errors": list(messages)}), status


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def page_args():
    problems = []
    values = {}
    for name, default, top in (("page", 1, None), ("per_page", 20, 100)):
        raw = request.args.get(name, str(default))
        if not raw.isdigit() or int(raw) < 1:
            problems.append(f"{name} must be a whole number of at least 1")
        elif top and int(raw) > top:
            problems.append(f"{name} must be at most {top}")
        else:
            values[name] = int(raw)
    return values, problems


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


# --- game data -------------------------------------------------------------------------------

@api.get("/areas")
def areas():
    return jsonify(store.list_areas(conn()))


@api.get("/areas/<slug>")
def area(slug):
    found = store.get_area(conn(), slug)
    return jsonify(found) if found else errors(404, f"no area '{slug}'")


@api.get("/bosses")
def bosses():
    paging, problems = page_args()
    required = request.args.get("required")
    if required not in (None, "true", "false"):
        problems.append("required must be true or false")
    area = request.args.get("area")
    if area and not store.area_exists(conn(), area):
        problems.append(f"area '{area}' does not exist")
    if problems:
        return errors(400, *problems)
    total, results = store.search_bosses(
        conn(), q=request.args.get("q", "").strip(), area=area,
        required=None if required is None else required == "true", **paging)
    pages = (total + paging["per_page"] - 1) // paging["per_page"]
    return jsonify({"total": total, **paging, "pages": pages, "results": results})


@api.get("/bosses/<slug>")
def boss(slug):
    found = store.get_boss(conn(), slug)
    return jsonify(found) if found else errors(404, f"no boss '{slug}'")


@api.get("/classes")
def classes():
    return jsonify(store.list_classes(conn()))


# --- characters --------------------------------------------------------------------------------

def find_character(character_id):
    return store.get_character(conn(), character_id)


@api.get("/characters")
def characters():
    return jsonify(store.list_characters(conn()))


@api.post("/characters")
def create_character():
    data = body()
    if data is None:
        return errors(400, "send a JSON object")
    problems = validate.new_character(data, lambda c: store.get_class(conn(), c) is not None)
    if problems:
        return errors(400, *problems)
    created = store.create_character(conn(), data["name"].strip(), data["class"])
    return jsonify(created), 201, {"Location": f"/api/characters/{created['id']}"}


@api.get("/characters/<int:character_id>")
def character(character_id):
    found = find_character(character_id)
    if not found:
        return errors(404, f"no character {character_id}")
    return jsonify({**found, "victories": store.list_victories(conn(), character_id)})


@api.patch("/characters/<int:character_id>")
def change_character(character_id):
    found = find_character(character_id)
    if not found:
        return errors(404, f"no character {character_id}")
    data = body()
    if data is None:
        return errors(400, "send a JSON object")
    start = store.get_class(conn(), found["class"])["level"]
    problems = validate.character_changes(data, start)
    if problems:
        return errors(400, *problems)
    if "name" in data:
        data["name"] = data["name"].strip()
    return jsonify(store.update_character(conn(), character_id, data))


@api.delete("/characters/<int:character_id>")
def remove_character(character_id):
    if not store.delete_character(conn(), character_id):
        return errors(404, f"no character {character_id}")
    return "", 204


@api.post("/characters/<int:character_id>/victories")
def add_victory(character_id):
    if not find_character(character_id):
        return errors(404, f"no character {character_id}")
    data = body()
    slug = data.get("boss") if data else None
    if not isinstance(slug, str) or not slug:
        return errors(400, "boss is required (see GET /api/bosses)")
    if not store.get_boss(conn(), slug):
        return errors(404, f"no boss '{slug}'")
    if not store.add_victory(conn(), character_id, slug):
        return errors(409, f"character {character_id} has already beaten {slug}")
    return jsonify(store.progress(conn(), character_id)), 201


@api.delete("/characters/<int:character_id>/victories/<slug>")
def remove_victory(character_id, slug):
    if not find_character(character_id):
        return errors(404, f"no character {character_id}")
    if not store.remove_victory(conn(), character_id, slug):
        return errors(404, f"character {character_id} hasn't beaten '{slug}'")
    return "", 204


@api.post("/characters/<int:character_id>/deaths")
def add_death(character_id):
    if not find_character(character_id):
        return errors(404, f"no character {character_id}")
    data = body()
    if data is None:
        return errors(400, "send a JSON object")
    problems = validate.new_death(data, lambda a: store.area_exists(conn(), a))
    if problems:
        return errors(400, *problems)
    return jsonify(store.add_death(conn(), character_id, data["area"], data.get("cause"))), 201


@api.get("/characters/<int:character_id>/deaths")
def deaths(character_id):
    if not find_character(character_id):
        return errors(404, f"no character {character_id}")
    return jsonify(store.deaths_by_area(conn(), character_id))


@api.get("/characters/<int:character_id>/progress")
def progress(character_id):
    if not find_character(character_id):
        return errors(404, f"no character {character_id}")
    return jsonify(store.progress(conn(), character_id))
