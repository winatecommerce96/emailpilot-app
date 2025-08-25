from fastapi import APIRouter

router = APIRouter()

@router.get("/clients2")
def goals_by_client2():
    return {"message": "Hello from goals2"}
