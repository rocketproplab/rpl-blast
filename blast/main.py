"""FastAPI main entry point for BLAST application"""
import uvicorn
import logging
from app import create_app
from app.config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main application entry point"""
    # Load settings
    settings = Settings()
    
    # Create FastAPI app
    app = create_app(settings)
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        reload=False,  # Set to True for development
        log_level="info"
    )

if __name__ == "__main__":
    main()