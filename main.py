# """
# Moviroo AI Chatbot - Main FastAPI Application
# """
# import logging
# import time
# from contextlib import asynccontextmanager
# from datetime import datetime

# from fastapi import FastAPI, Request, status
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from fastapi.exceptions import RequestValidationError

# from config import settings
# from database.connection import init_db, close_db
# from models.embedding import embedding_service
# from models.vector_store import vector_store
# from core.rag_pipeline import rag_pipeline

# logger = logging.getLogger(__name__)

# # ── Logging setup ────────────────────────────────────────────────────────────
# import sys
# from loguru import logger as log

# log.remove()
# log.add(sys.stdout, level=settings.log_level,
#         format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")
# log.add(settings.log_file, rotation=settings.log_rotation,
#         retention=settings.log_retention, level=settings.log_level)


# class _InterceptHandler(logging.Handler):
#     def emit(self, record):
#         try:
#             level = log.level(record.levelname).name
#         except ValueError:
#             level = record.levelno
#         frame, depth = logging.currentframe(), 2
#         while frame.f_code.co_filename == logging.__file__:
#             frame = frame.f_back
#             depth += 1
#         log.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# logging.basicConfig(handlers=[_InterceptHandler()], level=0)


# # ── Lifespan ─────────────────────────────────────────────────────────────────

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     log.info("=" * 60)
#     log.info(f"Starting {settings.app_name} v{settings.app_version}")

#     # 1. Database
#     await init_db()
#     log.info("Database ready")

#     # 2. Embedding model
#     embedding_service.load_model()
#     log.info("Embedding model loaded")

#     # 3. FAISS index
#     loaded = vector_store.load()
#     if not loaded:
#         log.info("No FAISS index found — building from dataset...")
#         from pipelines.training_pipeline import training_pipeline
#         from database.connection import AsyncSessionLocal
#         async with AsyncSessionLocal() as db:
#             report = await training_pipeline.run(db=db, force_rebuild=True)
#             if report.success:
#                 log.info(f"Index built: {report.vectors_indexed} vectors "
#                          f"(csv={report.final_from_csv}, tickets={report.final_from_tickets})")
#             else:
#                 log.error(f"Training failed: {report.error}")
#     else:
#         log.info(f"FAISS index loaded: {vector_store.index.ntotal} vectors")

#     # 4. Wire RAG pipeline
#     rag_pipeline.set_vector_store(vector_store)
#     log.info("RAG pipeline ready")

#     log.info(f"API running at http://{settings.api_host}:{settings.api_port}")
#     log.info(f"Docs: http://{settings.api_host}:{settings.api_port}/docs")
#     log.info("=" * 60)

#     yield

#     # Shutdown
#     vector_store.save()
#     await close_db()
#     log.info("Shutdown complete")


# # ── App ───────────────────────────────────────────────────────────────────────

# app = FastAPI(
#     title=settings.app_name,
#     version=settings.app_version,
#     description="""
# ## Moviroo AI Chatbot

# Multilingual RAG chatbot for transport support.

# **Languages**: English · Français · العربية · Franco-Arabic

# **Architecture**: SentenceTransformer → FAISS → Mistral/Llama

# ### Endpoints
# - `POST /chat` — Ask anything
# - `POST /tickets` — Create support ticket
# - `PATCH /tickets/{id}/resolve` — Resolve + auto-index
# - `POST /feedback` — Rate a response
# - `GET /stats` — System stats
# - `GET /health` — Health check
# - `POST /admin/rebuild-index` — Force rebuild FAISS
# """,
#     lifespan=lifespan,
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.cors_origins_list,
#     allow_credentials=settings.cors_allow_credentials,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     t0 = time.time()
#     response = await call_next(request)
#     ms = round((time.time() - t0) * 1000)
#     log.info(f"{request.method} {request.url.path} → {response.status_code} ({ms}ms)")
#     return response


# @app.exception_handler(RequestValidationError)
# async def validation_error(request: Request, exc: RequestValidationError):
#     return JSONResponse(
#         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#         content={"error": "Validation Error", "detail": exc.errors()},
#     )


# @app.exception_handler(Exception)
# async def general_error(request: Request, exc: Exception):
#     log.error(f"Unhandled error: {exc}", exc_info=True)
#     return JSONResponse(
#         status_code=500,
#         content={"error": "Internal Server Error",
#                  "detail": str(exc) if settings.debug else "Unexpected error"},
#     )


# # ── Routers ───────────────────────────────────────────────────────────────────

# from api import chat, tickets, feedback, health  # noqa: E402

# app.include_router(chat.router)
# app.include_router(tickets.router)
# app.include_router(feedback.router)
# app.include_router(health.router)


# @app.get("/", tags=["Root"])
# async def root():
#     return {
#         "name": settings.app_name,
#         "version": settings.app_version,
#         "status": "running",
#         "docs": "/docs",
#         "health": "/health",
#         "timestamp": datetime.now().isoformat(),
#     }


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "main:app",
#         host=settings.api_host,
#         port=settings.api_port,
#         reload=settings.debug,
#         workers=1,
#         log_level=settings.log_level.lower(),
#     )
"""
Moviroo AI Chatbot - Main FastAPI Application
"""
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from config import settings
from database.connection import init_db, close_db
from models.embedding import embedding_service
from models.vector_store import vector_store
from core.rag_pipeline import rag_pipeline

logger = logging.getLogger(__name__)

# ── Logging setup ────────────────────────────────────────────────────────────
import sys
from loguru import logger as log

log.remove()
log.add(sys.stdout, level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")
log.add(settings.log_file, rotation=settings.log_rotation,
        retention=settings.log_retention, level=settings.log_level)


class _InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = log.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        log.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[_InterceptHandler()], level=0)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 60)
    log.info(f"Starting {settings.app_name} v{settings.app_version}")

    # 1. Database
    await init_db()
    log.info("Database ready")

    # 2. Embedding model
    embedding_service.load_model()
    log.info("Embedding model loaded")

    # 3. FAISS index
    loaded = vector_store.load()
    if not loaded:
        log.info("No FAISS index found — building from dataset...")
        from pipelines.training_pipeline import training_pipeline
        from database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            report = await training_pipeline.run(db=db, force_rebuild=True)
            if report.success:
                log.info(f"Index built: {report.vectors_indexed} vectors "
                         f"(csv={report.final_from_csv}, tickets={report.final_from_tickets})")
            else:
                log.error(f"Training failed: {report.error}")
    else:
        log.info(f"FAISS index loaded: {vector_store.index.ntotal} vectors")

    # 4. Wire RAG pipeline
    rag_pipeline.set_vector_store(vector_store)
    log.info("RAG pipeline ready")

    log.info(f"API running at http://{settings.api_host}:{settings.api_port}")
    log.info(f"Docs: http://{settings.api_host}:{settings.api_port}/docs")
    log.info("=" * 60)

    yield

    # Shutdown
    vector_store.save()
    await close_db()
    log.info("Shutdown complete")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## Moviroo AI Chatbot

Multilingual RAG chatbot for transport support.

**Languages**: English · Français · العربية · Franco-Arabic

**Architecture**: SentenceTransformer → FAISS → Mistral/Llama

### Endpoints
- `POST /chat` — Ask anything
- `POST /tickets` — Create support ticket
- `PATCH /tickets/{id}/resolve` — Resolve + auto-index
- `POST /feedback` — Rate a response
- `GET /stats` — System stats
- `GET /health` — Health check
- `POST /admin/rebuild-index` — Force rebuild FAISS
""",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    ms = round((time.time() - t0) * 1000)
    log.info(f"{request.method} {request.url.path} → {response.status_code} ({ms}ms)")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation Error", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_error(request: Request, exc: Exception):
    log.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error",
                 "detail": str(exc) if settings.debug else "Unexpected error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

from api import chat, tickets, feedback, health  # noqa: E402

app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(feedback.router)
app.include_router(health.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=1,
        log_level=settings.log_level.lower(),
    )
