from fastapi import FastAPI

from app.api.v1.routers import v1_router

app = FastAPI()

app.include_router(v1_router)
