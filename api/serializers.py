from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.storage import public_media_url
from models.insulation import Insulation


class InsulationOut(BaseModel):
    insulation_id: int
    insulation_name: str
    insulation_description: str | None
    status: int
    image_url: str
    video_url: str
    price: int
    coefficient: int
    created_at: datetime
    formed_at: datetime
    user_id: int
    like_marks: int
    warehouse: int | None
    notes: str | None


class InsulationFeedOut(InsulationOut):
    is_liked: Literal[0, 1] = Field(
        description="1 - like, 0 - no like",
    )


class InsulationPublishIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insulation_description: str | None = None
    price: int | None = Field(default=None, ge=0, allow_inf_nan=False)
    coefficient: int | None = Field(default=None, ge=0, allow_inf_nan=False)

    @field_validator("insulation_description")
    @classmethod
    def empty_description(cls, value: str | None) -> str | None:
        return value if value and value.strip() else None


class LikeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    like: Literal[0, 1] = Field(description="0 - remove, 1 - like")


class LikeOut(BaseModel):
    insulation_id: int
    like: Literal[0, 1]
    like_marks: int


class UserRegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    password: str


class AuthenticationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class StubOut(BaseModel):
    implemented: bool = False
    detail: str


def insulation_to_out(insulation: Insulation, *, like_marks: int, current_user_id: int) -> InsulationOut:
    return InsulationOut(
        insulation_id=insulation.id,
        insulation_name=insulation.title,
        insulation_description=insulation.description,
        status=insulation.status,
        image_url=insulation.image_url,
        video_url=insulation.video_url,
        price=insulation.price,
        coefficient=insulation.coefficient,
        created_at=insulation.created_at,
        formed_at=insulation.formed_at,
        user_id=insulation.user_id,
        is_creator=1 if insulation.user_id == current_user_id else 0,
        like_marks=like_marks,
        warehouse=insulation.warehouse,
        notes=insulation.notes
    )