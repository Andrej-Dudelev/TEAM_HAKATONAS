from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Pages"], include_in_schema=False)

templates = Jinja2Templates(directory="app/template")

@router.get("/chat", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse(
        name="tikras_chatas.html",
        context={"request": request}
    )

@router.get("/", response_class=RedirectResponse)
async def root():
    return "/chat"