from fastapi import FastAPI

app = FastAPI(title="NP Planning")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
