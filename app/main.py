from fastapi import FastAPI

from app.api.routers import auth, business, canopy, critical_specs, opportunities, quotes, site_quality

app = FastAPI(title="NP Planning")
app.include_router(auth.router)
app.include_router(business.router)
app.include_router(canopy.router)
app.include_router(quotes.router)
app.include_router(opportunities.router)
app.include_router(critical_specs.router)
app.include_router(site_quality.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
