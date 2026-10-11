from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# SQLite connection with thread check disabled for FastAPI dependency injection
engine = create_engine(
    settings.RESOLVED_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import all models to register with Base before creating tables
    import app.models.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Lightweight SQLite column migration for processing_jobs
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(processing_jobs)"))
            existing_cols = {row[1] for row in result.fetchall()}
            cols_to_add = [
                ("telegram_chat_id", "VARCHAR(64)"),
                ("telegram_user_id", "VARCHAR(64)"),
                ("telegram_message_id", "INTEGER"),
                ("workflow_mode", "VARCHAR(32) DEFAULT 'interactive'"),
                ("source_url", "VARCHAR(1024)"),
                ("collected_settings", "JSON"),
                ("output_derivative_id", "VARCHAR(36)"),
                ("published_platforms", "JSON"),
            ]
            for col_name, col_type in cols_to_add:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE processing_jobs ADD COLUMN {col_name} {col_type}"))
            conn.commit()
        except Exception:
            # Table might not exist yet or non-sqlite engine; create_all handles it
            pass
