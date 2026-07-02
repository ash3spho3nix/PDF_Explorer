from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from html_frontend.adapters.stats import get_stats as adapter_get_stats

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/stats")
async def get_stats(request: Request):
    stats = adapter_get_stats()

    # If HTMX requested HTML, render a stats fragment
    if request.headers.get("hx-request"):
        return templates.TemplateResponse("fragments/stats.html", {"request": request, "stats": stats})

    return JSONResponse(content=stats)