import warnings
import asyncio
from contextlib import asynccontextmanager

# Suppress harmless multiprocessing warnings
warnings.filterwarnings("ignore", category=UserWarning, module="multiprocessing.resource_tracker")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongo import connect_to_mongo, close_mongo_connection, get_database
from app.routes.rag_routes import router as rag_router
from app.routes.system_routes import router as system_router
from app.routes.auth_routes import router as auth_router
from app.routes.evaluation_routes import router as evaluation_router
from app.routes.audit_routes import router as audit_router
from app.services.faiss_rag_service import FaissRagService
from app.services.embedding_service import get_embedding_model
from app.services.rag_service import RagService
from app.utils.config import settings
from app.utils.logger import get_logger
from app.utils.metrics import observe_http_request, set_storage_backend, start_timer

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → yield → shutdown."""
    logger.info("Starting RAG application")
    app.state.rag_service = None
    app.state.storage_backend = "uninitialized"
    mongo_ok = False

    # Connect to MongoDB
    try:
        await connect_to_mongo()
        logger.info("MongoDB connection established")
        mongo_ok = True
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        if settings.allow_start_without_mongo:
            logger.warning(
                "Starting in FAISS fallback mode because ALLOW_START_WITHOUT_MONGO=true. "
                "Fix MongoDB credentials in .env to switch back to Atlas."
            )
            faiss_service = FaissRagService()
            faiss_service.startup()
            app.state.rag_service = faiss_service
            app.state.storage_backend = "faiss-fallback"
            set_storage_backend("faiss-fallback")
            logger.info("FAISS fallback service initialized successfully")
        else:
            raise

    if mongo_ok:
        # Initialize RAG service
        try:
            db = get_database()
            rag_service = RagService(db)
            app.state.rag_service = rag_service
            app.state.storage_backend = "mongodb"
            set_storage_backend("mongodb")
            logger.info("RAG service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise

        # Get stats
        try:
            stats = await rag_service.get_vector_store_stats()
            logger.info(f"Vector store ready: {stats}")
        except Exception as e:
            logger.warning(f"Could not retrieve stats: {e}")

        # Warm the embedding model only when MongoDB is healthy —
        # no point loading heavy weights if we're in a broken state.
        try:
            await asyncio.to_thread(get_embedding_model)
            logger.info("Embedding model preloaded successfully")
        except Exception as e:
            logger.warning(f"Could not preload embedding model: {e}")

    yield  # ── Application runs ──────────────────────────────────────────

    logger.info("Shutting down RAG application")
    await close_mongo_connection()
    logger.info("MongoDB connection closed")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="""
    # 🤖 RAG Application API

    Production-grade Retrieval-Augmented Generation (RAG) system with:
    - **LangGraph** multi-agent workflow orchestration
    - **MongoDB** vector search with hybrid retrieval
    - **Query Expansion** for better coverage
    - **Cross-Encoder Reranking** for 20-30% accuracy boost
    - **Citation Generation** with inline source attribution

    ## 🔐 Authentication
    Use `/auth/login` to obtain a Bearer token, then include it in requests:
    ```
    Authorization: Bearer <your_token>
    ```

    ## 📤 Upload Flow
    1. Upload files: `POST /upload`
    2. Query documents: `POST /query`
    3. View documents: `GET /documents`
    """,
    contact={
        "name": "RAG Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "authentication", "description": "Login, logout, token management"},
        {"name": "rag", "description": "Upload files and query documents"},
        {"name": "system", "description": "Health checks and system status"},
        {"name": "evaluation", "description": "RAG quality metrics (RAGAS)"},
    ],
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Wildcard origin ("*") is invalid when allow_credentials=True (CORS spec).
# Load allowed origins from env; fall back to local dev ports only.
_raw_origins = settings.cors_allowed_origins
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(rag_router)
app.include_router(auth_router)
app.include_router(evaluation_router)
app.include_router(audit_router)


@app.middleware("http")
async def prometheus_http_middleware(request: Request, call_next):
    started = start_timer()
    method = request.method
    route = request.scope.get("route")
    endpoint = getattr(route, "path", request.url.path)

    try:
        response = await call_next(request)
        observe_http_request(method, endpoint, response.status_code, started)
        return response
    except Exception:
        observe_http_request(method, endpoint, 500, started)
        raise
