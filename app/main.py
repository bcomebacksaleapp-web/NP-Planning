from fastapi import FastAPI

from app.api.routers import auth, business, canopy, quotes

app = FastAPI(title="NP Planning")
app.include_router(auth.router)
app.include_router(business.router)
app.include_router(canopy.router)
app.include_router(quotes.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
