# English Learning Telegram Bot (personal project)

A personal, AI-free English vocabulary learning bot for Telegram,
combining FSRS spaced repetition, an Oxford 3000 word bank, an IELTS
vocabulary mode, a multiple-choice quiz engine, a daily lesson
composer, a progress dashboard, and a reminder system.

## Status: feature-complete

All planned phases are done:

- **Phase 1** - architecture (folder structure, DB schema, decisions)
- **Phase 2** - database layer: SQLAlchemy models, repositories, vocabulary
  loader + seed script
- **Phase 3** - Telegram bot core: `/start` onboarding, main menu, ⚙ Settings
- **Phase 4** - FSRS engine + 🔄 Review Words
- **Phase 5** - 📚 Learn English, ⭐ My Vocabulary, `/addword`, `/search`/`/find`
- **Phase 6** - 🎯 Daily Lesson (new words + reviews + quiz) and the
  multiple-choice quiz engine
- **Phase 7** - 🎓 IELTS Mode (topic browsing, dedicated learn/review queues)
- **Phase 8** (this pass) - filled two remaining gaps, added the reminder
  system, and finished testing/documentation:
  - **📊 Progress** was still a placeholder even though every number it
    needed already existed (`Progress` rollup, review accuracy) - added
    `ProgressService` and wired it in.
  - The favorite-toggle backend (`Card.is_favorite`,
    `LearningService.toggle_favorite`) existed with no button anywhere
    to trigger it - added a "⭐ Toggle favorite" button to the review
    screen.
  - **Reminder System** (`app/scheduler/`) - daily/review reminders via
    python-telegram-bot's `JobQueue` (backed by APScheduler under the
    hood), firing at each user's `reminder_time` from ⚙ Settings.

Every button in the UI now does something real - there are no remaining
"🚧 coming soon" placeholders.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set TELEGRAM_BOT_TOKEN (from @BotFather)

python -m scripts.seed_vocabulary   # creates tables + imports vocab
python main.py                       # starts polling + the reminder job
```

Then message your bot on Telegram and send `/start`.

## Running tests

```bash
pytest
```

Covers: FSRS scheduling math, all repositories, onboarding/settings,
learning/review/daily-lesson/IELTS/progress/reminder services, and the
quiz generator - all against an in-memory SQLite DB, no live Telegram
connection needed.

**Known limitation:** these tests were written and reviewed without
ever installing `python-telegram-bot`/SQLAlchemy/pytest in the sandbox
that produced this codebase (no network access there) - every file was
syntax-checked and cross-referenced (no dangling imports, every
callback-data prefix has a registered handler), but `pytest` itself
hasn't been run end-to-end. Run it yourself before relying on this in
production.

## Project layout

```
app/
  bot/            Telegram handlers, keyboards, message templates
  core/           config, logging, exceptions
  database/       engine/session setup, declarative base
  models/         SQLAlchemy ORM models
  repositories/   one class per table, all raw queries live here
  services/       business logic (onboarding, settings, learning,
                  review, daily lesson, IELTS, progress, reminders)
  fsrs/           framework-agnostic FSRS-5 scheduler
  quizzes/        multiple-choice question generation
  vocabulary/     JSON loading/validation for the word bank
  scheduler/      JobQueue registration + the reminder job
data/             oxford3000.json, ielts.json
scripts/          seed_vocabulary.py
tests/            pytest suite, in-memory SQLite fixture in conftest.py
```

## Notes for future changes

- To add a new quiz type: add a module under `app/quizzes/` following
  `multiple_choice.py`'s shape, then have `DailyLessonService.build_quiz`
  pick it (or add a user-facing toggle for quiz type).
- To add a new word source: it's just a new `WordSource` enum value -
  the `words` table and all repositories are already source-agnostic.
- The reminder job runs once a minute and fires on an exact `HH:MM`
  string match against `User.reminder_time` - simple and sufficient at
  personal-tool scale, but note it depends on the job actually running
  at that exact minute (no catch-up logic if the bot was offline).
