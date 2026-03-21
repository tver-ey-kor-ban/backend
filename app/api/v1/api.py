from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import auth

app = FastAPI(title="Mobile App Backend")

# Important for Flutter: Allow your app to communicate with the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Include auth routes
api_v1_router.include_router(auth.router)

# Include v1 router in main app
app.include_router(api_v1_router)

@app.get("/")
async def root():
    return {"message": "Backend is running"}