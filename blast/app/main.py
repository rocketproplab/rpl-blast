"""BLAST Application Entry Point"""
import uvicorn
from app import create_app
from app.config.settings import Settings


# Create application instance
settings = Settings()
app = create_app(settings)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )