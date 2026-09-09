"""
tests/unit/test_cpp_uia_backend.py
=====================================
Unit tests for jarvis.mcp.servers.ui_windows.backends.cpp_uia_backend.CppUIABackend.

NOTE: Reading the source, CppUIABackend is currently a pure Phase-1 stub --
every UIBackend method unconditionally raises NotImplementedError, and
is_available() always returns False. There is no native bridge dependency
to delegate to yet, so these tests verify the actual stub contract instead
of delegation behavior.
"""
import pytest

from jarvis.mcp.servers.ui_windows.backends.cpp_uia_backend import CppUIABackend

pytestmark = pytest.mark.unit


@pytest.fixture
def backend():
    return CppUIABackend()


def test_is_available_returns_false():
    assert CppUIABackend.is_available() is False


def test_list_windows_raises_not_implemented(backend):
    with pytest.raises(NotImplementedError, match="Phase 1"):
        backend.list_windows()


def test_launch_app_raises_not_implemented(backend):
    with pytest.raises(NotImplementedError, match="Phase 1"):
        backend.launch_app("notepad.exe")


def test_get_dom_raises_not_implemented(backend):
    with pytest.raises(NotImplementedError, match="Phase 1"):
        backend.get_dom(app_title="Notepad")


def test_click_raises_not_implemented(backend):
    with pytest.raises(NotImplementedError, match="Phase 1"):
        backend.click("some_id")


def test_type_text_raises_not_implemented(backend):
    with pytest.raises(NotImplementedError, match="Phase 1"):
        backend.type_text("some_id", "hello")


def test_set_value_raises_not_implemented(backend):
    with pytest.raises(NotImplementedError, match="Phase 1"):
        backend.set_value("some_id", "value")


def test_invoke_raises_not_implemented(backend):
    with pytest.raises(NotImplementedError, match="Phase 1"):
        backend.invoke("some_id")


def test_read_value_raises_not_implemented(backend):
    with pytest.raises(NotImplementedError, match="Phase 1"):
        backend.read_value("some_id")
