from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app.database import get_db
from app.security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2), db=Depends(get_db)):
    uid = decode_token(token)
    user = db.users.find_one({"_id": ObjectId(uid)}) if uid and ObjectId.is_valid(uid) else None
    if not user:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    return user


def oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(404, "Not found")
    return ObjectId(value)
