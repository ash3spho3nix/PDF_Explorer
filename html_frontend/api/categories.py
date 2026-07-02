from fastapi import APIRouter

router = APIRouter()


@router.get("/categories")
async def get_categories():
    # Minimal placeholder; adapter to be implemented
    return {"categories": []}
