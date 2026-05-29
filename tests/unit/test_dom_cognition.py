import pytest
from unittest.mock import MagicMock, patch
from jarvis.skills.builtins.browser_skill import (
    _MANAGER,
    extract_browser_dom_tree,
    click_browser_node,
    fill_browser_node
)

@pytest.fixture
def mock_browser_env():
    # Setup mock playwright page and elements
    page = MagicMock()
    context = MagicMock()
    context.pages = [page]
    
    # Create mock interactive elements
    elem1 = MagicMock()
    elem1.is_visible.return_value = True
    elem1.evaluate.return_value = "button"
    elem1.inner_text.return_value = "Submit Button"
    elem1.get_attribute.side_effect = lambda attr: {
        "placeholder": None,
        "role": "button",
        "id": "btn-submit",
        "name": None
    }.get(attr)
    
    elem2 = MagicMock()
    elem2.is_visible.return_value = True
    elem2.evaluate.return_value = "input"
    elem2.inner_text.return_value = ""
    elem2.get_attribute.side_effect = lambda attr: {
        "placeholder": "Enter your name",
        "role": None,
        "id": "name-input",
        "name": "username"
    }.get(attr)
    
    elem3 = MagicMock()
    elem3.is_visible.return_value = False  # Invisible element, should be skipped
    
    # Prevent MagicMock hasattr gotcha for click_input/type_keys pywinauto fallback checks
    del elem1.click_input
    del elem2.type_keys
    
    page.query_selector_all.return_value = [elem1, elem2, elem3]
    
    with patch.object(_MANAGER, "connect_or_launch", return_value=context):
        yield page, [elem1, elem2]


def test_extract_browser_dom_tree(mock_browser_env):
    page, active_elems = mock_browser_env
    
    res = extract_browser_dom_tree({})
    assert res.success is True
    assert "BUTTON[BUTTON]: 'Submit Button'" in res.data["dom_tree"]
    assert "INPUT: 'Enter your name'" in res.data["dom_tree"]
    assert len(_MANAGER.cached_nodes) == 2
    assert _MANAGER.cached_nodes[0] == active_elems[0]
    assert _MANAGER.cached_nodes[1] == active_elems[1]

def test_click_browser_node(mock_browser_env):
    page, active_elems = mock_browser_env
    
    # Perform extraction to populate cache
    extract_browser_dom_tree({})
    
    # Click first node
    res = click_browser_node({"index": 1})
    assert res.success is True
    active_elems[0].click.assert_called_once()
    
    # Out of bounds click
    res2 = click_browser_node({"index": 99})
    assert res2.success is False
    assert "out of cached bounds" in res2.message

def test_fill_browser_node(mock_browser_env):
    page, active_elems = mock_browser_env
    
    # Perform extraction to populate cache
    extract_browser_dom_tree({})
    
    # Fill second node
    res = fill_browser_node({"index": 2, "text": "Antigravity"})
    assert res.success is True
    active_elems[1].fill.assert_called_with("Antigravity")
    
    # Out of bounds fill
    res2 = fill_browser_node({"index": -5, "text": "Antigravity"})
    assert res2.success is False
    assert "out of cached bounds" in res2.message
