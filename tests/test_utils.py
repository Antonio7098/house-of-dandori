import pytest
from src.core.utils import clean_location, text_to_list, to_json, parse_json_fields


def test_clean_location():
    assert clean_location("Harrogate, UK") == "Harrogate"
    assert clean_location("Oxford Botanical Gardens") == "Oxford"
    assert clean_location("London") == "London"
    assert clean_location(None) is None
    assert clean_location("") == ""


def test_text_to_list():
    assert text_to_list("item1\nitem2\nitem3") == ["item1", "item2", "item3"]
    assert text_to_list("• item1\n• item2") == ["item1", "item2"]
    assert text_to_list("- item1\n* item2") == ["item1", "item2"]
    assert text_to_list(None) is None
    assert text_to_list("") is None
    assert text_to_list("\n\n") is None


def test_to_json():
    assert to_json({"key": "value"}) == '{"key": "value"}'
    assert to_json(["a", "b"]) == '["a", "b"]'
    assert to_json(None) is None


def test_parse_json_fields():
    course = {
        "id": 1,
        "title": "Test",
        "learning_objectives": '["obj1", "obj2"]',
        "provided_materials": '["material1"]',
        "skills": '["skill1"]',
    }
    result = parse_json_fields(course)
    assert result["learning_objectives"] == ["obj1", "obj2"]
    assert result["provided_materials"] == ["material1"]
    assert result["skills"] == ["skill1"]

    result2 = parse_json_fields(None)
    assert result2 is None
