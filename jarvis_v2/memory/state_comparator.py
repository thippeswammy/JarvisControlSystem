"""
State Comparator
================
Fuzzy comparison of two UIState dicts.
Ignores noise keys (clock, status bar) and minor value drift.

Used by VerificationLoop to decide if an action succeeded.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Keys that change constantly and should be ignored in comparison
_IGNORE_PATTERNS = {
    "clock", "time", "date", "battery", "notification", "wifi signal",
    "volume icon", "network", "system tray", "taskbar",
}


class StateComparator:
    """
    Compares actual vs expected UIState dicts with noise filtering.

    Usage:
        comparator = StateComparator()
        ok = comparator.matches(actual_state, expected_state, threshold=0.8)
    """

    def matches(
        self,
        actual: dict,
        expected: dict,
        threshold: float = 0.80,
    ) -> bool:
        """
        Returns True if actual state is similar enough to expected.

        Args:
            actual: State dict captured after action execution
            expected: Target state dict (from GraphNode.ui_metadata)
            threshold: Fraction of expected keys that must match (default 80%)
        """
        if not expected:
            # No expected state recorded — cannot verify, assume OK
            return True

        filtered_expected = self._filter_noise(expected)
        if not filtered_expected:
            return True

        matched = 0
        total = len(filtered_expected)

        for key, exp_val in filtered_expected.items():
            act_val = actual.get(key)
            if act_val is None:
                continue  # Key missing in actual — soft miss
            if self._values_match(act_val, exp_val):
                matched += 1

        score = matched / total
        result = score >= threshold
        logger.debug(
            f"[StateComparator] Match score: {matched}/{total} = {score:.2f} "
            f"(threshold={threshold}) → {'PASS' if result else 'FAIL'}"
        )
        return result

    def diff(self, actual: dict, expected: dict) -> dict:
        """
        Return a dict of keys where actual differs from expected.
        Useful for the 'ask_user' recovery message.
        """
        diffs = {}
        for key, exp_val in self._filter_noise(expected).items():
            act_val = actual.get(key)
            if not self._values_match(act_val, exp_val):
                diffs[key] = {"expected": exp_val, "actual": act_val}
        return diffs

    # ── Private ──────────────────────────────────────

    @staticmethod
    def _filter_noise(state: dict) -> dict:
        return {
            k: v for k, v in state.items()
            if not any(noise in k.lower() for noise in _IGNORE_PATTERNS)
        }

    @staticmethod
    def _values_match(actual: Any, expected: Any) -> bool:
        """
        Fuzzy value comparison:
        - Booleans: exact match (0 != False/True is handled explicitly)
        - Ints: within ±10 (slider bucket tolerance)
        - Strings: case-insensitive strip match
        """
        if actual is None:
            return False
        # Strict bool check first (bool is a subclass of int — don't mix)
        if isinstance(expected, bool):
            return isinstance(actual, bool) and actual == expected
        if isinstance(expected, int):
            if isinstance(actual, bool):
                return False  # bool vs int — not compatible
            if isinstance(actual, int):
                # Slider tolerance only applies to range values (>= 10)
                # Toggle values (0, 1) must match exactly
                if expected >= 10:
                    return abs(actual - expected) <= 10
                return actual == expected
        if isinstance(expected, str):
            return str(actual).strip().lower() == expected.strip().lower()
        return actual == expected
