from fastapi import FastAPI

from app.api.routers import (
    auth,
    business,
    canopy,
    critical_specs,
    opportunities,
    products,
    quotes,
    recipes,
    site_knowledge,
    site_quality,
    suppliers,
    website,
)

app = FastAPI(title="NP Planning")
app.include_router(auth.router)
app.include_router(business.router)
app.include_router(canopy.router)
app.include_router(quotes.router)
app.include_router(opportunities.router)
app.include_router(critical_specs.router)
app.include_router(site_quality.router)
app.include_router(site_knowledge.router)
app.include_router(website.router)
app.include_router(suppliers.router)
app.include_router(recipes.router)
app.include_router(products.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
