from datetime import datetime, timedelta
from typing import Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from config import Config
from pydantic import BaseModel

class TokenData(BaseModel):
    user_id: Union[int, None] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    display_name: str

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password, hashed_password)

def authenticate_user(db, user_orm, username: str, password: str):
    user = db.query(user_orm).filter_by(username=username).first()
    userpasswd = user.password if Config.DB != "mysql" else user.password.encode('utf-8')
    if not user:
        return False
    if not verify_password(password.encode('utf-8'), userpasswd):
        return False
    return user

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + Config.JWT_ACCESS_TOKEN_EXPIRES
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
    return encoded_jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(db, user_orm, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token,  Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    user = db.query(user_orm).filter_by(id=token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user
