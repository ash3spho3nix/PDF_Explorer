from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/search")
async def search(q: str = Query(None)):
    return {"q": q, "results": []}
