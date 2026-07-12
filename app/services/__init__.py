from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import session_scope
from app.models import DecisionAnalysis


def count_saved_analyses() -> int:
    """Return the number of saved decision analyses without breaking health checks.

    Before the initial database migration runs, the table may not exist yet. In
    that case the status endpoint must remain available and report zero.
    """
    try:
        with session_scope() as session:
            count = session.scalar(
                select(func.count()).select_from(DecisionAnalysis)
            )
            return int(count or 0)
    except SQLAlchemyError:
        return 0
