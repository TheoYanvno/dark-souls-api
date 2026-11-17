"""Every SQL statement in the app lives here. Routes call these functions and never write SQL."""

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


