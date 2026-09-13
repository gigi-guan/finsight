"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import accounts, analytics, health, transactions
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(analytics.router)


@app.get("/")
def root() -> dict[str, str]:
    """Simple root response so visiting the API base URL is informative."""
    return {"message": f"Welcome to {settings.app_name} API"}
