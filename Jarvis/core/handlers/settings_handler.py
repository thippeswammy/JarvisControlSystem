"""
Settings Handler — Open Windows Settings pages
Uses the refactored settings_map from WindowsDefaultApps.
"""
import logging
import os
from difflib import get_close_matches
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Flat settings URI map (consolidated from settingControlApp.py)
#  Key: lowercase keyword(s) → Value: ms-settings: URI
# ─────────────────────────────────────────────
SETTINGS_MAP: dict[str, str] = {
    # System
    "system":             "ms-settings:system",
    "display":            "ms-settings:display",
    "sound":              "ms-settings:sound",
    "notifications":      "ms-settings:notifications",
    "focus assist":       "ms-settings:quiethours",
    "focus":              "ms-settings:quiethours",
    "storage":            "ms-settings:storagesense",
    "power":              "ms-settings:powersleep",
    "power and sleep":    "ms-settings:powersleep",
    "sleep":              "ms-settings:powersleep",
    "battery":            "ms-settings:batterysaver-settings",
    "multitasking":       "ms-settings:multitasking",
    "about":              "ms-settings:about",
    "clipboard":          "ms-settings:clipboard",
    "tablet mode":        "ms-settings:tabletmode",
    "tablet":             "ms-settings:tabletmode",
    "remote desktop":     "ms-settings:remotedesktop",
    # Bluetooth & devices
    "bluetooth":          "ms-settings:bluetooth",
    "printers":           "ms-settings:printers",
    "mouse":              "ms-settings:mousetouchpad",
    "touchpad":           "ms-settings:devices-touchpad",
    "typing":             "ms-settings:typing",
    "autoplay":           "ms-settings:autoplay",
    "usb":                "ms-settings:usb",
    # Network
    "network":            "ms-settings:network",
    "internet":           "ms-settings:network",
    "wifi":               "ms-settings:network-wifi",
    "ethernet":           "ms-settings:network-ethernet",
    "vpn":                "ms-settings:network-vpn",
    "airplane mode":      "ms-settings:network-airplanemode",
    "hotspot":            "ms-settings:network-mobilehotspot",
    "proxy":              "ms-settings:network-proxy",
    # Personalization
    "personalization":    "ms-settings:personalization",
    "background":         "ms-settings:personalization-background",
    "wallpaper":          "ms-settings:personalization-background",
    "colors":             "ms-settings:personalization-colors",
    "lock screen":        "ms-settings:lockscreen",
    "themes":             "ms-settings:themes",
    "fonts":              "ms-settings:fonts",
    "start menu":         "ms-settings:start",
    "taskbar":            "ms-settings:taskbar",
    # Apps
    "apps":               "ms-settings:appsfeatures",
    "default apps":       "ms-settings:defaultapps",
    "startup apps":       "ms-settings:startupapps",
    "startup":            "ms-settings:startupapps",
    "video playback":     "ms-settings:videoplayback",
    # Accounts
    "accounts":           "ms-settings:yourinfo",
    "email":              "ms-settings:emailandaccounts",
    "sign in":            "ms-settings:signinoptions",
    "family":             "ms-settings:otherusers",
    "other users":        "ms-settings:otherusers",
    "backup":             "ms-settings:backup",
    # Time & Language
    "time":               "ms-settings:dateandtime",
    "date":               "ms-settings:dateandtime",
    "date and time":      "ms-settings:dateandtime",
    "region":             "ms-settings:regionlanguage",
    "language":           "ms-settings:regionlanguage",
    "speech":             "ms-settings:speech",
    # Gaming
    "gaming":             "ms-settings:gaming-gamebar",
    "game bar":           "ms-settings:gaming-gamebar",
    "game mode":          "ms-settings:gaming-gamemode",
    "captures":           "ms-settings:gaming-captures",
    "xbox":               "ms-settings:gaming-gamebar",
    # Accessibility
    "accessibility":      "ms-settings:easeofaccess-display",
    "magnifier":          "ms-settings:easeofaccess-magnifier",
    "narrator":           "ms-settings:easeofaccess-narrator",
    "high contrast":      "ms-settings:easeofaccess-highcontrast",
    "color filters":      "ms-settings:easeofaccess-colorfilter",
    "closed captions":    "ms-settings:easeofaccess-closedcaptions",
    # Privacy & Security
    "privacy":            "ms-settings:privacy",
    "camera privacy":     "ms-settings:privacy-webcam",
    "microphone privacy": "ms-settings:privacy-microphone",
    "location":           "ms-settings:privacy-location",
    "activity history":   "ms-settings:privacy-activityhistory",
    # Windows Update
    "windows update":     "ms-settings:windowsupdate",
    "update":             "ms-settings:windowsupdate",
    "windows security":   "ms-settings:windowsdefender",
    "security":           "ms-settings:windowsdefender",
    "recovery":           "ms-settings:recovery",
    "activation":         "ms-settings:activation",
    "troubleshoot":       "ms-settings:troubleshoot",
    "developers":         "ms-settings:developers",
    # Home
    "home":               "ms-settings:home",
    "settings":           "ms-settings:home",
}

_ALL_KEYS = list(SETTINGS_MAP.keys())


def _find_setting_uri(query: str) -> tuple[str, str] | None:
    """
    Find best matching settings URI for a text query.
    Returns (key, uri) or None if no match above threshold.
    """
    q = query.lower().strip()

    # Exact match
    if q in SETTINGS_MAP:
        return (q, SETTINGS_MAP[q])

    # Partial substring match
    for key in _ALL_KEYS:
        if key in q or q in key:
            return (key, SETTINGS_MAP[key])

    # Fuzzy match
    matches = get_close_matches(q, _ALL_KEYS, n=1, cutoff=0.5)
    if matches:
        key = matches[0]
        return (key, SETTINGS_MAP[key])

    return None


@registry.register(
    actions=[ActionType.OPEN_SETTINGS],
    priority=10,
    description="Open a Windows Settings page by name"
)
def handle_open_settings(intent: Intent, context) -> ActionResult:
    # Target may be "settings wifi" / "wifi settings" / just "settings"
    query = intent.target.strip()

    # Remove leading "settings" word if present
    for prefix in ["settings ", "setting "]:
        if query.startswith(prefix):
            query = query[len(prefix):].strip()

    if not query or query in ("", "settings", "setting"):
        # Open main settings home
        os.system("start ms-settings:home")
        return ActionResult.ok("Opening Windows Settings.")

    match = _find_setting_uri(query)
    if match:
        key, uri = match
        os.system(f"start {uri}")
        return ActionResult.ok(f"Opening {key} settings.")

    # Last resort: try pywinauto-based navigation
    logger.warning(f"Settings key not found for query: {query!r}")
    os.system("start ms-settings:home")
    return ActionResult.ok(f"Opening Settings. Could not find specific page for '{query}'.")


@registry.register(
    actions=[ActionType.CLOSE_SETTINGS],
    priority=10,
    description="Close the Windows Settings window"
)
def handle_close_settings(intent: Intent, context) -> ActionResult:
    from Jarvis.ApplicationManager import close_application
    success = close_application(app_name_query="settings", addr="SettingsHandler.close ->")
    return ActionResult.ok("Settings closed.") if success else ActionResult.fail("Could not close Settings.")
