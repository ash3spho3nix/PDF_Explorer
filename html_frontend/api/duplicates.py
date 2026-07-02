from fastapi import APIRouter

router = APIRouter()


@router.get("/duplicates")
async def get_duplicates():
    return {"duplicates": []}
