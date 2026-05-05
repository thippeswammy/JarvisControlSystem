import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis.skills.builtins.session_skill import system_status
from jarvis.skills.skill_bus import SkillResult

# Test with Telegram interface
params_tg = {"_interface": "telegram"}
res_tg = system_status(params_tg)
print(f"Telegram test: {'Interface: Telegram' in res_tg.message}")
print(f"Status line: {res_tg.message.splitlines()[-1]}")

# Test with CLI interface
params_cli = {"_interface": "text"}
res_cli = system_status(params_cli)
print(f"CLI test: {'Interface: Text' in res_cli.message}")
