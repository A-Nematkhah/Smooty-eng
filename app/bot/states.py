"""ConversationHandler states and callback-data conventions.

Centralizing callback_data prefixes here (rather than hardcoding
strings in every handler/keyboard) means a typo shows up as an
import error, not a silently-dead button in Telegram.
"""

from __future__ import annotations

from enum import IntEnum, auto


class OnboardingState(IntEnum):
    """States for the /start onboarding ConversationHandler."""

    CHOOSING_LEVEL = auto()
    CHOOSING_GOAL = auto()
    CHOOSING_DAILY_GOAL = auto()


# --- Callback data prefixes ---
# Format is always "<namespace>:<action>[:<value>]", e.g. "menu:learn",
# "onboarding:level:B1", "settings:daily_goal:20".
CB_ONBOARDING_LEVEL = "onboarding:level"
CB_ONBOARDING_GOAL = "onboarding:goal"
CB_ONBOARDING_DAILY_GOAL = "onboarding:daily_goal"

CB_MENU = "menu"  # menu:<section>, section in {learn, review, daily_lesson, ielts,
#                   progress, vocabulary, settings, main}

CB_SETTINGS = "settings"  # settings:<field>[:<value>], field in
#                            {level, goal, daily_goal, reminder_time, mode, back}

CB_REVIEW = "review"  # review:<action>[:<card_id>[:<rating>]], action in
#                        {reveal, rate}; rating in {again, hard, good, easy}

CB_LEARN = "learn"  # learn:<action>:<word_id>, action in {reveal, enroll}

CB_VOCAB = "vocab"  # vocab:<action>:<id>, action in
#                      {enroll (id=word_id), fav (id=card_id)}

CB_QUIZ = "quiz"  # quiz:<action>[:<position>[:<option_index>]], action in
#                    {start, answer, next}

CB_IELTS = "ielts"  # ielts:<action>[:<value>], action in
#                      {topics, topic (value=topic name), learn, review, back}


def build_callback(*parts: str) -> str:
    """Join callback-data parts with ':' - keeps prefix typos in one place."""
    return ":".join(parts)


def parse_callback(data: str, maxsplit: int = -1) -> list[str]:
    """Split callback_data back into its ':'-separated parts.

    Most callbacks (menu, review, learn, quiz, vocab) pack only
    colon-free values (ids, enum values) after the prefix, so the
    default unlimited split is safe and unchanged for them.

    A few callbacks carry a *value* that can itself contain ':' -
    a "HH:MM" reminder time in settings, or an IELTS topic like
    "Book 2: Unit 18". Callers for those pass maxsplit=2 so the
    value survives intact as the final part instead of being
    shattered into extra pieces (this was a real bug: it silently
    truncated reminder times to "HH" and IELTS topics to "Book N",
    breaking both features whenever the value contained ':').
    """
    return data.split(":", maxsplit)
