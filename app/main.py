from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routers import (
    auth,
    business,
    canopy,
    critical_specs,
    inquiries,
    opportunities,
    products,
    quotes,
    recipes,
    site_knowledge,
    site_quality,
    sites,
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
app.include_router(sites.router)
app.include_router(website.router)
app.include_router(suppliers.router)
app.include_router(recipes.router)
app.include_router(products.router)
app.include_router(inquiries.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


_WEB_DIR = Path(__file__).parent / "web"


@app.get("/site")
def website_demo_site() -> FileResponse:
    """The real N.S. Construct site renderer -- fetches its content client-side from
    /website/pages/{branch}/{slug} (same origin, so no CORS/CSP issue) instead of hardcoding it,
    unlike the earlier standalone demo. See app/web/site.html."""
    return FileResponse(_WEB_DIR / "site.html")


@app.get("/site/editor")
def website_demo_editor() -> FileResponse:
    return FileResponse(_WEB_DIR / "editor.html")
