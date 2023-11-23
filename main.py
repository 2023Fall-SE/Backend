import json
import os
from typing import Annotated
from fastapi import FastAPI, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import  OAuth2PasswordRequestForm
import bcrypt
import model
from model import User
from schema import UserCreate
from database import SessionLocal, engine
import uvicorn
from sqlalchemy.orm.session import Session
from shared.auth import Token, authenticate_user, create_access_token, get_current_user, oauth2_scheme

db_dir = os.getcwd() + "/database/"
if not os.path.isdir(os.getcwd() + db_dir):
    os.mkdir(db_dir)

model.Base.metadata.create_all(bind=engine)
app = FastAPI()
origins = [
    "http://localhost",
    "http://localhost:3000",
]
app.add_middleware(CORSMiddleware,
                    allow_origins=origins,
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"])
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/token-check", status_code=status.HTTP_200_OK)
def token_check(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    user = get_current_user(db, User, token)
    if user:
        return user.as_dict().pop("password")
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")

@app.post("/login", status_code=status.HTTP_200_OK, response_model=Token)
def user_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    username, password = form_data.username, form_data.password
    user = authenticate_user(db, User, username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤")
    else:
        user_token = create_access_token({"user_id": user.id})
        res = Token(access_token=user_token, token_type="bearer")
        return res

@app.post("/user", status_code=status.HTTP_201_CREATED)
def create_user(user_form: UserCreate, db: Session = Depends(get_db)):
    username, password, display_name, phone, = user_form.username, user_form.password, user_form.display_name, user_form.phone
    is_exist = db.query(User).filter_by(username=username).first()
    if is_exist:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="帳號已被註冊")
    else:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf8'), salt)
        user = User(
            username=username,
            password=hashed,
            display_name=display_name,
            phone=phone,
            carpool_money=50
        )
        db.add(user)
        db.commit()
        return {"user_id": user.id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")

