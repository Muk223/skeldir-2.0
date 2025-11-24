"""
Skeldir Attribution Intelligence - FastAPI Application

This is the main FastAPI application entry point for contract-first enforcement testing.
Routes are organized by domain (auth, attribution, etc.) and must align with OpenAPI contracts.

Contract-First Enforcement:
- All routes under /api/* are governed by contract scope configuration
- Each route must have a corresponding OpenAPI operation
- Static and dynamic conformance checks prevent divergence
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.api import auth, attribution

# Import middleware - Phase G: Active Privacy Defense
from app.middleware import PIIStrippingMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="Skeldir Attribution Intelligence API",
    version="1.0.0",
    description="Privacy-first attribution intelligence platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# PII Stripping Middleware - Phase G: Defense-in-Depth Layer 1
# Must be added BEFORE other middleware to ensure PII is stripped first
app.add_middleware(PIIStrippingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(attribution.router, prefix="/api/attribution", tags=["Attribution"])

# Health check endpoint (out-of-scope per contract_scope.yaml)
@app.get("/health")
async def health_check():
    """Health check endpoint - explicitly out-of-scope for contract enforcement."""
    return {"status": "healthy", "service": "skeldir-api"}


@app.get("/")
async def root():
    """Root endpoint - redirects to documentation."""
    return {
        "message": "Skeldir Attribution Intelligence API",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

