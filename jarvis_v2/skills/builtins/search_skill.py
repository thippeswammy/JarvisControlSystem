"""Search Skill — web search and Windows search."""
import logging
import time
from jarvis_v2.skills.skill_decorator import skill
from jarvis_v2.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["search web", "search for", "google", "look up", "browse"],
       name="search_web", category="search")
def search_web(params: dict) -> SkillResult:
    query = params.get("query", "").strip()
    engine = params.get("engine", "google").lower()
    if not query:
        return SkillResult(success=False, message="No search query")

    urls = {
        "google": f"https://www.google.com/search?q={query.replace(' ', '+')}",
        "bing":   f"https://www.bing.com/search?q={query.replace(' ', '+')}",
        "duck":   f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
    }
    url = urls.get(engine, urls["google"])
    try:
        import webbrowser
        webbrowser.open(url)
        return SkillResult(success=True, action_taken=f"Searched: {query!r}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))


@skill(triggers=["windows search", "search files", "find file", "search start"],
       name="search_windows", category="search")
def search_windows(params: dict) -> SkillResult:
    query = params.get("query", "").strip()
    try:
        import pyautogui
        pyautogui.hotkey("win", "s")
        time.sleep(0.5)
        if query:
            pyautogui.typewrite(query, interval=0.05)
        return SkillResult(success=True, action_taken=f"Searched Windows: {query!r}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))
