from fastapi import APIRouter
from .endpoints import health, enrollment, authentication, face, voice, audit

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(enrollment.router, tags=["Enrollment"])
api_router.include_router(authentication.router, prefix="/authentication", tags=["Authentication"])
api_router.include_router(face.router, prefix="/face", tags=["Face Pipeline"])
api_router.include_router(voice.router, prefix="/voice", tags=["Voice Pipeline"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit & Forensics"])

