import json
import os
from typing import Annotated
from fastapi import FastAPI, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import  OAuth2PasswordRequestForm
import bcrypt
import model
from model import User, Event
from schema import UserCreate, CreateEventBase, UserId, EventId, FindLocationForm
from database import SessionLocal, engine
import uvicorn
from sqlalchemy.orm.session import Session
from shared.auth import Token, authenticate_user, create_access_token, get_current_user, oauth2_scheme
from datetime import datetime

db_dir = os.getcwd() + "/database/"
if not os.path.isdir(db_dir):
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

# (5)搜尋
@app.get("/find-carpool", status_code=status.HTTP_200_OK)
def find_carpool(startLocation:str, endLocation:str, db: Session = Depends(get_db)):
    # find SQL
    # startLocation, endLocation = location.start_location, location.end_location
    # events = db.query(Event).filter(Event.available_seats > -1).all()
    search = "%{}%".format("," + startLocation + ",")
    events = db.query(Event).filter(Event.location.like(search)).all()
    eventList = []
    for event in events:
        temp_location= event.location[event.location.index(startLocation)+len(startLocation):]
        if  (endLocation in temp_location):
            eventList.append(event)
    # return
    if len(eventList) == 0:
        return {"result" : "None"}
    return eventList




# (6)加入此共乘     建議把上下 及搜尋刪除
@app.post("/join-the-carpool", status_code=status.HTTP_200_OK)
def join_the_carpool(eventForm:EventId, user:UserId, db: Session = Depends(get_db)):
    event = db.query(Event).filter_by(id=eventForm.event_id).first()
    if not event:
       raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此Event")
    user = db.query(User).filter_by(id=user.user_id).first()
    if not user:
       raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此User")
    if event.available_seats < 1:
       raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="位子不夠")
    if str(user.id) in event.joiner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="使用者已在此Event")
    newJoiner = event.joiner + str(user.id) + ','
    event.joiner = newJoiner
    event.available_seats = event.available_seats - 1
    db.commit()
    return {"result" : "success"}


# (7)(8) 已加入的共乘
@app.get("/search-joined-event", status_code=status.HTTP_200_OK)
def search_joined_event(user_id:int, db: Session = Depends(get_db)):
    # user_id = str(user.user_id)
    search = "%{}%".format("," + str(user_id) + ",")
    events = db.query(Event).filter(Event.joiner.like(search)).all()
    print(search)
    if len(events) == 0:
        return {"result" : "None"}
    return events




# (7)(8) 共乘聊天室
@app.get("/carpool-chat-room/{eventID}", status_code=status.HTTP_200_OK)
def carpool_chat_room(eventID:int, db: Session = Depends(get_db)):
   # find SQL
   # add the info to DB
   # return chat_room
   return {"result" : "success"}




# (7) 結束此共乘
@app.post("/end-the-carpool", status_code=status.HTTP_200_OK)
def  end_the_carpool(eventID:EventId, db: Session = Depends(get_db)):
    event = db.query(Event).filter_by(id = eventID.event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此Event")
    if event.end_time != None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event已結束")
    db.query(Event).filter_by(id=eventID.event_id).update({'end_time':datetime.now()})
    db.query(Event).filter_by(id=eventID.event_id).update({'available_seats':0})
    db.commit()
    return {"result" : "success"}



# (10) 新增共乘, otherLocation use comma to split
# @app.get("/InitiateCarpoolEventUI/{userID}/{numberOfPeople}/{selfdriveOrNot}/{startLocation}/{endLocation}/{otherLocation}")
@app.post("/initiate-carpool-event-ui", status_code=status.HTTP_200_OK)
def create_new_carpool(eventForm: CreateEventBase, db: Session = Depends(get_db)):
    # user_id, initiator, start_time, self_drive_or_not, number_of_people, start_location, 
    user_id, start_time, self_drive_or_not, number_of_people = eventForm.user_id, eventForm.start_time, eventForm.self_drive_or_not, eventForm.number_of_people
    #check user_id
    user = db.query(User).filter_by(id=eventForm.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")

    # check license
    if self_drive_or_not:
        initiator = db.query(User).filter_by(id=user_id).first()
        if not initiator.license:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無駕照")

    # check date
    if start_time.timestamp() < datetime.now().timestamp():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="日期輸入錯誤")


    stops = ",".join(eventForm.other_location)
    wholeLocation = ',' + eventForm.start_location + ',' + stops + ',' + eventForm.end_location + ','
    addEvent = Event(initiator=user_id, 
                joiner=',' + str(user_id) + ',',
                location=wholeLocation, 
                start_time=start_time, 
                is_self_drive=self_drive_or_not,
                number_of_people=number_of_people, 
                available_seats=number_of_people-1)
    db.add(addEvent)
    db.commit()
    # return success or fail
    return {"Event_Id" : addEvent.id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")
