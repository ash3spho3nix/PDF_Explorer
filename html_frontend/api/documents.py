from fastapi import APIRouter, Query, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from html_frontend.adapters.documents import list_documents, get_document

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/documents")
async def api_list_documents(request: Request, response: Response, page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=500), q: str = None):
    data = list_documents(page=page, limit=limit, q=q)
    # expose total for clients
    response.headers["X-Total-Count"] = str(data.get("total", 0))

    # If HTMX requested an HTML fragment, render the documents table fragment
    if request.headers.get("hx-request"):
        return templates.TemplateResponse("fragments/documents_table.html", {"request": request, **data})

    return JSONResponse(content=data)


@router.get("/documents/{doc_id}")
async def api_get_document(request: Request, doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        return JSONResponse(content={"error": "not found"}, status_code=404)

    # HTMX could request an HTML fragment; for now return JSON
    if request.headers.get("hx-request"):
        return templates.TemplateResponse("fragments/document_detail_fragment.html", {"request": request, "item": doc})

    return JSONResponse(content=doc)
