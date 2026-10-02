import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.database.config import SessionLocal, init_db
from backend.database.models import User
from backend.routers import advisor, analytics, auth as auth_router, chat, forecasting, goals, memory, scenario, subscriptions, transactions

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _ensure_demo_user():
    """Create the placeholder demo user (used until real auth exists) if missing."""
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
        return

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.id == "demo-user").first():
            db.add(User(id="demo-user", email="demo@finmind.local", username="demo"))
            db.commit()
            logger.info("Created demo user")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _ensure_demo_user()
    yield


app = FastAPI(
    title='FinMind AI Backend',
    description='AI-powered personal finance platform',
    version='1.0.0',
    lifespan=lifespan,
)


@app.middleware('http')
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'no-referrer')
    response.headers.setdefault(
        'Permissions-Policy',
        'camera=(), microphone=(), geolocation=()',
    )

    if (
        os.getenv('ENVIRONMENT', 'development').strip().lower()
        in {'production', 'prod', 'staging'}
        and request.url.scheme == 'https'
    ):
        response.headers.setdefault(
            'Strict-Transport-Security',
            'max-age=31536000; includeSubDomains',
        )

    return response

# CORS middleware
frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, 'http://localhost:3000', 'http://localhost:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include routers
app.include_router(transactions.router, prefix='/transactions', tags=['transactions'])
app.include_router(chat.router, prefix='/chat', tags=['chat'])
app.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
app.include_router(analytics.router, prefix='/analytics', tags=['analytics']) 
app.include_router(
    memory.router,
    prefix="/memory",
    tags=["memory"],
)
app.include_router(
    subscriptions.router,
    prefix="/subscriptions",
    tags=["subscriptions"],
)
app.include_router(
    forecasting.router,
    prefix="/forecasting",
    tags=["forecasting"],
)
app.include_router(goals.router, prefix="/goals", tags=["goals"])
app.include_router(scenario.router, prefix="/scenario", tags=["scenario"])
app.include_router(auth_router.router, prefix='/auth', tags=['auth'])
@app.get('/')
def read_root():
    return {
        'message': 'FinMind AI backend is running.',
        'version': '1.0.0',
        'environment': os.getenv('ENVIRONMENT', 'development')
    }


@app.get('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return {
        'status': 'healthy',
        'gemini_configured': bool(os.getenv('GEMINI_API_KEY')),
        'database_configured': bool(os.getenv('DATABASE_URL')),
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)