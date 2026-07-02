from fastapi import APIRouter

router = APIRouter()


@router.get("/topics")
async def get_topics():
    return {"topics": []}
