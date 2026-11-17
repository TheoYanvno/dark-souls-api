"""Checks for request bodies. Each returns a list of every problem, so a client can fix them all at once."""

NAME_MAX = 30
LEVEL_MAX = 713          # the highest soul level in Dark Souls


def _name_problems(body):
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return ["name is required and must be text"]
    if len(name.strip()) > NAME_MAX:
        return [f"name must be at most {NAME_MAX} characters"]
    return []


def new_character(body, class_exists):
    problems = _name_problems(body)
    cls = body.get("class")
    if not isinstance(cls, str) or not cls:
        problems.append("class is required (see GET /api/classes)")
    elif not class_exists(cls):
        problems.append(f"class '{cls}' is not a starting class (see GET /api/classes)")
    return problems


def character_changes(body, start_level):
    problems = []
    unknown = sorted(set(body) - {"name", "level"})
    if unknown:
        problems.append(f"only name and level can change, not: {', '.join(unknown)}")
    if not set(body) & {"name", "level"}:
        problems.append("send name or level to change")
    if "name" in body:
        problems += _name_problems(body)
    if "level" in body:
        level = body["level"]
        if not isinstance(level, int) or isinstance(level, bool):
            problems.append("level must be a whole number")
        elif not start_level <= level <= LEVEL_MAX:
            problems.append(f"level must be between {start_level} (this class's starting level) and {LEVEL_MAX}")
    return problems


def new_death(body, area_exists):
    problems = []
    area = body.get("area")
    if not isinstance(area, str) or not area:
        problems.append("area is required (see GET /api/areas)")
    elif not area_exists(area):
        problems.append(f"area '{area}' does not exist (see GET /api/areas)")
    cause = body.get("cause")
    if cause is not None and (not isinstance(cause, str) or len(cause) > 100):
        problems.append("cause must be text of at most 100 characters")
    return problems
