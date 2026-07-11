import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import UserProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfilePayload(BaseModel):
    full_name: str = Field(min_length=3, max_length=180)
    phone: str = Field(min_length=8, max_length=30)
    cpf: str = Field(min_length=11, max_length=14)
    birth_date: date
    zip_code: str = Field(min_length=8, max_length=9)
    street: str = Field(min_length=2, max_length=180)
    number: str = Field(min_length=1, max_length=30)
    complement: str = Field(default="", max_length=120)
    lot: str = Field(default="", max_length=30)
    block: str = Field(default="", max_length=30)
    building: str = Field(default="", max_length=30)
    apartment: str = Field(default="", max_length=30)
    neighborhood: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=2)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _serialize(profile: UserProfile | None) -> dict:
    if profile is None:
        return {"completed": False, "profile": None}
    return {
        "completed": bool(profile.completed),
        "profile": {
            "fullName": profile.full_name,
            "phone": profile.phone,
            "cpf": profile.cpf,
            "birthDate": profile.birth_date.isoformat() if profile.birth_date else "",
            "zipCode": profile.zip_code,
            "street": profile.street,
            "number": profile.number,
            "complement": profile.complement,
            "lot": profile.lot,
            "block": profile.block,
            "building": profile.building,
            "apartment": profile.apartment,
            "neighborhood": profile.neighborhood,
            "city": profile.city,
            "state": profile.state,
        },
    }


@router.get("")
def get_profile(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        return _serialize(db.get(UserProfile, user_id))


@router.put("")
def save_profile(payload: ProfilePayload, session: dict = Depends(require_authenticated_user)):
    cpf = _digits(payload.cpf)
    phone = _digits(payload.phone)
    zip_code = _digits(payload.zip_code)

    if len(cpf) != 11:
        raise HTTPException(status_code=400, detail="Informe um CPF válido com 11 dígitos.")
    if len(phone) < 10:
        raise HTTPException(status_code=400, detail="Informe um telefone válido com DDD.")
    if len(zip_code) != 8:
        raise HTTPException(status_code=400, detail="Informe um CEP válido com 8 dígitos.")
    if payload.birth_date >= date.today():
        raise HTTPException(status_code=400, detail="Informe uma data de nascimento válida.")

    user_id = session.get("sub")
    with session_scope() as db:
        profile = db.get(UserProfile, user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            db.add(profile)

        profile.full_name = payload.full_name.strip()
        profile.phone = phone
        profile.cpf = cpf
        profile.birth_date = payload.birth_date
        profile.zip_code = zip_code
        profile.street = payload.street.strip()
        profile.number = payload.number.strip()
        profile.complement = payload.complement.strip()
        profile.lot = payload.lot.strip()
        profile.block = payload.block.strip()
        profile.building = payload.building.strip()
        profile.apartment = payload.apartment.strip()
        profile.neighborhood = payload.neighborhood.strip()
        profile.city = payload.city.strip()
        profile.state = payload.state.strip().upper()
        profile.completed = 1
        db.flush()
        return _serialize(profile)
