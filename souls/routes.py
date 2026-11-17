"""The endpoints. Each one reads the request, checks it, calls store.py, and picks the status code."""
from flask import Blueprint, current_app, g, jsonify, request

from . import db, store

api = Blueprint("api", __name__)


def conn():
    if "conn" not in g:
        g.conn = db.connect(current_app.config["DATABASE"])
    return g.conn


def errors(status, *messages):
    return jsonify({"errors": list(messages)}), status


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


