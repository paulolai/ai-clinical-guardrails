from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(directory="pwa/frontend/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Home page with patient list."""
    return templates.TemplateResponse("base.html", {"request": request})
