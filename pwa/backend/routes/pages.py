from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

# Use absolute path from project root for templates
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Home page with patient list."""
    return templates.TemplateResponse("base.html", {"request": request})
