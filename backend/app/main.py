from fastapi import FastAPI
from .database import engine
from . import models
from .routes import router

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "AI CRM API running"}