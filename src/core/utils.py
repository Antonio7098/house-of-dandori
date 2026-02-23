import json
from typing import List, Optional

from src.core.config import LOCATION_CLEANUP


def clean_location(location: Optional[str]) -> Optional[str]:
    if not location:
        return location
    return LOCATION_CLEANUP.get(location, location)


def text_to_list(text: Optional[str]) -> Optional[List[str]]:
    if not text:
        return None
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        stripped = line.lstrip("•·-* ").strip()
        if stripped:
            items.append(stripped)
    return items if items else None


def to_json(val):
    return json.dumps(val) if val is not None else None


def parse_json_fields(course):
    if not course:
        return course
    json_fields = ["learning_objectives", "provided_materials", "skills"]
    result = dict(course) if not isinstance(course, dict) else course.copy()
    for field in json_fields:
        val = result.get(field)
        if val and isinstance(val, str):
            try:
                result[field] = json.loads(val)
            except json.JSONDecodeError:
                pass
    return result
