"""
Moviroo AI Chatbot - Main Application
FastAPI application with all routes and middleware
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import time

from config import settings
from database.connection import init_db, close_db
from models.embedding import embedding_service
from core.container import vector_store# Import routers
from api import chat, tickets, feedback, health
from models.vector_store import FAISSVectorStore
vector_store = FAISSVectorStore()
# Configure logging
from loguru import logger as loguru_logger
import sys

# Remove default handler
loguru_logger.remove()

# Add custom handler
loguru_logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

loguru_logger.add(
    settings.log_file,
    rotation=settings.log_rotation,
    retention=settings.log_retention,
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Bridge loguru to standard logging
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        loguru_logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# Configure standard logging
logging.basicConfig(handlers=[InterceptHandler()], level=0)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown
    """
    # Startup
    logger.info("=" * 80)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("=" * 80)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_db()
        
        # Load embedding model
        logger.info("Loading embedding model...")
        embedding_service.load_model()
        
        # ── Charge ou entraîne l'index FAISS ──
        logger.info("Chargement de l'index vectoriel...")
        loaded = vector_store.load()

        if not loaded:
            logger.info(
                "Aucun index trouvé → pipeline d'entraînement "
                "(dataset.csv + tickets BD)..."
            )
            from pipelines.training_pipeline import training_pipeline
            from database.connection import AsyncSessionLocal
            async with AsyncSessionLocal() as db_train:
                report = await training_pipeline.run(db=db_train, force_rebuild=True)
                if report.success:
                    logger.info(
                        f"Index construit : {report.vectors_indexed} vecteurs "
                        f"({report.final_from_csv} CSV, "
                        f"{report.final_from_tickets} tickets)"
                    )
                else:
                    logger.error(f"Entraînement échoué : {report.error}")
        else:
            logger.info(
                f"Index chargé depuis disque : "
                f"{vector_store.index.ntotal} vecteurs existants"
            )
        
        logger.info("=" * 80)
        logger.info("Moviroo AI Chatbot is ready!")
        logger.info(f"API available at: http://{settings.api_host}:{settings.api_port}")
        logger.info(f"Docs available at: http://{settings.api_host}:{settings.api_port}/docs")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    try:
        # Save vector store
        logger.info("Saving vector store...")
        vector_store.save()
        
        # Close database
        logger.info("Closing database connections...")
        await close_db()
        
        logger.info("Shutdown complete")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    🚀 **Moviroo AI Chatbot Backend**
    
    Production-ready multilingual AI chatbot for transport support.
    
    ## Features
    
    * 🌍 **Multilingual**: English, French, Arabic, Franco-Arabic
    * 🧠 **Semantic Search**: Understanding, not just keyword matching
    * 📚 **Incremental Learning**: Learns from resolved tickets
    * 💬 **Feedback System**: Continuous improvement
    * 🎯 **High Accuracy**: Confidence scores for every response
    
    ## Supported Categories
    
    * Payment issues
    * Ride delays
    * Booking problems
    * Account management
    * Password reset
    * App bugs
    
    ## Quick Start
    
    1. **Chat**: POST /chat with your message
    2. **Create Ticket**: POST /ticket if chatbot can't help
    3. **Provide Feedback**: POST /feedback to improve responses
    
    ## Admin Endpoints
    
    * Load initial dataset: POST /admin/load-dataset
    * Rebuild index: POST /admin/rebuild-index
    * View statistics: GET /stats
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"→ {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        f"← {request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Duration: {duration:.3f}s"
    )
    
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )


# Include routers
app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(feedback.router)
app.include_router(health.router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.api_workers,
        log_level=settings.log_level.lower()
    )
