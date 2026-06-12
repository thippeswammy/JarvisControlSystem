"""
Knowledge Gap Engine
====================
Detects missing required parameters and insufficient knowledge in a GoalModel
before the planning phase begins. If gaps are found, it triggers the
UserInteractionManager for clarifications.

In the cognitive loop pipeline:
    NLU → GoalUnderstanding → GroundingLayer → **KnowledgeGapEngine** → CapabilityPlanner

This engine prevents the system from generating incomplete or hallucinated plans
by identifying what it doesn't know and asking the user proactively.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from jarvis.perception.perception_packet import GoalModel

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeGap:
    """Represents a single missing piece of information."""
    parameter: str          # The missing parameter name (e.g. "target_directory", "date_range")
    description: str        # Human-readable description of what's missing
    severity: str = "required"  # "required" = blocks execution, "optional" = can infer/skip
    suggested_question: str = ""  # Pre-built clarification question for the user
    default_value: str = ""       # Fallback default if user doesn't respond


@dataclass
class GapCheckResult:
    """Result of a knowledge gap analysis."""
    has_gaps: bool = False
    gaps: List[KnowledgeGap] = field(default_factory=list)
    goal: Optional[GoalModel] = None  # Updated goal model (if gaps were auto-resolved)
    clarification_needed: bool = False  # True if user interaction is required


# ── Intent-Specific Required Parameters ──────────────────

# Maps abstract intents to their required parameters
_INTENT_REQUIREMENTS = {
    "app_interaction": {
        "required": ["target_app"],
        "questions": {
            "target_app": "Which application should I open?",
        },
    },
    "web_search": {
        "required": ["search_query"],
        "questions": {
            "search_query": "What would you like me to search for?",
        },
    },
    "file_management": {
        "required": ["file_path"],
        "questions": {
            "file_path": "Which file or directory are you referring to?",
        },
    },
    "content_generation": {
        "required": ["content_topic"],
        "questions": {
            "content_topic": "What should the content be about?",
        },
    },
    "system_control": {
        "required": ["control_target"],
        "questions": {
            "control_target": "Which system setting should I modify?",
        },
    },
    "communication": {
        "required": ["recipient", "message_content"],
        "questions": {
            "recipient": "Who should I send this to?",
            "message_content": "What message should I send?",
        },
    },
}


class KnowledgeGapEngine:
    """
    Scans a GoalModel for missing required parameters and knowledge prerequisites.

    Usage::

        engine = KnowledgeGapEngine()
        result = engine.check(goal_model)
        if result.clarification_needed:
            # Route to UserInteractionManager
            for gap in result.gaps:
                answer = uim.prompt_clarification(gap.suggested_question)
                goal_model = engine.fill_gap(goal_model, gap.parameter, answer)
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Parameters
        ----------
        confidence_threshold : float
            Minimum confidence required from GoalUnderstandingLayer.
            Below this threshold, the entire goal is treated as ambiguous.
        """
        self._confidence_threshold = confidence_threshold

    def check(self, goal: GoalModel) -> GapCheckResult:
        """
        Analyze a GoalModel for missing information.

        Parameters
        ----------
        goal : GoalModel
            The grounded goal model to analyze.

        Returns
        -------
        GapCheckResult
            Analysis result with any detected gaps and clarification needs.
        """
        gaps: List[KnowledgeGap] = []

        # 1. Check overall confidence
        if goal.confidence < self._confidence_threshold:
            gaps.append(KnowledgeGap(
                parameter="goal_clarity",
                description="The goal interpretation has low confidence",
                severity="required",
                suggested_question=f"I'm not sure I understood correctly. Did you mean: '{goal.primary_goal}'?",
            ))

        # 2. Check for empty primary goal
        if not goal.primary_goal or not goal.primary_goal.strip():
            gaps.append(KnowledgeGap(
                parameter="primary_goal",
                description="No goal was extracted from the utterance",
                severity="required",
                suggested_question="What would you like me to do?",
            ))
            goal.knowledge_gaps = [g.parameter for g in gaps]
            goal.is_complete = False
            return GapCheckResult(has_gaps=True, gaps=gaps, goal=goal, clarification_needed=True)

        # 3. Check intent-specific requirements
        for intent in goal.intents:
            intent_gaps = self._check_intent_requirements(intent, goal)
            gaps.extend(intent_gaps)

        # 4. Check for target app when intents require one
        app_intents = {"app_interaction", "text_edit"}
        if app_intents.intersection(set(goal.intents)) and not goal.target_app:
            # Check if target is embedded in the goal text
            if not self._can_infer_app_from_text(goal.primary_goal):
                gaps.append(KnowledgeGap(
                    parameter="target_app",
                    description="No target application specified for app interaction",
                    severity="required",
                    suggested_question="Which application should I use?",
                ))

        # 5. Check required knowledge prerequisites
        for knowledge_req in goal.required_knowledge:
            gaps.append(KnowledgeGap(
                parameter=f"knowledge_{knowledge_req}",
                description=f"Required knowledge not available: {knowledge_req}",
                severity="optional",  # Can attempt to acquire dynamically
                suggested_question=f"I may need additional information about: {knowledge_req}. Can you provide details?",
            ))

        # Build result
        required_gaps = [g for g in gaps if g.severity == "required"]
        has_gaps = len(gaps) > 0
        clarification_needed = len(required_gaps) > 0

        if has_gaps:
            goal.knowledge_gaps = [g.parameter for g in gaps]
            goal.is_complete = not clarification_needed

        return GapCheckResult(
            has_gaps=has_gaps,
            gaps=gaps,
            goal=goal,
            clarification_needed=clarification_needed,
        )

    def fill_gap(self, goal: GoalModel, parameter: str, value: str) -> GoalModel:
        """
        Fill a specific knowledge gap with a user-provided value.

        Parameters
        ----------
        goal : GoalModel
            The goal model with gaps.
        parameter : str
            The parameter name to fill.
        value : str
            The user-provided value.

        Returns
        -------
        GoalModel
            Updated goal model with the gap filled.
        """
        if parameter == "target_app":
            goal.target_app = value
        elif parameter == "goal_clarity":
            # User confirmed or corrected the goal
            goal.confidence = 1.0
        elif parameter == "primary_goal":
            goal.primary_goal = value

        # Remove from gaps list
        goal.knowledge_gaps = [g for g in goal.knowledge_gaps if g != parameter]
        goal.is_complete = len([g for g in goal.knowledge_gaps]) == 0

        logger.info(f"[KnowledgeGapEngine] Filled gap '{parameter}' = '{value}'")
        return goal

    def _check_intent_requirements(self, intent: str, goal: GoalModel) -> List[KnowledgeGap]:
        """Check if an intent's required parameters are satisfied."""
        gaps = []
        requirements = _INTENT_REQUIREMENTS.get(intent, {})
        required_params = requirements.get("required", [])
        questions = requirements.get("questions", {})

        for param in required_params:
            # Skip target_app check here — handled separately with text inference
            if param == "target_app":
                continue
            if not self._is_parameter_available(param, goal):
                gaps.append(KnowledgeGap(
                    parameter=param,
                    description=f"Missing required parameter '{param}' for intent '{intent}'",
                    severity="required",
                    suggested_question=questions.get(param, f"What is the {param.replace('_', ' ')}?"),
                ))

        return gaps

    @staticmethod
    def _is_parameter_available(param: str, goal: GoalModel) -> bool:
        """Check if a required parameter can be found in the goal model."""
        if param == "target_app":
            return bool(goal.target_app)
        if param == "search_query":
            # Search query is typically embedded in the primary goal
            return bool(goal.primary_goal)
        if param == "content_topic":
            return bool(goal.primary_goal)
        if param == "control_target":
            return bool(goal.primary_goal)
        if param == "file_path":
            # Check if a file path is mentioned in the goal
            return any(c in goal.primary_goal for c in ["/", "\\", ".txt", ".py", ".doc"])
        # Default: assume available if we have a goal
        return bool(goal.primary_goal)

    @staticmethod
    def _is_valid_user_app(name: str) -> bool:
        """Filters out background services, drivers, host processes, and system utilities."""
        import re
        n = name.lower().strip()
        if len(n) <= 2:
            return n in {"cmd", "git", "wsl", "go"}

        # Expanded blacklist for high-quality sanitization
        blacklist = [
            "host", "service", "helper", "handler", "agent", "daemon", "driver", "system",
            "telemetry", "runtime", "broker", "background", "server", "utility", "diag", "diagnostic",
            "manager", "updater", "overlay", "plugin", "extension", "cache", "monitor",
            "client", "proxy", "listener", "controller", "sync", "hook", "analytics",
            "crash", "reporter", "engine", "auth", "login", "credential", "dispatcher", "bridge",
            "worker", "amd", "nvidia", "asus", "intel", "realtek", "ati", "task",
            "redistributable", "sdk", "compiler", "package", "library", "framework",
            "setup", "install", "uninstall", "help", "manual", "readme", "license",
            "register", "activate", "config", "utility", "support", "feedback",
            "troubleshoot", "wizard", "migrator", "check", "viewer", "reinstall",
            "add-in", "addin", "shortcut", "documentation", "tutorial", "guide",
            "release notes", "whatsnew", "what's new", "development kit", "hotfix", "patch"
        ]

        # Explicit exceptions that are user-facing but contain blacklisted words
        exceptions = {"settings", "cmd", "explorer", "powershell", "git bash"}
        if n in exceptions:
            return True

        # Check ends with srv/svc
        if n.endswith(("srv", "svc")):
            return False

        # Block pure numbers or special chars
        if re.match(r'^[\d\W_]+$', n):
            return False

        # Block typical background/development tools that users don't say
        system_blacklist = {
            "csrss", "dwm", "ctfmon", "lsaiso", "msmpeng", "spoolsv", "winlogon", "wmiprvse", "wlanext",
            "smss", "svchost", "lsass", "wininit", "conhost", "taskhostw", "smartscreen", "dllhost",
            "searchindexer", "unsecapp", "wudfhost", "devenvexe", "officeclicktorun", "perfwatson2",
            "vcpkgsrv", "vcxprojreader", "appactions", "castsrv", "cmwebadmin", "cncmd", "codemeter",
            "crossdeviceresume", "dax3api", "hasplms", "hasplmv", "ipoverusbsvc", "keyboxd", "lockapp",
            "memcompression", "msedgewebview2", "ngciso", "nissrv", "rtkuwp", "widgets", "wstoastnotification",
            "registry", "uihost", "crossdeviceservice", "crossdevicetask", "applicationframehost",
            "aggregatorhost", "amdfendrsr", "amdrsserv", "amdrssrcext", "asusappservice", "asusoptimization",
            "asusoptimizationstartuptask", "asusosd", "asusproarthost", "asusproartservice", "asusproartupdateservice",
            "asussoftwaremanager", "asussoftwaremanageragent", "asusswitch", "asussystemanalysis", "asussystemdiagnosis",
            "asuswifismartconnect", "backgroundtaskhost", "bravecrashhandler", "bravecrashhandler64", "browserhost",
            "cpumetricsserver", "dashost", "dataexchangehost", "focalfpsrvcdeamon", "fontdrvhost", "glidexnearservice",
            "glidexremoteservice", "glidexservice", "glidexserviceext", "language_server_windows_x64",
            "microsoft.servicehub.controller", "mpdefendercoreservice", "mscopilot_proxy", "nvcontainer",
            "nvdisplay.container", "nvsphelper64", "onedrive.sync.service", "onenotem.exe", "phoneexperiencehost",
            "rtkauduservice64", "runtimebroker", "saclient", "safeexambrowser.service", "saservice", "sdxhelper",
            "searchhost", "securityhealthservice", "servicehost", "servicehub.datawarehousehost",
            "servicehub.host.clr.x64", "servicehub.host.clr.x86", "servicehub.identityhost",
            "servicehub.roslyncodeanalysisservice", "servicehub.settingshost", "servicehub.threadedwaitdialog",
            "servicehub.vsdetouredhost", "shellexperiencehost", "shellhost", "sihost", "startmenuexperiencehost",
            "systemsettings", "textinputhost", "tvnserver", "useroobebroker", "wslservice", "wsnativepushservice",
            "winword", "powerpnt"
        }
        if n in system_blacklist:
            return False

        return not any(sub in n for sub in blacklist)

    @classmethod
    def _clean_app_name(cls, display_name: str) -> str:
        """Removes version numbers, parentheses, and trailing punctuation from application names."""
        import re
        name = display_name
        
        # Remove parentheses and their common contents
        name = re.sub(
            r'\((x64|x86|64-bit|32-bit|64\s*bit|32\s*bit|User|System|Community|Professional|Enterprise|Home|Preview|Update|SDK|Runtime|Compiler)\)',
            '',
            name,
            flags=re.IGNORECASE
        )
        
        # Remove standard version-like numbers
        name = re.sub(r'\b\d+(\.\d+)+\b', '', name)
        # Remove single digit or prefixed version ending
        name = re.sub(r'\b[vV]\d+(\.\d+)*\b', '', name)
        
        # Clean up multiple spaces and strip punctuation
        name = re.sub(r'\s+', ' ', name).strip()
        name = name.rstrip('-,. ')
        
        return name.lower().strip()

    @classmethod
    def _get_known_apps(cls) -> set:
        """Loads known apps, scans OS Start Menu shortcuts and Registry for human-friendly names, filters processes, and saves it."""
        import json
        import os
        import psutil

        config_dir = "jarvis/config"
        config_path = os.path.join(config_dir, "known_apps.json")

        # Standard fallback list of known user applications
        default_apps = {
            "notepad", "chrome", "google chrome", "edge", "microsoft edge", 
            "firefox", "word", "microsoft word", "excel", "microsoft excel", 
            "powerpoint", "microsoft powerpoint", "vscode", "visual studio code", 
            "visual studio", "terminal", "powershell", "cmd", "explorer", 
            "file explorer", "settings", "slack", "spotify", "discord", "teams", 
            "outlook", "calculator", "paint", "brave", "brave browser", "opera", 
            "winword", "powerpnt", "notepad++", "git bash", "ollama", "wsl", "zoom"
        }

        # Load previously persisted list from file
        loaded_apps = set()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded_apps = set(json.load(f))
            except Exception as e:
                logger.warning(f"[KnowledgeGapEngine] Failed to load known_apps.json: {e}")

        # Filter loaded apps to purge any dirty ones that might have slipped into the file previously
        loaded_apps = {app for app in loaded_apps if cls._is_valid_user_app(app)}

        known = default_apps.union(loaded_apps)

        # Dynamic Windows OS query of active processes (with filtering)
        new_running = set()
        try:
            for proc in psutil.process_iter(["name"]):
                name = proc.info["name"]
                if name:
                    name_clean = name.replace(".exe", "").lower().strip()
                    if cls._is_valid_user_app(name_clean):
                        new_running.add(name_clean)
        except Exception as e:
            logger.debug(f"[KnowledgeGapEngine] Dynamic process scan failed: {e}")

        # Dynamic Windows API window title processes (with filtering)
        try:
            import win32gui
            import win32process
            def enum_windows_callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd) or ""
                    if title:
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            proc_name = proc.name().replace(".exe", "").lower().strip()
                            if cls._is_valid_user_app(proc_name):
                                extra.add(proc_name)
                        except Exception:
                            pass
                return True
            win32gui.EnumWindows(enum_windows_callback, new_running)
        except Exception as e:
            logger.debug(f"[KnowledgeGapEngine] Dynamic EnumWindows scan failed: {e}")

        # Dynamic Start Menu & Desktop Shortcut Scanning (Real Human Names)
        shortcut_names = set()
        paths_to_scan = []
        
        # Public Programs
        prog_data = os.environ.get("ProgramData", "C:\\ProgramData")
        paths_to_scan.append(os.path.join(prog_data, "Microsoft\\Windows\\Start Menu\\Programs"))
        
        # User Programs
        app_data = os.environ.get("AppData")
        if app_data:
            paths_to_scan.append(os.path.join(app_data, "Microsoft\\Windows\\Start Menu\\Programs"))
            
        # Desktops
        public_desktop = "C:\\Users\\Public\\Desktop"
        paths_to_scan.append(public_desktop)
        
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            paths_to_scan.append(os.path.join(user_profile, "Desktop"))

        for path in paths_to_scan:
            if os.path.exists(path):
                try:
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if file.endswith((".lnk", ".url")):
                                base_name = os.path.splitext(file)[0].lower().strip()
                                base_name = cls._clean_app_name(base_name)
                                if base_name and cls._is_valid_user_app(base_name):
                                    shortcut_names.add(base_name)
                except Exception as e:
                    logger.debug(f"[KnowledgeGapEngine] Shortcut folder walk failed for {path}: {e}")

        # Dynamic Windows Registry Queries (for full installed applications inventory)
        registry_names = set()
        try:
            import winreg
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            ]
            for hive, path in registry_paths:
                try:
                    with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                        num_subkeys, _, _ = winreg.QueryInfoKey(key)
                        for i in range(num_subkeys):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                        if display_name:
                                            cleaned = cls._clean_app_name(display_name)
                                            if cleaned and cls._is_valid_user_app(cleaned):
                                                registry_names.add(cleaned)
                                    except OSError:
                                        pass
                            except OSError:
                                pass
                except OSError:
                    pass
        except Exception as e:
            logger.debug(f"[KnowledgeGapEngine] Dynamic Registry scan failed: {e}")

        # Add shorthands dynamically for discovered apps
        shorthands = set()
        for app in new_running.union(shortcut_names).union(registry_names):
            if "google chrome" in app:
                shorthands.add("chrome")
            if "visual studio code" in app:
                shorthands.add("vscode")
                shorthands.add("visual studio")
            if "microsoft edge" in app:
                shorthands.add("edge")
            if "microsoft word" in app:
                shorthands.add("word")
            if "microsoft excel" in app:
                shorthands.add("excel")
            if "microsoft powerpoint" in app:
                shorthands.add("powerpoint")
            if "file explorer" in app:
                shorthands.add("explorer")

        # Combine sets
        final_set = known.union(new_running).union(shortcut_names).union(registry_names).union(shorthands)

        # Filter the final combined set to be absolutely safe
        final_set = {app for app in final_set if cls._is_valid_user_app(app)}

        # Persist the clean list back to file
        if final_set != loaded_apps:
            try:
                os.makedirs(config_dir, exist_ok=True)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(sorted(list(final_set)), f, indent=2)
            except Exception as e:
                logger.warning(f"[KnowledgeGapEngine] Failed to save known_apps.json: {e}")

        return final_set

    @classmethod
    def _can_infer_app_from_text(cls, text: str) -> bool:
        """Check if the target app can be inferred from the goal text."""
        text_lower = text.lower()
        known_apps = cls._get_known_apps()
        return any(app in text_lower for app in known_apps)
