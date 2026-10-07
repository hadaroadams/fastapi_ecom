from fastapi import FastAPI
from app.core.config import settings
from app.routers import products

from app.db.base import Base
from app.db.session import engine
from app.models import product as product_model

Base.metadata.create_all(bind=engine)


app = FastAPI(title=settings.app_name, version=settings.version)
app.include_router(products.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def welcome():
    return {
        "message": "welcome to fastapi",
        "app_name": settings.app_name,
        "version": settings.version,
    }
