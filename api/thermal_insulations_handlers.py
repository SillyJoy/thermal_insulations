from typing import Annotated
from sqlalchemy import select, text, update
from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from models.insulation import Insulation
from models.like import Like

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def get_catalog(request: Request, id: int = 1, next: str = "false", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Insulation).where(Insulation.id == id, Insulation.status == 1))
    res_ins = result.scalar_one_or_none()
    if res_ins is None:
        id = 1
        result = await db.execute(select(Insulation).where(Insulation.id == id, Insulation.status == 1))
        res_ins = result.scalar_one_or_none()

    liked_result = await db.execute(select(Like.user_id).where(Like.insulation_id == id))
    temp = liked_result.all()
    liked = 1 in [row[0] for row in temp]
    likes = len(temp)

    nextid = id + 1
    if next == "true":
        id += 1
        nextid = id + 1
    return templates.TemplateResponse(
        request=request,
        name="thermal_insulations_feed.html",
        context={"insulator": res_ins, "liked": liked, "likes": likes, "nextid": nextid}
    )


@router.get("/add_thermal_insulations")
async def get_catalog(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Insulation).where(Insulation.status == 2))
    draft = result.scalar_one_or_none()
    return templates.TemplateResponse(
        request=request,
        name="thermal_insulations_add.html",
        context={"draft": draft, "publish": draft is None}
    )


@router.get("/list_thermal_insulations")
async def get_catalog(request: Request, lower: int = 500, higher: int = 5000, db: AsyncSession = Depends(get_db)):
    stmt = select(Insulation).where(Insulation.status == 1, lower <= Insulation.price, Insulation.price <= higher)
    result = await db.execute(stmt)
    insulation = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="thermal_insulations_list.html",
        context={"db": insulation, "low": lower, "high": higher}
    )


@router.post("/insulation/{insulation_id}/delete")
async def delete_hotel(insulation_id: int, db: AsyncSession = Depends(get_db)):
    update_query = """
        UPDATE insulations
        SET status = 0 
        WHERE id = :id
    """

    # Выполняем запрос через курсор
    await db.execute(text(update_query), {"id": insulation_id})
    await db.commit()

    # Перенаправляем пользователя обратно на главную страницу
    return RedirectResponse(url="/list_thermal_insulations", status_code=303)


@router.post("/insulation/add")
async def add_hotel(title: Annotated[str, Form()], descr: Annotated[str, Form()], coef: Annotated[int, Form()], price: Annotated[int, Form()], db: AsyncSession = Depends(get_db)):
    db.add(Insulation(title=title, description=descr, coefficient=coef, price=price, video_url="", image_url="", status=2, user_id=1))
    await db.commit()
    return RedirectResponse(url="/add_thermal_insulations", status_code=303)


@router.post("/insulation/{insulation_id}/publish")
async def publish_hotel(insulation_id: int, db: AsyncSession = Depends(get_db)):
    stmt = update(Insulation).where(Insulation.id == insulation_id).values(status=1)
    result = await db.execute(stmt)
    print(result)
    await db.commit()
    return RedirectResponse(url="/add_thermal_insulations", status_code=303)
