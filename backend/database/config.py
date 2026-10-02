# """
# Database configuration and session management
# """
# import os
# import logging
# from sqlalchemy import create_engine, event
# from sqlalchemy.orm import sessionmaker, Session
# from sqlalchemy.pool import NullPool

# logger = logging.getLogger(__name__)

# # Get database URL from environment
# DATABASE_URL = os.getenv(
#     'DATABASE_URL',
#     'postgresql://user:password@localhost:5432/finmind_db'
# )

# # Create engine
# engine = create_engine(
#     DATABASE_URL,
#     # Use NullPool for serverless/railway deployments
#     poolclass=NullPool if 'railway' in DATABASE_URL or 'supabase' in DATABASE_URL else None,
#     echo=os.getenv('LOG_LEVEL') == 'DEBUG',
#     connect_args={
#         'connect_timeout': 10,
#         'keepalives': 1,
#         'keepalives_idle': 30,
#     } if 'postgresql' in DATABASE_URL else {}
# )

# # Create session factory
# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine
# )


# def get_db() -> Session:
#     """Get database session dependency"""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# async def get_db_async() -> Session:
#     """Async wrapper for database session"""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# def init_db():
#     """Initialize database tables"""
#     try:
#         from backend.database.models import Base
#         Base.metadata.create_all(bind=engine)
#         logger.info("Database tables created successfully")
#     except Exception as e:
#         logger.error(f"Failed to initialize database: {str(e)}")
#         raise


# # Connection pool event listeners for PostgreSQL
# if 'postgresql' in DATABASE_URL:
#     @event.listens_for(engine, "connect")
#     def set_sqlite_pragma(dbapi_conn, connection_record):
#         """Set connection parameters for PostgreSQL"""
#         try:
#             # Set timeouts
#             dbapi_conn.set_isolation_level(0)  # Autocommit mode
#         except Exception as e:
#             logger.warning(f"Could not set connection pragma: {str(e)}")


"""
Database configuration and session management
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

# Defaults to a local SQLite file so `pip install -r backend/requirements.txt` + `uvicorn`
# works with zero external setup. Set DATABASE_URL to a real Postgres URL for production.
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./finmind.db')

if DATABASE_URL.startswith('sqlite'):
    connect_args = {'check_same_thread': False}
elif DATABASE_URL.startswith('postgresql'):
    connect_args = {
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
    }
else:
    connect_args = {}

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool if ('railway' in DATABASE_URL or 'supabase' in DATABASE_URL) else None,
    echo=os.getenv('LOG_LEVEL') == 'DEBUG',
    hide_parameters=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    environment = os.getenv(
        'ENVIRONMENT',
        'development',
    ).strip().lower()

    if environment not in {
        'development',
        'dev',
        'test',
        'testing',
    }:
        logger.info(
            "Skipping automatic schema creation in %s; "
            "apply Alembic migrations explicitly",
            environment,
        )
        return

    try:
        from backend.database.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(
            "Failed to initialize database (error_type=%s)",
            type(e).__name__,
        )
        raise