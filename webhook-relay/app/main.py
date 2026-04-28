from fastapi import FastAPI

from app.routes import inbound, sources

app = FastAPI(
    title="Webhook Relay",
    description="Capture, inspect, and replay webhooks",
    version="0.1.0",
)

app.include_router(sources.router, prefix="/sources", tags=["sources"])
app.include_router(inbound.router, tags=["inbound"])


@app.get("/health")
async def health():
    return {"status": "ok"}
