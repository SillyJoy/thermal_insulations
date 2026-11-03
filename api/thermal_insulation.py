import asyncio

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.serializers import (
    InsulationFeedOut,
    InsulationOut,
    InsulationPublishIn,
    LikeIn,
    LikeOut,
    insulation_to_out,
)
from core.singleton import get_current_user_id
from core.storage import (
    MAX_FILE_BYTES,
    StorageError,
    ensure_bucket,
    extension_for,
    latin_object_name,
    upload_bytes,
)
from db.session import get_db
from models.insulation import (
    STATUS_DELETED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    Insulation,
    utc_now,
)
from models.like import Like
from models.user import User

router = APIRouter(prefix="/api/thermal_insulations", tags=["Утеплители"])

FORBIDDEN_CLIENT_FIELDS = {
    "insulation_id",
    "status",
    "user_id",
    "created_at",
    "formed_at"
}


async def _mark_counts(db: AsyncSession, insulation_ids: list[int]) -> dict[int, int]:
    if not insulation_ids:
        return {}
    result = await db.execute(
        select(Like.insulation_id, func.count(Like.user_id))
        .where(Like.insulation_id.in_(insulation_ids))
        .group_by(Like.insulation_id)
    )
    return {insulation_id: count for insulation_id, count in result.all()}


async def _feed_insulation(db: AsyncSession, insulation_id: int | None = None, *, next_item: bool = False) -> Insulation:
    stmt = select(Insulation).where(Insulation.status == STATUS_PUBLISHED)
    if insulation_id is not None:
        stmt = stmt.where(Insulation.id > insulation_id if next_item else Insulation.id == insulation_id)
    result = await db.execute(stmt.order_by(Insulation.id).limit(1))
    insulation = result.scalar_one_or_none()
    if insulation is None and next_item:
        return await _feed_insulation(db)
    if insulation is None:
        raise HTTPException(status_code=404, detail="Insulation not found")
    return insulation


async def _visible(db: AsyncSession, insulation_id: int) -> Insulation:
    result = await db.execute(
        select(Insulation).where(
            Insulation.id == insulation_id,
            Insulation.status != STATUS_DELETED,
        )
    )
    insulation = result.scalar_one_or_none()
    if insulation is None:
        raise HTTPException(status_code=404, detail="Insulation not found")
    return insulation


def _ensure_owner(insulation: Insulation, user_id: int) -> None:
    if insulation.user_id != user_id:
        raise HTTPException(status_code=403, detail="Can edit only owned insulators")


async def _outs(db: AsyncSession, insulations: list[Insulation]) -> list[InsulationOut]:
    user_id = get_current_user_id()
    counts = await _mark_counts(db, [insulation.id for insulation in insulations])
    return [
        insulation_to_out(
            insulation,
            like_marks=counts.get(insulation.id, 0),
            current_user_id=user_id,
        )
        for insulation in insulations
    ]


async def _out(db: AsyncSession, insulation: Insulation) -> InsulationOut:
    return (await _outs(db, [insulation]))[0]


async def _feed_out(db: AsyncSession, insulation: Insulation) -> InsulationFeedOut:
    out = await _out(db, insulation)
    mark = await db.execute(
        select(Like.id)
        .where(
            Like.insulation_id == insulation.id,
            Like.user_id == get_current_user_id(),
        )
        .limit(1)
    )
    return InsulationFeedOut(
        **out.model_dump(),
        is_liked=1 if mark.scalar_one_or_none() is not None else 0,
    )


async def _reject_system_fields(request: Request) -> None:
    form = await request.form()
    present = sorted(FORBIDDEN_CLIENT_FIELDS.intersection(form.keys()))
    if present:
        names = ", ".join(present)
        raise HTTPException(
            status_code=422,
            detail=f"System fields rejected: {names}",
        )


async def _require_user(db: AsyncSession, user_id: int) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=409,
            detail=f"User {user_id} from singleton not found",
        )


async def _store_media(kind: str, upload: UploadFile) -> str:
    data = await upload.read()
    if not data:
        title = "images" if kind == "image" else "video"
        raise HTTPException(status_code=422, detail=f"File {title} empty")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File bigger than 30 MB")
    try:
        extension = extension_for(kind, upload.content_type, upload.filename)
        object_name = latin_object_name(kind, extension)
    except StorageError as exc:
        raise HTTPException(status_code=415, detail=exc.detail) from exc
    content_type = upload.content_type or "application/octet-stream"
    try:
        await asyncio.to_thread(upload_bytes, object_name, data, content_type)
    except StorageError as exc:
        raise HTTPException(status_code=503, detail=exc.detail) from exc
    return object_name


@router.get("", response_model=list[InsulationOut], summary="List of insulators")
async def list_insulations(
    botttom_price: float | None = Query(
        default=None, ge=0, allow_inf_nan=False,
        description="Filter by lower price",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[InsulationOut]:
    if botttom_price is not None and botttom_price < 0:
        raise HTTPException(status_code=422, detail="Price cannot be negative")
    stmt = select(Insulation).where(Insulation.status == STATUS_PUBLISHED)
    if botttom_price is not None:
        stmt = stmt.where(Insulation.price >= botttom_price)
    result = await db.execute(stmt.order_by(Insulation.id))
    return await _outs(db, list(result.scalars().all()))


@router.get("/feed", response_model=InsulationFeedOut, summary="Insulators feed")
async def feed(
    insulation_id: int | None = Query(default=None, gt=0),
    next_item: bool = Query(
        False, alias="next", description="Next after insulation_id",
    ),
    db: AsyncSession = Depends(get_db),
) -> InsulationFeedOut:
    if next_item and insulation_id is None:
        raise HTTPException(status_code=422, detail="For next=true set insulation_id")
    return await _feed_out(db, await _feed_insulation(db, insulation_id, next_item=next_item))


@router.get("/draft", response_model=InsulationOut, summary="User draft")
async def get_draft(db: AsyncSession = Depends(get_db)) -> InsulationOut:
    result = await db.execute(
        select(Insulation).where(
            Insulation.status == STATUS_DRAFT,
            Insulation.user_id == get_current_user_id(),
        )
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return await _out(db, draft)


@router.post("", response_model=InsulationOut, status_code=201, summary="Add insulator")
async def create_insulation(
    request: Request,
    insulation_name: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> InsulationOut:
    await _reject_system_fields(request)
    extra_fields = set((await request.form()).keys()) - {"insulation_name", "image", "video"}
    if extra_fields:
        raise HTTPException(
            status_code=422,
            detail="Required insulation_name, image and video. "
            "Other parameters can be passed through PUT",
        )
    user_id = get_current_user_id()
    await _require_user(db, user_id)

    name = insulation_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Insulator title required")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="Name is longer than 100 symbols")
    existing = await db.execute(
        select(Insulation.id).where(
            Insulation.status == STATUS_DRAFT,
            Insulation.user_id == get_current_user_id(),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Draft already exists",
        )

    try:
        await asyncio.to_thread(ensure_bucket)
    except StorageError as exc:
        raise HTTPException(status_code=503, detail=exc.detail) from exc

    image_name = await _store_media("image", image)
    video_name = await _store_media("video", video)
    now = utc_now()
    insulation = Insulation(
        title=name,
        description="",
        status=STATUS_DRAFT,
        image_url=image_name,
        video_url=video_name,
        coefficient=0,
        price=0,
        created_at=now,
        formed_at=now,
        user_id=user_id,
    )
    db.add(insulation)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Draft already exists.",
        ) from None
    await db.refresh(insulation)
    return await _out(db, insulation)


@router.put(
    "/{insulation_id}",
    response_model=InsulationOut,
    summary="Publish draft",
)
async def publish_insulation(
    insulation_id: int,
    body: InsulationPublishIn | None = None,
    db: AsyncSession = Depends(get_db),
) -> InsulationOut:
    insulation = await _visible(db, insulation_id)
    _ensure_owner(insulation, get_current_user_id())
    if insulation.status != STATUS_DRAFT:
        raise HTTPException(
            status_code=409,
            detail="You can only publish draft",
        )
    if body is not None:
        for name, value in body.model_dump(exclude_unset=True).items():
            setattr(insulation, name, value)
    insulation.status = STATUS_PUBLISHED
    insulation.formed_at = utc_now()
    await db.commit()
    await db.refresh(insulation)
    return await _out(db, insulation)


@router.delete("/{insulation_id}", status_code=204, summary="Delete insulator")
async def delete_insulation(
    insulation_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    insulation = await _visible(db, insulation_id)
    _ensure_owner(insulation, get_current_user_id())
    insulation.status = STATUS_DELETED
    await db.commit()


@router.post(
    "/{insulation_id}/likes",
    response_model=LikeOut,
    summary="User like",
)
async def set_like(
    insulation_id: int,
    body: LikeIn,
    db: AsyncSession = Depends(get_db),
) -> LikeOut:
    user_id = get_current_user_id()
    await _require_user(db, user_id)

    result = await db.execute(
        select(Insulation).where(
            Insulation.id == insulation_id,
            Insulation.status == STATUS_PUBLISHED,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Insulator not found")

    existing = await db.execute(
        select(Like).where(Like.user_id == user_id, Like.insulation_id == insulation_id)
    )
    mark = existing.scalar_one_or_none()
    if body.like == 1 and mark is None:
        db.add(Like(user_id=user_id, insulation_id=insulation_id))
    elif body.like == 0 and mark is not None:
        await db.delete(mark)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Already liked") from None

    count = await db.execute(
        select(func.count()).select_from(Like).where(Like.insulation_id == insulation_id)
    )
    return LikeOut(
        insulation_id=insulation_id,
        like=body.like,
        like_marks=count.scalar() or 0,
    )