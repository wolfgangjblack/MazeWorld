import json
from unittest.mock import patch
from src.generate.generate_llm_primatives import (
    generate_personality_primative,
    generate_npc_convo,
    generate_image_description,
)


SAMPLE_PERSONALITY = {
    "name": "Arin",
    "job": "hunter",
    "personality": "cheerful",
    "hobby": "tracking",
    "environment": "forest",
    "environment_name": "Iron Oak",
}


@patch("src.generate.generate_llm_primatives.generate")
def test_personality_primative_parses_json(mock_generate):
    mock_generate.return_value = json.dumps({
        "name": "helena", "job": "herbalist",
        "personality": "mysterious", "hobby": "collecting herbs"
    })
    env = {"environment": {"type": "forest", "name": "Iron Oak"}}
    result = generate_personality_primative(env)
    assert result["name"] == "helena"
    assert result["environment"] == "forest"
    assert result["environment_name"] == "Iron Oak"


@patch("src.generate.generate_llm_primatives.generate")
def test_personality_primative_parses_local_format(mock_generate):
    mock_generate.return_value = (
        "some preamble\n========================================\n"
        "##Output: {'name': 'khalid', 'job': 'merchant', "
        "'personality': 'charming', 'hobby': 'haggling'}\n========"
    )
    env = {"environment": {"type": "desert", "name": "Sandstone"}}
    result = generate_personality_primative(env)
    assert result["name"] == "khalid"
    assert result["environment"] == "desert"


@patch("src.generate.generate_llm_primatives.generate")
def test_personality_primative_returns_error_on_failure(mock_generate):
    mock_generate.return_value = "totally unparseable garbage"
    env = {"environment": {"type": "city", "name": "Test"}}
    result = generate_personality_primative(env)
    assert "error" in result


@patch("src.generate.generate_llm_primatives.generate")
def test_generate_npc_convo_returns_string(mock_generate):
    mock_generate.return_value = "Hello, welcome to the forest!"
    result = generate_npc_convo(SAMPLE_PERSONALITY.copy())
    assert isinstance(result, str)
    assert len(result) > 0


@patch("src.generate.generate_llm_primatives.generate")
def test_image_description_contains_style_prefix(mock_generate):
    mock_generate.return_value = "A cheerful hunter standing in a lush forest"
    result = generate_image_description(SAMPLE_PERSONALITY)
    assert result.startswith("masterpiece")
    assert "pixel art" in result
    assert "cheerful hunter" in result


@patch("src.generate.generate_llm_primatives.generate")
def test_image_description_extracts_from_local_format(mock_generate):
    mock_generate.return_value = (
        "preamble\n##Output: A stoic ranger in iron armor\nmore stuff"
    )
    result = generate_image_description(SAMPLE_PERSONALITY)
    assert "stoic ranger" in result
    assert result.startswith("masterpiece")
