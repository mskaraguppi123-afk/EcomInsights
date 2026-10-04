import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.web import web_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401 - registers models with SQLAlchemy metadata

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_starter_tables() -> None:
    """Create initial tables and seed sample data on fresh deployment."""
    try:
        Base.metadata.create_all(bind=engine)
        from app.db.session import SessionLocal
        from app.models.product import Product
        from app.db.seed import seed_sample_data

        with SessionLocal() as db:
            if db.query(Product).count() == 0:
                seed_sample_data(db)
                logger.info("Auto-seeded initial sample products for fresh deployment.")
    except Exception as exc:
        logger.warning("Could not auto-create database tables on startup: %s", exc)


app.include_router(web_router)
app.include_router(router, prefix=settings.api_v1_prefix)
