import urllib.parse
from collections.abc import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from config import settings

_odbc_params = urllib.parse.quote_plus(settings.sql_connection_string)
engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={_odbc_params}",
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def next_id(db: Session, pk_column, prefix: str) -> str:
    """Generate the next sequential prefixed string ID (e.g. 's009') for
    tables whose primary key has no autoincrement/identity — the real
    schema uses app-generated string IDs, not integers. Not safe under
    concurrent writers; fine for this POC's demo-scale usage."""
    existing_ids = db.execute(select(pk_column)).scalars().all()
    numbers = [int(pk[len(prefix):]) for pk in existing_ids if pk.startswith(prefix)]
    next_number = max(numbers, default=0) + 1
    return f"{prefix}{next_number:03d}"
