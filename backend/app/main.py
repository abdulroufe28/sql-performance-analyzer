from fastapi import FastAPI

app = FastAPI(
    title="SQL Performance Analyzer",
    description="Database performance monitoring and SQL query analysis platform.",
    version="0.1.0",
)


@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy"}