"""
Aahar-Rx FastAPI Backend Application
Strictly compliant with GEMINI.md, DPDP Act 2023, and ANVESHAN Rule 3 (Full Anonymity).
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints import router as api_v1_router
from app.core.config import settings
from app.schemas.clinical import MANDATORY_CLINICAL_DISCLAIMER

# Strict Anonymity (ANVESHAN Rule 3): No personal, university, or mentor names
app = FastAPI(
    title=settings.app_title,
    description=(
        "Food-Drug Interaction & Safe Time-Gap Guidance System for Indian Polypharmacy. "
        "Enforces DPDP Act 2023 consent protocols and evidence-backed ICMR-NIN IFCT dietary swaps."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration for Cross-Origin Frontend Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Modular API Router
app.include_router(api_v1_router)

# -----------------------------------------------------------------------------
# Structured JSON Error Handlers
# -----------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "clinical_disclaimer": MANDATORY_CLINICAL_DISCLAIMER
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "detail": "Request payload validation error",
            "validation_errors": exc.errors(),
            "path": request.url.path,
            "clinical_disclaimer": MANDATORY_CLINICAL_DISCLAIMER
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "An internal clinical computation error occurred.",
            "path": request.url.path,
            "clinical_disclaimer": MANDATORY_CLINICAL_DISCLAIMER
        }
    )

# -----------------------------------------------------------------------------
# Health Check Endpoint
# -----------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["System"],
    summary="Clinical Engine Health Check"
)
async def health_check():
    return {
        "status": "HEALTHY",
        "service": "Aahar-Rx Clinical Guidance Engine",
        "dpdp_compliance": "DPDP Act 2023 Active",
        "clinical_disclaimer": MANDATORY_CLINICAL_DISCLAIMER
    }
