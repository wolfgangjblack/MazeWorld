"""Tests for the ScreenController state machine."""

import pytest
from src.controllers.screen_controller import ScreenController, ScreenState


def test_initial_state():
    sc = ScreenController()
    assert sc.state == ScreenState.START
    assert sc.depth == 1


def test_initial_state_custom():
    sc = ScreenController(ScreenState.GAMEPLAY)
    assert sc.state == ScreenState.GAMEPLAY


def test_push():
    sc = ScreenController(ScreenState.GAMEPLAY)
    sc.push(ScreenState.PAUSE)
    assert sc.state == ScreenState.PAUSE
    assert sc.depth == 2


def test_pop_returns_to_previous():
    sc = ScreenController(ScreenState.GAMEPLAY)
    sc.push(ScreenState.PAUSE)
    popped = sc.pop()
    assert popped == ScreenState.PAUSE
    assert sc.state == ScreenState.GAMEPLAY
    assert sc.depth == 1


def test_pop_on_single_screen_returns_none():
    sc = ScreenController(ScreenState.START)
    result = sc.pop()
    assert result is None
    assert sc.state == ScreenState.START
    assert sc.depth == 1


def test_replace():
    sc = ScreenController(ScreenState.START)
    sc.replace(ScreenState.GAMEPLAY)
    assert sc.state == ScreenState.GAMEPLAY
    assert sc.depth == 1


def test_nested_push_pop():
    sc = ScreenController(ScreenState.GAMEPLAY)
    sc.push(ScreenState.PLAYER_MENU)
    sc.push(ScreenState.PAUSE)
    assert sc.depth == 3
    assert sc.state == ScreenState.PAUSE

    sc.pop()
    assert sc.state == ScreenState.PLAYER_MENU

    sc.pop()
    assert sc.state == ScreenState.GAMEPLAY

    # Should not pop past the base
    sc.pop()
    assert sc.state == ScreenState.GAMEPLAY


def test_esc_behavior_pop():
    """Esc always calls pop() — context-sensitive close."""
    sc = ScreenController(ScreenState.GAMEPLAY)
    sc.push(ScreenState.DIALOGUE)
    sc.push(ScreenState.PAUSE)

    # Simulate pressing Esc three times
    sc.pop()  # PAUSE -> DIALOGUE
    assert sc.state == ScreenState.DIALOGUE
    sc.pop()  # DIALOGUE -> GAMEPLAY
    assert sc.state == ScreenState.GAMEPLAY
    sc.pop()  # At base, stays GAMEPLAY
    assert sc.state == ScreenState.GAMEPLAY


def test_replace_then_push():
    sc = ScreenController(ScreenState.START)
    sc.replace(ScreenState.GAMEPLAY)
    sc.push(ScreenState.COMBAT)
    assert sc.depth == 2
    assert sc.state == ScreenState.COMBAT
    sc.pop()
    assert sc.state == ScreenState.GAMEPLAY
