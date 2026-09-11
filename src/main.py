# pour lancer le serveur : uv run uvicorn src.main:app --reload
from fastapi import FastAPI

app = FastAPI(title="ytastycrousty-g3")

# route health, renvoi status ok si le server est allumé
@app.get("/health")
def health():
    return {"status": "ok"}