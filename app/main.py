from fastapi import FastAPI

from app.api.routers import auth, business

app = FastAPI(title="NP Planning")
app.include_router(auth.router)
app.include_router(business.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
