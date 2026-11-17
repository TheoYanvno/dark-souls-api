# Dark Souls REST API

A REST API for Dark Souls (2011). Browse the game's areas, bosses and starting classes, then make your own characters and track every boss they beat and every place they died. It tells you which required bosses are left, how many Lord Souls you hold and whether the Kiln is open.

Built with **Python, Flask and SQLite**. Flask is the only package to install.

![tests](https://github.com/TheoYanvno/dark-souls-api/actions/workflows/tests.yml/badge.svg)

## Run it (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py              # API at http://127.0.0.1:5000
python -m unittest         # 25 tests
```

On macOS or Linux, activate with `source .venv/bin/activate` and use `python3` in place of `python`.

The database (`souls.db`) is created on first start and the game data is loaded into it. Starting again updates the game data and never touches your characters.

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
| GET | `/api/characters` | Your characters |
| POST | `/api/characters` | Make a character: `{"name": "Solaire", "class": "knight"}` (201). It starts at the class's level. |
| GET | `/api/characters/<id>` | One character and the bosses they've beaten |
| PATCH | `/api/characters/<id>` | Change `name` or `level` (from the class's starting level up to 713) |
| DELETE | `/api/characters/<id>` | Delete a character and their history (204) |
| POST | `/api/characters/<id>/victories` | Record a boss: `{"boss": "taurus-demon"}` (201). Already beaten: 409. |
| DELETE | `/api/characters/<id>/victories/<slug>` | Undo a victory (204) |
| POST | `/api/characters/<id>/deaths` | Record a death: `{"area": "blighttown", "cause": "fell"}` (201) |
| GET | `/api/characters/<id>/deaths` | Deaths per area, worst first |
| GET | `/api/characters/<id>/progress` | Bosses beaten, required bosses left, Lord Souls, whether the Kiln is open, deaths and the deadliest area |
| GET | `/api/health` | `{"status": "ok"}` |

Errors always come back as `{"errors": ["..."]}` with the right status code: 400 lists every problem with what you sent, 404 says what wasn't found, 409 means it's already recorded.

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/characters/1/progress
```

```json
{
  "bosses_beaten": 4,
  "bosses_total": 22,
  "required_remaining": ["taurus-demon", "bell-gargoyles", "..."],
  "lord_souls": 4,
  "kiln_open": true,
  "deaths": 3,
  "deadliest_area": "blighttown"
}
```

## The game data

`data/` holds the 22 areas, 22 bosses and 10 starting classes of the base game as JSON. **Required** means a boss you have to beat to reach the end in a normal playthrough. Sequence breaks aside, these are the twelve bosses the game makes you fight, including the four Lord Soul holders (Gravelord Nito, Seath the Scaleless, the Four Kings and the Bed of Chaos) and Gwyn. The Artorias of the Abyss DLC isn't included yet.

## How it's built

```
souls/
  __init__.py   create_app(): config, JSON errors for 404 and 405, closes the database after each request
  db.py         the schema and loading data/*.json (safe to run again)
  store.py      every SQL statement, always with ? placeholders
  validate.py   checks request bodies and returns every problem at once
  routes.py     the endpoints: read the request, validate, call the store, pick the status code
tests/          25 tests with Flask's test client, each on its own temporary database
```

- **Six tables.** `areas`, `bosses` and `classes` hold the game. `characters` holds yours, and `victories` and `deaths` link them to bosses and areas with foreign keys.
- **The database enforces the rules.** `victories` has the primary key `(character_id, boss)`, so a boss can't be counted twice. Deleting a character cascades to its victories and deaths.
- **Thin routes.** No SQL in the routes and no HTTP in the store, so each part can change without breaking the other.
- **Safe search.** `%` and `_` in a search are escaped, so they're matched as text.
- **Runs the same everywhere.** Tests run on Windows and Ubuntu in GitHub Actions.

## What I'd add next

- The Artorias of the Abyss DLC areas and bosses
- Weapons and armor, and builds that check stat requirements
- Accounts so each player sees only their own characters

## AI tools

Built with help from AI coding tools for planning, code review and tests. Every feature is reviewed and tested before it ships.

## License

MIT. Dark Souls is a trademark of Bandai Namco Entertainment and FromSoftware. This is an unofficial fan project.
