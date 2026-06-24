from fastapi import FastAPI
from app.api.v1 import chat, memory, persona, emotion, care
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(persona.router, prefix="/api/v1/persona", tags=["Persona"])
app.include_router(emotion.router, prefix="/api/v1/emotion", tags=["Emotion"])
app.include_router(care.router, prefix="/api/v1/care", tags=["Care"])

@app.get("/")
async def root():
    return {"message": "校园情感陪伴助手 API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
