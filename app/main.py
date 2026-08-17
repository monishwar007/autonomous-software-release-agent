from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes.webhook import router as webhook_router
from app.utils.logger import logger
import os

app = FastAPI(
    title="Autonomous Release Agent",
    description="AI-Powered DevOps Release Decision Engine",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include webhook routes
app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Autonomous Release Agent"}


# Serve React frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        file_path = os.path.join(frontend_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Autonomous Release Agent...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
