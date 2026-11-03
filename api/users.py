from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.serializers import AuthenticationIn, StubOut, UserOut, UserRegisterIn
from db.session import get_db
from models.user import User

router = APIRouter(prefix="/api", tags=["Users"])


@router.post("/users", response_model=UserOut, status_code=201, summary="Register")
async def register_user(body: UserRegisterIn, db: AsyncSession = Depends(get_db)) -> UserOut:
    username = body.username.strip()
    password = body.password.strip()
    if not username or not password:
        raise HTTPException(status_code=422, detail="Supply username and password")

    user = User(username=username, password=password)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Usename is taken") from None
    await db.refresh(user)
    return UserOut(user_id=user.id, username=user.username, password=user.password)


@router.post("/authentication", response_model=StubOut, summary="STUB")
async def authenticate(_body: AuthenticationIn) -> StubOut:
    return StubOut(implemented=False, detail="STUB")


@router.post("/deauthentication", response_model=StubOut, summary="STUB")
async def deauthenticate() -> StubOut:
    return StubOut(implemented=False, detail="STUB")
