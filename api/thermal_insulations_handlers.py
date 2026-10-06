from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from data.thermal_insulations_collections import thermal_insulators_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
def get_catalog(request: Request, id: int = 1, next: str = "false"):
    nextid = id + 1
    if next == "true":
        id += 1
        nextid = id + 1
    if id < 0 or id > len(thermal_insulators_db):
        id = 1
        nextid = 2
    if nextid > len(thermal_insulators_db):
        nextid = 1
    return templates.TemplateResponse(
        request=request,
        name="thermal_insulations_feed.html",
        context={"insulator": thermal_insulators_db[id-1], "liked": len(thermal_insulators_db[id-1]["likes"]), "nextid": nextid}
    )


@router.get("/add_thermal_insulations")
def get_catalog(request: Request):
    for i in thermal_insulators_db:
        if i["status"] == 2:
            id = i["id"]
            break
    return templates.TemplateResponse(
        request=request,
        name="thermal_insulations_add.html",
        context={"insulator": thermal_insulators_db[id]}
    )


@router.get("/list_thermal_insulations")
def get_catalog(request: Request, lower: int = 500, higher: int = 5000):
    temp_db = [i for i in thermal_insulators_db if lower <= i["price"] <= higher]
    return templates.TemplateResponse(
        request=request,
        name="thermal_insulations_list.html",
        context={"db": temp_db, "low": lower, "high": higher}
    )
