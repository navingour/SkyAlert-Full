from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(
    directory="web/templates"
)


router = APIRouter()


@router.get("/aircraft")
async def aircraft_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="pages/aircraft.html",
        context={
            "request": request,
            "title": "Live Aircraft"
        }
    )
