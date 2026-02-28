from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Chatbot.core.config import settings
from Chatbot.core.database import engine
from Chatbot.models import base
from Chatbot.routers import auth, chat

# Initialize DB tables
base.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for CSIS SmartAssist",
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])

@app.get("/")
def read_root():
    return {"message": "Welcome to CSIS SmartAssist Backend API!"}
