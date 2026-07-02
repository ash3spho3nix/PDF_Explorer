from fastapi import APIRouter

router = APIRouter()


@router.get("/findings")
async def get_findings():
    return {"findings": []}
