"""Every SQL statement in the app lives here. Routes call these functions and never write SQL."""

LORD_SOULS = 4


def _boss(row):
    return {"slug": row["slug"], "name": row["name"], "area": row["area"],
            "required": bool(row["required"]), "lord_soul": bool(row["lord_soul"])}


# --- game data -------------------------------------------------------------------------------

def list_areas(conn):
    rows = conn.execute(
        "SELECT a.slug, a.name, COUNT(b.slug) AS bosses FROM areas a "
        "LEFT JOIN bosses b ON b.area = a.slug GROUP BY a.slug ORDER BY a.rowid").fetchall()
    return [dict(r) for r in rows]


def get_area(conn, slug):
    row = conn.execute("SELECT slug, name FROM areas WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        return None
    bosses = conn.execute("SELECT * FROM bosses WHERE area = ? ORDER BY position", (slug,)).fetchall()
    return {**dict(row), "bosses": [_boss(b) for b in bosses]}


def area_exists(conn, slug):
    return conn.execute("SELECT 1 FROM areas WHERE slug = ?", (slug,)).fetchone() is not None


def search_bosses(conn, q=None, area=None, required=None, page=1, per_page=20):
    where, args = [], []
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("name LIKE ? ESCAPE '\\'")
        args.append(f"%{escaped}%")
    if area:
        where.append("area = ?")
        args.append(area)
    if required is not None:
        where.append("required = ?")
        args.append(1 if required else 0)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM bosses {clause}", args).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM bosses {clause} ORDER BY position LIMIT ? OFFSET ?",
                        [*args, per_page, (page - 1) * per_page]).fetchall()
    return total, [_boss(r) for r in rows]


def get_boss(conn, slug):
    row = conn.execute("SELECT * FROM bosses WHERE slug = ?", (slug,)).fetchone()
    return _boss(row) if row else None


def list_classes(conn):
    return [dict(r) for r in conn.execute("SELECT slug, name, level FROM classes ORDER BY rowid")]


def get_class(conn, slug):
    row = conn.execute("SELECT slug, name, level FROM classes WHERE slug = ?", (slug,)).fetchone()
    return dict(row) if row else None


# --- characters --------------------------------------------------------------------------------

def _character(row):
    return {"id": row["id"], "name": row["name"], "class": row["class"], "level": row["level"],
            "created_at": row["created_at"]}


def create_character(conn, name, class_slug):
    start = get_class(conn, class_slug)["level"]
    with conn:
        cur = conn.execute("INSERT INTO characters (name, class, level) VALUES (?, ?, ?)",
                           (name, class_slug, start))
    return get_character(conn, cur.lastrowid)


def list_characters(conn):
    return [_character(r) for r in conn.execute("SELECT * FROM characters ORDER BY id")]


def get_character(conn, character_id):
    row = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
    return _character(row) if row else None


def update_character(conn, character_id, fields):
    allowed = {k: fields[k] for k in ("name", "level") if k in fields}
    if allowed:
        sets = ", ".join(f"{k} = ?" for k in allowed)          # keys come from the fixed list above
        with conn:
            conn.execute(f"UPDATE characters SET {sets} WHERE id = ?", [*allowed.values(), character_id])
    return get_character(conn, character_id)


def delete_character(conn, character_id):
    with conn:
        return conn.execute("DELETE FROM characters WHERE id = ?", (character_id,)).rowcount > 0


# --- victories and deaths ----------------------------------------------------------------------

def add_victory(conn, character_id, boss):
    """True if recorded, False if this character had already beaten that boss."""
    with conn:
        cur = conn.execute("INSERT OR IGNORE INTO victories (character_id, boss) VALUES (?, ?)",
                           (character_id, boss))
    return cur.rowcount == 1


def remove_victory(conn, character_id, boss):
    with conn:
        return conn.execute("DELETE FROM victories WHERE character_id = ? AND boss = ?",
                            (character_id, boss)).rowcount > 0


def list_victories(conn, character_id):
    rows = conn.execute(
        "SELECT b.*, v.beaten_at FROM victories v JOIN bosses b ON b.slug = v.boss "
        "WHERE v.character_id = ? ORDER BY v.beaten_at, b.position", (character_id,)).fetchall()
    return [{**_boss(r), "beaten_at": r["beaten_at"]} for r in rows]


def add_death(conn, character_id, area, cause):
    with conn:
        cur = conn.execute("INSERT INTO deaths (character_id, area, cause) VALUES (?, ?, ?)",
                           (character_id, area, cause))
    row = conn.execute("SELECT * FROM deaths WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def deaths_by_area(conn, character_id):
    rows = conn.execute(
        "SELECT a.slug AS area, a.name, COUNT(*) AS deaths FROM deaths d JOIN areas a ON a.slug = d.area "
        "WHERE d.character_id = ? GROUP BY a.slug ORDER BY deaths DESC, a.rowid", (character_id,)).fetchall()
    return [dict(r) for r in rows]


def progress(conn, character_id):
    rows = conn.execute(
        "SELECT b.*, v.boss IS NOT NULL AS beaten FROM bosses b "
        "LEFT JOIN victories v ON v.boss = b.slug AND v.character_id = ? ORDER BY b.position",
        (character_id,)).fetchall()
    required = [r for r in rows if r["required"]]
    lord_souls = sum(1 for r in rows if r["lord_soul"] and r["beaten"])
    by_area = deaths_by_area(conn, character_id)
    return {
        "bosses_beaten": sum(1 for r in rows if r["beaten"]),
        "bosses_total": len(rows),
        "required_remaining": [r["slug"] for r in required if not r["beaten"]],
        "lord_souls": lord_souls,
        "kiln_open": lord_souls == LORD_SOULS,
        "deaths": sum(a["deaths"] for a in by_area),
        "deadliest_area": by_area[0]["area"] if by_area else None,
    }
