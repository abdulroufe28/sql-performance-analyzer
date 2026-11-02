from fastapi import FastAPI

from backend.app.api.auth import router as auth_router


app = FastAPI(
    title="SQL Performance Analyzer",
    description="Database performance monitoring and SQL query analysis platform.",
    version="0.1.0",
)


app.include_router(
    auth_router,
    prefix="/api/v1",
)


@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy"}