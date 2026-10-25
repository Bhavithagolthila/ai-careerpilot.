from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from app.config import settings


BCRYPT_MAX_BYTES = 72  # bcrypt only accepts 72 BYTES (not characters); newer versions raise above that


def password_fits(password: str) -> bool:
    return len(password.encode()) <= BCRYPT_MAX_BYTES


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    if not password_fits(password):  # cannot match any stored hash; avoid a 500 error
        return False
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str):
    try:
        sub = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"]).get("sub")
    except jwt.PyJWTError:
        return None
    return sub if isinstance(sub, str) else None
