import json
from unittest.mock import patch

from src.generate.generators.llm_primitives import (
    generate_image_description,
    generate_npc_convo,
    generate_personality_primitive,
)
from src.prompts.base import LLMRequest

SAMPLE_PERSONALITY = {
    "name": "Arin",
    "job": "hunter",
    "personality": "cheerful",
    "hobby": "tracking",
    "environment": "forest",
    "environment_name": "Iron Oak",
}


@patch("src.generate.generators.llm_primitives.generate")
def test_personality_primitive_parses_json(mock_generate):
    mock_generate.return_value = json.dumps({
        "name": "helena", "job": "herbalist",
        "personality": "mysterious", "hobby": "collecting herbs"
    })
    env = {"environment": {"type": "forest", "name": "Iron Oak"}}
    result = generate_personality_primitive(env)
    assert result["name"] == "helena"
    assert result["environment"] == "forest"
    assert result["environment_name"] == "Iron Oak"


@patch("src.generate.generators.llm_primitives.generate")
def test_personality_primitive_parses_local_format(mock_generate):
    mock_generate.return_value = (
        "some preamble\n========================================\n"
        "##Output: {'name': 'khalid', 'job': 'merchant', "
        "'personality': 'charming', 'hobby': 'haggling'}\n========"
    )
    env = {"environment": {"type": "desert", "name": "Sandstone"}}
    result = generate_personality_primitive(env)
    assert result["name"] == "khalid"
    assert result["environment"] == "desert"


@patch("src.generate.generators.llm_primitives.generate")
def test_personality_primitive_returns_error_on_failure(mock_generate):
    mock_generate.return_value = "totally unparseable garbage"
    env = {"environment": {"type": "city", "name": "Test"}}
    result = generate_personality_primitive(env)
    assert "error" in result


@patch("src.generate.generators.llm_primitives.generate")
def test_generate_npc_convo_extracts_response(mock_generate):
    mock_generate.return_value = (
        "preamble\n##Output: Welcome to the forest, traveler!\nmore stuff"
    )
    result = generate_npc_convo(SAMPLE_PERSONALITY.copy())

    assert result == "Welcome to the forest, traveler!"

    request = mock_generate.call_args[0][0]
    assert isinstance(request, LLMRequest)
    assert "Arin" in request.system
    assert "hunter" in request.system


@patch("src.generate.generators.llm_primitives.generate")
def test_image_description_contains_style_prefix(mock_generate):
    mock_generate.return_value = "A cheerful hunter standing in a lush forest"
    result = generate_image_description(SAMPLE_PERSONALITY)
    assert result.startswith("masterpiece")
    assert "pixel art" in result
    assert "cheerful hunter" in result


@patch("src.generate.generators.llm_primitives.generate")
def test_image_description_extracts_from_local_format(mock_generate):
    mock_generate.return_value = (
        "preamble\n##Output: A stoic ranger in iron armor\nmore stuff"
    )
    result = generate_image_description(SAMPLE_PERSONALITY)
    assert "stoic ranger" in result
    assert result.startswith("masterpiece")
