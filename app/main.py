from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.core.config import settings
from fastapi import FastAPI, Request
from fastapi.responses import Response
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# from app.db.base import Base
# from app.db.session import engine
from app.models import product as product_model
from app.routers import payments, products
from app.routers import auth
from app.routers import cart
from app.routers import order
from app.core.rate_limit import limiter


# Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)


async def rate_limit_handler(
    request: Request,
    exc: Exception,
) -> Response:
    if not isinstance(exc, RateLimitExceeded):
        raise exc

    return _rate_limit_exceeded_handler(request, exc)


app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    rate_limit_handler,
)


# NEW: security headers on every response
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(order.router)
app.include_router(payments.router)


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
