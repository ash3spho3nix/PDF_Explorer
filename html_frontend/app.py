
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

from .api import stats, documents, categories, topics, duplicates, similarity, findings, search, charts

app = FastAPI(title="PDF Explorer")

_HERE = Path(__file__).parent

# Mount static files
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(_HERE / "templates"))

# Include routers
app.include_router(stats.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(topics.router, prefix="/api")
app.include_router(duplicates.router, prefix="/api")
app.include_router(similarity.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(charts.router, prefix="/api")


@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/documents")
async def documents_page(request: Request):
    return templates.TemplateResponse("documents.html", {"request": request})


@app.get("/documents/{doc_id}")
async def document_detail(request: Request, doc_id: str):
    return templates.TemplateResponse("document_detail.html", {"request": request, "doc_id": doc_id})


@app.get("/categories")
async def categories_page(request: Request):
    return templates.TemplateResponse("categories.html", {"request": request})


@app.get("/topics")
async def topics_page(request: Request):
    return templates.TemplateResponse("topics.html", {"request": request})


@app.get("/duplicates")
async def duplicates_page(request: Request):
    return templates.TemplateResponse("duplicates.html", {"request": request})


@app.get("/similarity")
async def similarity_page(request: Request):
    return templates.TemplateResponse("similarity.html", {"request": request})


@app.get("/findings")
async def findings_page(request: Request):
    return templates.TemplateResponse("findings.html", {"request": request})