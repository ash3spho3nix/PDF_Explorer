from fastapi import APIRouter

router = APIRouter()


@router.get("/similarity")
async def get_similarity(doc_id: str = None, limit: int = 10):
    return {"doc_id": doc_id, "neighbors": []}
