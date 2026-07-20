"""Registers scheduled jobs on the bot's `JobQueue`.

Called once from `main.py` after the `Application` is built. Kept as
its own module (rather than inlined in `bot_app.py`) so adding a
second job later (e.g. a weekly summary) is a one-line addition here,
not a change to how the Application itself is constructed.
"""

from __future__ import annotations

from telegram.ext import Application

from app.scheduler.reminder_job import check_reminders

_REMINDER_CHECK_INTERVAL_SECONDS = 60


def register_jobs(application: Application) -> None:
    """Register recurring jobs. Requires the app to be built with the
    `job-queue` extra (see requirements.txt) - `application.job_queue`
    is `None` otherwise, which would silently disable reminders.
    """
    if application.job_queue is None:  # pragma: no cover - defensive, config error
        raise RuntimeError(
            "JobQueue is not available - install python-telegram-bot[job-queue] "
            "(see requirements.txt) to enable the reminder system."
        )

    application.job_queue.run_repeating(
        check_reminders,
        interval=_REMINDER_CHECK_INTERVAL_SECONDS,
        first=0,
        name="reminder_check",
    )
