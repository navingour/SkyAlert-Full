from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from web.services.config_manager import config_manager
from web.services.config_schema import config_schema

templates = Jinja2Templates(directory="web/templates")

router = APIRouter()


def update_config(config, form, prefix=""):

    for key, value in config.items():

        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):

            update_config(value, form, full_key)

        elif isinstance(value, bool):

            config[key] = full_key in form

        elif full_key not in form:

            continue

        elif isinstance(value, int):

            config[key] = int(form[full_key])

        elif isinstance(value, list):

            config[key] = [
                x.strip()
                for x in form[full_key].splitlines()
                if x.strip()
            ]

        else:

            config[key] = form[full_key]


@router.get("/settings")
async def settings(request: Request):

    config = config_manager.load()

    schema = config_schema.build(config)

    return templates.TemplateResponse(
        request=request,
        name="pages/settings.html",
        context={
            "request": request,
            "title": "Configuration",
            "schema": schema,
        },
    )


@router.post("/settings")
async def save_settings(request: Request):

    form = await request.form()

    config = config_manager.load()

    update_config(config, form)

    config_manager.save(config)

    return RedirectResponse(
        "/settings",
        status_code=303,
    )
