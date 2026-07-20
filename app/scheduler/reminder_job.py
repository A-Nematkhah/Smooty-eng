"""The recurring job that checks, once a minute, which users are due
for a reminder right now and sends it.

Registered via `Application.job_queue` (see `scheduler_setup.py`).
python-telegram-bot's `JobQueue` runs on APScheduler under the hood
(`AsyncIOScheduler`), which is what the master spec's "use
APScheduler" requirement asks for - going through `job_queue` instead
of instantiating a second, separate `AsyncIOScheduler` avoids two
schedulers fighting over the same asyncio event loop that
`Application.run_polling()` already owns.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram.error import TelegramError
from telegram.ext import ContextTypes

from app.core.config import get_settings
from app.database.engine import session_scope
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


async def check_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs every minute: find users whose reminder_time is now, message them.

    Each user's send is wrapped individually - one user blocking the
    bot (e.g. they deleted the chat) must not stop the rest of the
    batch from being notified.
    """
    settings = get_settings()
    now = datetime.now(ZoneInfo(settings.scheduler_timezone))
    current_hhmm = now.strftime("%H:%M")

    with session_scope() as session:
        service = ReminderService(session)
        due_users = service.users_due_now(current_hhmm)
        # Snapshot (telegram_id, text) pairs before the session closes,
        # since User rows would otherwise expire once we leave `with`.
        messages = [
            (user.telegram_id, service.build_reminder_text(user, now=now)) for user in due_users
        ]

    for telegram_id, text in messages:
        try:
            await context.bot.send_message(chat_id=telegram_id, text=text, parse_mode="Markdown")
        except TelegramError:
            logger.warning("Could not send reminder to telegram_id=%s", telegram_id, exc_info=True)
