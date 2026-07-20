"""ORM models package.

Importing this package registers every model on `Base.metadata`,
which `database.engine.init_db()` relies on before calling
`create_all`.
"""

from app.models.card import Card
from app.models.progress import Progress
from app.models.review import Review
from app.models.user import User
from app.models.word import Word

__all__ = ["User", "Word", "Card", "Review", "Progress"]
