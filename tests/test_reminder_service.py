"""Tests for `ReminderService`, backing the previously-unbuilt
Reminder System (app/scheduler/).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.enums import CEFRLevel, LearningGoal, WordSource
from app.repositories.card_repository import CardRepository
from app.repositories.user_repository import UserRepository
from app.repositories.word_repository import WordRepository
from app.services.reminder_service import ReminderService


def _make_user(db_session, telegram_id: int, reminder_time: str | None):
    return UserRepository(db_session).create(
        telegram_id=telegram_id,
        username=None,
        level=CEFRLevel.B1,
        learning_goal=LearningGoal.GENERAL,
        daily_goal=10,
        reminder_time=reminder_time,
    )


def test_users_due_now_matches_exact_reminder_time(db_session):
    due_user = _make_user(db_session, telegram_id=1, reminder_time="09:00")
    other_user = _make_user(db_session, telegram_id=2, reminder_time="20:00")
    _make_user(db_session, telegram_id=3, reminder_time=None)

    due = ReminderService(db_session).users_due_now("09:00")

    assert [u.id for u in due] == [due_user.id]
    assert other_user.id not in [u.id for u in due]


def test_build_reminder_text_mentions_due_count_when_words_are_due(db_session):
    user = _make_user(db_session, telegram_id=1, reminder_time="09:00")
    words = WordRepository(db_session)
    cards = CardRepository(db_session)
    now = datetime.now(timezone.utc)

    word = words.create(word="abandon", meaning="x", source=WordSource.OXFORD_3000)
    cards.create(user_id=user.id, word_id=word.id, due_date=now)

    text = ReminderService(db_session).build_reminder_text(user, now=now)

    assert "1 word" in text


def test_build_reminder_text_falls_back_when_nothing_due(db_session):
    user = _make_user(db_session, telegram_id=1, reminder_time="09:00")

    text = ReminderService(db_session).build_reminder_text(user)

    assert "lesson is ready" in text
