# Dark Souls REST API

A REST API for Dark Souls (2011). Browse the game's areas, bosses and starting classes, search the bosses and filter them by area or by whether the game makes you fight them.

Built with **Python, Flask and SQLite**. Flask is the only package to install.

![tests](https://github.com/TheoYanvno/dark-souls-api/actions/workflows/tests.yml/badge.svg)

## Run it (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py              # API at http://127.0.0.1:5000
python -m unittest         # 12 tests
```

On macOS or Linux, activate with `source .venv/bin/activate` and use `python3` in place of `python`.

The database (`souls.db`) is created on first start and the game data is loaded into it. Starting again updates the game data.

### VS Code

Open the folder and install the recommended extensions when asked. **Terminal → Run Task** has *Install*, *Start the API* and *Run the tests*, **F5** starts the API in the debugger, and `requests.http` has a request for each endpoint that you can send with the REST Client extension.

## The API

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/areas` | Every area and how many bosses it has |
| GET | `/api/areas/<slug>` | One area and its bosses |
| GET | `/api/bosses` | Bosses in the order you'd usually meet them. Optional `q` (words in the name), `area`, `required` (`true`/`false`), `page`, `per_page` (up to 100). |
| GET | `/api/bosses/<slug>` | One boss |
| GET | `/api/classes` | The ten starting classes and their starting levels |
| GET | `/api/health` | `{"status": "ok"}` |

Errors always come back as `{"errors": ["..."]}` with the right status code: 400 lists every problem with what you sent and 404 says what wasn't found.

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/api/bosses?required=true&per_page=3"
```

## The game data

`data/` holds the 22 areas, 22 bosses and 10 starting classes of the base game as JSON. **Required** means a boss you have to beat to reach the end in a normal playthrough. Sequence breaks aside, these are the twelve bosses the game makes you fight, including the four Lord Soul holders (Gravelord Nito, Seath the Scaleless, the Four Kings and the Bed of Chaos) and Gwyn. The Artorias of the Abyss DLC isn't included yet.

## How it's built

```
souls/
  __init__.py   create_app(): config, JSON errors for 404 and 405, closes the database after each request
  db.py         the schema and loading data/*.json (safe to run again)
  store.py      every SQL statement, always with ? placeholders
  routes.py     the endpoints: read the request, validate, call the store, pick the status code
tests/          12 tests with Flask's test client, each on its own temporary database
```

- **Three tables.** `areas`, `bosses` and `classes`, with each boss linked to its area by a foreign key.
- **Thin routes.** No SQL in the routes and no HTTP in the store, so each part can change without breaking the other.
- **Safe search.** `%` and `_` in a search are escaped, so they're matched as text.
- **Runs the same everywhere.** Tests run on Windows and Ubuntu in GitHub Actions.

## What I'd add next

- The Artorias of the Abyss DLC areas and bosses
- Weapons and armor, and builds that check stat requirements
- Characters of your own that track the bosses they beat and where they died

## AI tools

Built with help from AI coding tools for planning, code review and tests. Every feature is reviewed and tested before it ships.

## License

MIT. Dark Souls is a trademark of Bandai Namco Entertainment and FromSoftware. This is an unofficial fan project.
