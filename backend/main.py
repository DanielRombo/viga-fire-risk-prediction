from fastapi import FastAPI

app = FastAPI(title="VIGA API")


@app.get("/health")
def health():
    return {"status": "ok", "service": "VIGA"}
