from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.database import get_db
from app.deps import get_current_user
from app.ratelimit import login_limiter
from app.security import create_access_token, hash_password, password_fits, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, v: str) -> str:
        if not password_fits(v):  # 72 characters can exceed 72 bytes with non-ASCII characters
            raise ValueError("Password is too long (max 72 bytes; non-English characters count as several)")
        return v


def public(user):
    return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}


@router.post("/register", status_code=201)
def register(data: RegisterIn, db=Depends(get_db)):
    email = data.email.lower()
    if db.users.find_one({"email": email}):
        raise HTTPException(409, "An account with this email already exists")
    user = {"name": data.name.strip(), "email": email, "password_hash": hash_password(data.password),
            "created_at": datetime.now(timezone.utc)}
    user["_id"] = db.users.insert_one(user).inserted_id
    return public(user)


@router.post("/login")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    key = f"{request.client.host if request.client else 'unknown'}|{form.username.lower()}"
    wait = login_limiter.blocked_for(key)
    if wait:
        raise HTTPException(429, f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s).",
                            headers={"Retry-After": str(wait)})
    user = db.users.find_one({"email": form.username.lower()})
    if not user or not verify_password(form.password, user["password_hash"]):
        login_limiter.record_failure(key)
        raise HTTPException(401, "Incorrect email or password")
    login_limiter.reset(key)
    return {"access_token": create_access_token(str(user["_id"])), "token_type": "bearer"}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return public(user)
