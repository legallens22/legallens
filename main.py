from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.scan import router as scan_router # Brings back your scanner routes

app = FastAPI(title="LegalLens AI")

# Unlocks the backend for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connects your API endpoints to the app
app.include_router(scan_router)