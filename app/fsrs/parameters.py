"""FSRS-4.5/5-style algorithm weights and tunables.

These are the published default weights from the open-source FSRS
project (used by modern Anki). They are reasonable for any learner
out of the box - per-user optimization from review history is a
possible future phase, not needed for a personal tool.
"""

from __future__ import annotations

# Default parameter vector (19 weights, FSRS-5), as published by the
# FSRS project. w[0..3] seed initial stability by first rating; w[4..]
# tune the difficulty/stability update formulas.
DEFAULT_WEIGHTS: tuple[float, ...] = (
    0.4072,
    1.1829,
    3.1262,
    15.4722,
    7.2102,
    0.5316,
    1.0651,
    0.0234,
    1.616,
    0.1544,
    1.0824,
    1.9813,
    0.0953,
    0.2975,
    2.2042,
    0.2407,
    2.9466,
    0.5034,
    0.6567,
)

# Target probability of recall to solve for the next interval - 90%
# is the standard FSRS default (vs. SM-2's fixed multipliers).
DEFAULT_REQUEST_RETENTION: float = 0.9

# Absolute ceiling on scheduled interval, in days, so a card can
# never drift years into the future on a small personal deck.
DEFAULT_MAXIMUM_INTERVAL: int = 365 * 2

# Stability/difficulty are clamped to these bounds to keep the
# formulas numerically stable at the extremes.
MIN_DIFFICULTY: float = 1.0
MAX_DIFFICULTY: float = 10.0
MIN_STABILITY: float = 0.01

# Minutes-scale intervals used for the LEARNING/RELEARNING steps
# (before a card graduates to full day-scale REVIEW scheduling).
# Kept short since this is a personal vocab tool, not a rote-drill deck.
LEARNING_STEPS_MINUTES: tuple[int, ...] = (1, 10)
RELEARNING_STEPS_MINUTES: tuple[int, ...] = (10,)
