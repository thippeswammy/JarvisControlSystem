import os
import sys

# Add project root to sys.path so we can import jarvis
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.graph_db import GraphNode, GraphEdge

def seed_triggers():
    mem = MemoryManager()
    db = mem.get_db()
    
    # Let's create a "system" app if it doesn't exist
    mem.save_node(GraphNode(id="sys.volume", app_id="system", type="ACTION", label="Volume Control"))
    mem.save_node(GraphNode(id="sys.power", app_id="system", type="ACTION", label="Power Control"))
    mem.save_node(GraphNode(id="sys.brightness", app_id="system", type="ACTION", label="Brightness Control"))

    # Add edges with rich natural language triggers
    
    # 1. Volume Up
    mem.save_edge(GraphEdge(
        id="edge.volume_up",
        from_id="sys.volume",
        to_id="sys.volume",
        action_type="command",
        action_params={"action": "set_volume", "direction": "up"},
        confidence=0.9,
        triggers=[
            "increase volume", 
            "volume up", 
            "make it louder",
            "crank up the tunes",
            "it's too quiet",
            "pump up the volume"
        ]
    ))
    
    # 2. Volume Down
    mem.save_edge(GraphEdge(
        id="edge.volume_down",
        from_id="sys.volume",
        to_id="sys.volume",
        action_type="command",
        action_params={"action": "set_volume", "direction": "down"},
        confidence=0.9,
        triggers=[
            "decrease volume", 
            "volume down", 
            "make it quieter",
            "shh",
            "it's too loud",
            "lower the sound"
        ]
    ))
    
    # 3. Shutdown
    mem.save_edge(GraphEdge(
        id="edge.shutdown",
        from_id="sys.power",
        to_id="sys.power",
        action_type="command",
        action_params={"action": "power_action", "command": "shutdown"},
        confidence=0.9,
        triggers=[
            "shut down", 
            "turn off the computer", 
            "power off",
            "go to sleep jarvis",
            "i'm done for the day",
            "kill the system"
        ]
    ))

    # 4. Brightness Up
    mem.save_edge(GraphEdge(
        id="edge.brightness_up",
        from_id="sys.brightness",
        to_id="sys.brightness",
        action_type="command",
        action_params={"action": "set_brightness", "direction": "up"},
        confidence=0.9,
        triggers=[
            "increase brightness", 
            "make the screen brighter", 
            "i can't see the screen",
            "turn up the brightness"
        ]
    ))

    # 5. Brightness Down
    mem.save_edge(GraphEdge(
        id="edge.brightness_down",
        from_id="sys.brightness",
        to_id="sys.brightness",
        action_type="command",
        action_params={"action": "set_brightness", "direction": "down"},
        confidence=0.9,
        triggers=[
            "decrease brightness", 
            "dim the screen", 
            "it's too bright",
            "my eyes hurt",
            "lower brightness"
        ]
    ))

    print("Successfully added new edges with rich semantic triggers to jarvis.db!")
    mem.close()

if __name__ == "__main__":
    seed_triggers()
