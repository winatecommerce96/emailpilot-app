from fastapi import FastAPI, Depends
from app.deps.firestore import get_db
import os

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "revision": os.getenv("K_REVISION")}

@app.get("/goals/{user_id}")
def get_goals(user_id: str, db = Depends(get_db)):
    docs = db.collection("goals").where("userId", "==", user_id).stream()
    return [d.to_dict() | {"id": d.id} for d in docs]
