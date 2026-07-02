from fastapi import APIRouter
from html_frontend.adapters.stats import get_stats as adapter_get_stats

router = APIRouter()


@router.get("/charts/storage")
async def storage_chart():
    stats = adapter_get_stats()
    # Expect stats to include storage distribution e.g., stats['distributions']['storage']
    storage = stats.get("distributions", {}).get("storage", {})
    labels = list(storage.keys())
    values = [storage[k] for k in labels]
    return {"labels": labels, "values": values}


@router.get("/charts/categories")
async def categories_chart():
    stats = adapter_get_stats()
    cats = stats.get("distributions", {}).get("categories", {})
    labels = list(cats.keys())
    values = [cats[k] for k in labels]
    return {"labels": labels, "values": values}
