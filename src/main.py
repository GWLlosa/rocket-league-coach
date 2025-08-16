"""Main FastAPI application for Rocket League Coach."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

from .config import get_settings
from .logging_config import get_logger


# Initialize logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    
    # Startup
    logger.info(
        "Starting Rocket League Coach",
        environment=settings.environment,
        debug=settings.debug,
        version="1.0.0"
    )
    
    # Ensure directories exist
    settings.replays_dir.mkdir(parents=True, exist_ok=True)
    settings.analysis_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.player_data_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Rocket League Coach")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Rocket League Coach",
        description="Automated Rocket League coaching system with win/loss correlation analysis",
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # Configure CORS
    if settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Add middleware for request logging
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests."""
        logger.info(
            "HTTP request",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
        )
        
        response = await call_next(request)
        
        logger.info(
            "HTTP response",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
        )
        
        return response
    
    # Exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler."""
        logger.error(
            "Unhandled exception",
            error=str(exc),
            error_type=type(exc).__name__,
            url=str(request.url),
            method=request.method,
        )
        
        if settings.debug:
            # In debug mode, return detailed error information
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(exc),
                    "type": type(exc).__name__,
                }
            )
        else:
            # In production, return generic error message
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "rocket-league-coach",
            "version": "1.0.0",
            "environment": settings.environment,
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information."""
        return {
            "service": "Rocket League Coach",
            "description": "Automated coaching system with win/loss correlation analysis",
            "version": "1.0.0",
            "docs": "/docs" if settings.debug else "Documentation not available in production",
            "health": "/health",
        }
    
    # Mount static files (when web interface is implemented)
    static_dir = Path(__file__).parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    
    # Run the application
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
