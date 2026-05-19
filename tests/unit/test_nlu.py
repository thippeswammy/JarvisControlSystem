import pytest
from jarvis.perception.nlu import NLU
from jarvis.perception.perception_packet import Utterance

def test_open_close_intents():
    nlu = NLU()
    
    # Open app
    packet = nlu.parse(Utterance("open notepad"))
    assert packet.intent == "open_app"
    assert packet.entities.get("target") == "notepad"
    
    # Close app
    packet = nlu.parse(Utterance("close notepad"))
    assert packet.intent == "close_app"
    assert packet.entities.get("target") == "notepad"

def test_log_analysis_intent():
    nlu = NLU()
    
    packet = nlu.parse(Utterance("analyze the logs"))
    assert packet.intent == "log_analysis"
    
    packet = nlu.parse(Utterance("check logs"))
    assert packet.intent == "log_analysis"

def test_compound_splitting_protects_quotes():
    nlu = NLU()
    
    # Normal compound command
    packet = nlu.parse(Utterance("open notepad and then close settings"))
    assert packet.compound is True
    assert len(packet.sub_commands) == 2
    assert packet.sub_commands[0]["intent"] == "open_app"
    assert packet.sub_commands[1]["intent"] == "close_app"
    
    # Quoted compound command
    packet = nlu.parse(Utterance("summarize this: \"open notepad and then close settings\""))
    assert packet.compound is False # or at least length 1 if it falls back
    # In NLU, if length of parts is 1, compound is not True
    assert packet.intent == "llm_route" # because 'summarize this' doesn't match a direct intent
    assert packet.entities.get("raw") == "summarize this: \"open notepad and then close settings\""

def test_sub_location_extraction():
    nlu = NLU()
    packet = nlu.parse(Utterance("open settings display"))
    assert packet.intent == "open_app"
    assert packet.entities.get("target") == "settings"
    assert packet.sub_location == "display"
