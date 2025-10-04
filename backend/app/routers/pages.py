from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse


router = APIRouter()


def _jinja_url_for(request: Request):
    def _inner(name: str, **kwargs):
        # Translate Flask-style static arg to Starlette's
        if name == "static" and "filename" in kwargs:
            kwargs = {"path": kwargs.pop("filename")}
        return request.url_for(name, **kwargs)

    return _inner


@router.get("/", name="main.index", response_class=HTMLResponse)
def index(request: Request):
    templates: Jinja2Templates = request.app.state.templates
    settings = request.app.state.settings
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "config": settings, "url_for": _jinja_url_for(request)},
    )


@router.get("/pressure", name="main.pressure", response_class=HTMLResponse)
def pressure(request: Request):
    templates: Jinja2Templates = request.app.state.templates
    settings = request.app.state.settings
    return templates.TemplateResponse(
        "pressure.html",
        {"request": request, "config": settings, "url_for": _jinja_url_for(request)},
    )


@router.get("/thermocouples", name="main.thermocouples", response_class=HTMLResponse)
def thermocouples(request: Request):
    templates: Jinja2Templates = request.app.state.templates
    settings = request.app.state.settings
    return templates.TemplateResponse(
        "thermocouples.html",
        {"request": request, "config": settings, "url_for": _jinja_url_for(request)},
    )


@router.get("/valves", name="main.valves", response_class=HTMLResponse)
def valves(request: Request):
    templates: Jinja2Templates = request.app.state.templates
    settings = request.app.state.settings
    return templates.TemplateResponse(
        "valves.html",
        {"request": request, "config": settings, "url_for": _jinja_url_for(request)},
    )

