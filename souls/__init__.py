"""Dark Souls REST API: browse the game's areas, bosses and starting classes."""
from flask import Flask, g, jsonify

from . import db
from .routes import api


def create_app(database="souls.db"):
    app = Flask(__name__)
    app.config["DATABASE"] = str(database)
    app.json.sort_keys = False
    db.init(app.config["DATABASE"])

    @app.teardown_appcontext
    def close(_exc):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"errors": ["no such endpoint"]}), 404

    @app.errorhandler(405)
    def wrong_method(_e):
        return jsonify({"errors": ["that method isn't allowed here"]}), 405

    app.register_blueprint(api, url_prefix="/api")
    return app
