import pytest
import re
import json
from jarvis.perception.nlu import NLU
from jarvis.perception.perception_packet import Utterance

class MockBackend:
    def _call_llm_closed_loop(self, prompt, context=""):
        m = re.search(r"Utterance: (.*)$", prompt)
        text = m.group(1).strip() if m else prompt
        
        if text == "open notepad":
            return '{"intent": "open_app", "entities": {"target": "notepad"}, "intent_category": "EXECUTION"}'
        elif text == "close notepad":
            return '{"intent": "close_app", "entities": {"target": "notepad"}, "intent_category": "EXECUTION"}'
        elif text in ("analyze the logs", "check logs"):
            return '{"intent": "log_analysis", "entities": {}, "intent_category": "EXECUTION"}'
        elif text == "open notepad and then close settings":
            return '{"intent": "open_app", "entities": {"target": "notepad"}, "intent_category": "EXECUTION", "compound": true, "sub_commands": [{"intent": "open_app", "entities": {"target": "notepad"}}, {"intent": "close_app", "entities": {"target": "settings"}}]}'
        elif text == 'summarize this: "open notepad and then close settings"':
            return '{"intent": "llm_route", "entities": {"raw": "summarize this: \\"open notepad and then close settings\\""}, "intent_category": "EXECUTION", "compound": false}'
        elif text == "open settings display":
            return '{"intent": "open_app", "entities": {"target": "settings", "sub_location": "display"}, "intent_category": "EXECUTION"}'
        return '{}'

class MockRouter:
    def __init__(self):
        self._primary = MockBackend()
        self._fallback = None
        self._emergency = None

    def _clean_and_parse_json(self, raw):
        return json.loads(raw)

@pytest.fixture
def nlu_with_mock():
    return NLU(router=MockRouter())

def test_open_close_intents(nlu_with_mock):
    # Open app
    packet = nlu_with_mock.parse(Utterance("open notepad"))
    assert packet.intent == "open_app"
    assert packet.entities.get("target") == "notepad"
    
    # Close app
    packet = nlu_with_mock.parse(Utterance("close notepad"))
    assert packet.intent == "close_app"
    assert packet.entities.get("target") == "notepad"

def test_log_analysis_intent(nlu_with_mock):
    packet = nlu_with_mock.parse(Utterance("analyze the logs"))
    assert packet.intent == "log_analysis"
    
    packet = nlu_with_mock.parse(Utterance("check logs"))
    assert packet.intent == "log_analysis"

def test_compound_splitting_protects_quotes(nlu_with_mock):
    # Normal compound command
    packet = nlu_with_mock.parse(Utterance("open notepad and then close settings"))
    assert packet.compound is True
    assert len(packet.sub_commands) == 2
    assert packet.sub_commands[0]["intent"] == "open_app"
    assert packet.sub_commands[1]["intent"] == "close_app"
    
    # Quoted compound command
    packet = nlu_with_mock.parse(Utterance("summarize this: \"open notepad and then close settings\""))
    assert packet.compound is False
    assert packet.intent == "llm_route"
    assert packet.entities.get("raw") == "summarize this: \"open notepad and then close settings\""

def test_sub_location_extraction(nlu_with_mock):
    packet = nlu_with_mock.parse(Utterance("open settings display"))
    assert packet.intent == "open_app"
    assert packet.entities.get("target") == "settings"
    assert packet.sub_location == "display"
