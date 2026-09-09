"""
tests/unit/test_brave_agent.py
===============================
Unit tests for jarvis.agents.builtin.brave_agent.BraveAgent.

NOTE: Despite the module docstring mentioning "web browsing", BraveAgent does
NOT call any HTTP/search API directly (no requests/httpx/urllib usage). It is
a browser-automation dispatcher: it builds a jarvis.skills.skill_bus.SkillCall
and hands it to a SkillBus (context["_bus"]). That SkillBus.dispatch(...) call
is the actual external boundary (it shields the agent from exceptions raised
by the underlying browser-automation skill, converting them into a failed
SkillResult) so it is what gets mocked here.
"""
from unittest.mock import MagicMock

import pytest

from jarvis.agents.builtin.brave_agent import BraveAgent
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.skills.skill_bus import SkillCall, SkillResult

pytestmark = pytest.mark.unit


def make_memory():
    return AgentLocalMemory(agent_name="brave_agent")


def test_tab_switch_dispatches_correct_skill_call_and_returns_success():
    """A 'switch tab' task is parsed into a target tab name and dispatched to
    the switch_browser_tab skill; a successful SkillResult is surfaced as-is."""
    agent = BraveAgent()
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = SkillResult(success=True, action_taken="Switched to tab: Gmail")

    result = agent.run("switch tab to gmail", {"_bus": mock_bus}, make_memory(), MagicMock())

    assert result.success is True
    assert result.output == "Switched to tab: Gmail"
    mock_bus.dispatch.assert_called_once()
    call = mock_bus.dispatch.call_args[0][0]
    assert isinstance(call, SkillCall)
    assert call.skill == "switch_browser_tab"
    assert call.params == {"target": "gmail"}


def test_click_element_dispatch_failure_is_surfaced_as_failed_result():
    """A 'click on X' task dispatches click_web_element; a failed SkillResult
    (e.g. because the underlying automation/network call failed) is turned
    into a failed AgentResult with the SkillBus message included."""
    agent = BraveAgent()
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = SkillResult(success=False, message="Element not found in DOM")

    result = agent.run("click on the link", {"_bus": mock_bus}, make_memory(), MagicMock())

    assert result.success is False
    assert result.output == "Failed to click web element: Element not found in DOM"
    call = mock_bus.dispatch.call_args[0][0]
    assert call.skill == "click_web_element"
    assert call.params == {"selector": "the link"}


def test_click_selector_parsing_truncates_when_target_word_contains_on():
    """Documents a real parsing gap: the selector is extracted via
    task_lower.split("on")[1], which only works when "on" appears exactly
    once. If the target text itself contains the substring "on" (e.g. the
    word "button"), split() produces more than 2 parts and everything from
    the second "on" onward is silently dropped from the selector."""
    agent = BraveAgent()
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = SkillResult(success=True, action_taken="clicked")

    agent.run("click on the submit button", {"_bus": mock_bus}, make_memory(), MagicMock())

    call = mock_bus.dispatch.call_args[0][0]
    # NOTE: a user would expect {"selector": "the submit button"}; the code
    # instead truncates to "the submit butt" because "button" contains "on".
    assert call.params == {"selector": "the submit butt"}


def test_no_recognized_keyword_falls_back_to_opening_default_profile():
    """A task with none of the 'profile'/'tab'/'click' keywords falls through
    to the general default-profile-open branch."""
    agent = BraveAgent()
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = SkillResult(success=True, action_taken="Brave launched with Default profile")

    result = agent.run("open brave", {"_bus": mock_bus}, make_memory(), MagicMock())

    assert result.success is True
    assert result.output == "Brave launched with Default profile"
    call = mock_bus.dispatch.call_args[0][0]
    assert call.skill == "open_brave_profile"
    assert call.params == {"profile": "Default"}


def test_profile_switch_failure_returns_failure_message():
    """A failed profile-switch SkillResult is surfaced with the SkillBus
    failure message embedded in the agent output."""
    agent = BraveAgent()
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = SkillResult(success=False, message="Profile directory locked")

    result = agent.run("open profile Work", {"_bus": mock_bus}, make_memory(), MagicMock())

    assert result.success is False
    assert result.output == "Failed to switch profile: Profile directory locked"
    call = mock_bus.dispatch.call_args[0][0]
    assert call.skill == "open_brave_profile"


def test_profile_name_extraction_picks_the_literal_word_profile_first():
    """Documents actual (buggy-looking) parsing behavior: the word-matching
    loop tests each word of the task in order for "person"/"profile"/isdigit,
    and since the task must contain the literal word "profile" to reach this
    branch at all, that word itself satisfies the condition and is picked as
    profile_name *before* the loop ever reaches a trailing qualifier like
    "2" or "Person3" that a user actually intended as the profile name."""
    agent = BraveAgent()
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = SkillResult(success=True, action_taken="done")

    agent.run("switch to profile 2", {"_bus": mock_bus}, make_memory(), MagicMock())

    call = mock_bus.dispatch.call_args[0][0]
    # NOTE: a user would expect params == {"profile": "2"}; the code instead
    # matches on the trigger word "profile" itself before reaching "2".
    assert call.params == {"profile": "profile"}
