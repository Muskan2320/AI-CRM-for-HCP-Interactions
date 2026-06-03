from fastapi import FastAPI
from .database import engine
from . import models
from .routes import router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI CRM HCP",
    version="1.0.0",
    description="AI-powered CRM for healthcare professional interactions"
)
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "AI CRM API running"}