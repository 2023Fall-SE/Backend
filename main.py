import json
import os
from typing import Annotated
from fastapi import FastAPI, Depends, status, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.testclient import TestClient
import bcrypt
import model
from model import User, Event, Payment
from schema import UserCreate, CreateEventBase, UserId, EventJoin, EventId, FindLocationForm, UserView, UserLicense, EventIdAndUserId
from database import SessionLocal, engine
import uvicorn
from sqlalchemy.orm.session import Session
from sqlalchemy import or_
from shared.auth import Token, authenticate_user, create_access_token, get_current_user, oauth2_scheme
from shared.payment import create_payment
from shared.linepay_service import create_order, create_confirm
from shared.pusher_util import send_push_notification
from datetime import datetime, timedelta
from config import Config
import random
import string
from starlette.responses import FileResponse
import requests
from httpx import AsyncClient


db_dir = os.getcwd() + "/database/"
if not os.path.isdir(db_dir):
    os.mkdir(db_dir)

if not os.path.isdir(Config.LICENSE_UPLOAD_PATH):
    os.mkdir(Config.LICENSE_UPLOAD_PATH)

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

@app.post("/login", status_code=status.HTTP_200_OK, response_model=dict)
def user_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    username, password = form_data.username, form_data.password
    user = authenticate_user(db, User, username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤")
    else:
        user_token = create_access_token({"user_id": user.id})
        res = Token(access_token=user_token, token_type="bearer", user_id=str(user.id))
        return res

@app.post("/user", status_code=status.HTTP_201_CREATED)
def create_user(user_form: UserCreate, db: Session = Depends(get_db)):
    username, password, display_name, phone, mail = user_form.username, user_form.password, user_form.display_name, user_form.phone, user_form.mail
    is_exist = db.query(User).filter_by(username=username).first()

    if is_exist:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="帳號已被註冊")

    same_name_user = db.query(User).filter_by(display_name=display_name).first()
    if same_name_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此使用者名稱已被使用")

    if phone:
        user_with_phone = db.query(User).filter_by(phone=phone).first()
        if user_with_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此手機號碼已被使用")

    if mail:
        user_with_mail = db.query(User).filter_by(mail=mail).first()
        if user_with_mail:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此信箱已被使用")

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf8'), salt)
    user = User(
        username=username,
        password=hashed,
        display_name=display_name,
        phone=phone,
        carpool_money=50,
        mail=mail,
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
        temp_location = event.location[event.location.index(startLocation)+len(startLocation):]
        if f",{endLocation}," in temp_location:
            eventList.append(event)
    # return
    if len(eventList) == 0:
        return {"result" : "None"}
    return eventList


# (6)加入此共乘     建議把上下 及搜尋刪除
@app.post("/join-the-carpool", status_code=status.HTTP_200_OK)
def join_the_carpool(eventForm:EventJoin, db: Session = Depends(get_db)):
    event = db.query(Event).filter_by(id=eventForm.event_id).first()

    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此Event")
    user = db.query(User).filter_by(id=eventForm.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此User")
    if event.available_seats < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="位子不夠")
    if str(user.id) in event.joiner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="使用者已在此Event")
    

    #find the location id and update the joiner_to_loc column
    loc_list = event.location.split(',')
    if eventForm.start_loc not in loc_list:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="起始地點無效")

    if eventForm.end_loc not in loc_list or loc_list.index(eventForm.end_loc) <= loc_list.index(eventForm.start_loc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="結束地點無效")
    
    newJoiner = event.joiner + str(user.id) + ','
    event.joiner = newJoiner
    event.available_seats = event.available_seats - 1

    start_loc_idx, end_loc_idx = loc_list.index(eventForm.start_loc), loc_list.index(eventForm.end_loc)
    joiner_loc_str = f"{start_loc_idx-1}-{end_loc_idx-1},"
    event.joiner_to_location = event.joiner_to_location + joiner_loc_str
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
async def end_the_carpool(eventID:EventId, db: Session = Depends(get_db)):
    event = db.query(Event).filter_by(id = eventID.event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此Event")
    if event.end_time != None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event已結束")
    db.query(Event).filter_by(id=eventID.event_id).update({'end_time':datetime.now()})
    db.query(Event).filter_by(id=eventID.event_id).update({'available_seats':0})
    db.commit()
    
    #create payment and send reward notification to initiator on success
    if event.end_time > event.start_time:
        oncreate = create_payment(event, db) #create Payment instances for joiners and calculate payables respectively
        if not oncreate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment創建失敗")
        
        rewardapi_url = f"{Config.BACKEND_URL}/send-reward/{event.initiator}"
        
        async with AsyncClient() as client:
            response = await client.post(rewardapi_url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
    return {"result" : "success"}


# (7) 離開此共乘
@app.post("/leave-the-carpool", status_code=status.HTTP_200_OK)
def leave_the_carpool(eventIdAndUserId:EventIdAndUserId, db: Session = Depends(get_db)):
    event_id, user_id = eventIdAndUserId.event_id, eventIdAndUserId.user_id
    event = db.query(Event).filter_by(id = event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此Event")
    if event.end_time != None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event已結束")
    if str(user_id) not in event.joiner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此user不在event")
    if user_id == event.initiator:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此user為initiator")
    if (datetime.now() + timedelta(hours=1)) > event.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event即將開始無法退出")

    old_joiner = event.joiner
    old_joiner = old_joiner.split(',')
    user_position = old_joiner.index(str(user_id))
    new_joiner = old_joiner[:user_position] + old_joiner[user_position+1:]
    new_joiner = ','.join(new_joiner)
    event.joiner = new_joiner

    event.available_seats = event.available_seats + 1

    old_joiner_to_location = event.joiner_to_location
    old_joiner_to_location = old_joiner_to_location.split(',')
    new_joiner_to_location = old_joiner_to_location[:user_position] + old_joiner_to_location[user_position+1:]
    new_joiner_to_location = ','.join(new_joiner_to_location)
    event.joiner_to_location = new_joiner_to_location
    db.commit()

    # oncreate = create_payment(event, db) #create Payment instances for joiners and calculate payables respectively
    # if not oncreate:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment創建失敗")

    return {"result" : "success"}


# (10) 新增共乘, otherLocation use comma to split
# @app.get("/InitiateCarpoolEventUI/{userID}/{numberOfPeople}/{selfdriveOrNot}/{startLocation}/{endLocation}/{otherLocation}")
@app.post("/initiate-carpool-event", status_code=status.HTTP_200_OK)
def create_new_carpool(eventForm: CreateEventBase, db: Session = Depends(get_db)):
    # user_id, initiator, start_time, self_drive_or_not, number_of_people, start_location,
    user_id, start_time, self_drive_or_not, number_of_people, acc_payable = eventForm.user_id, eventForm.start_time, eventForm.self_drive_or_not, eventForm.number_of_people, eventForm.acc_payable
    
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
    
    total_loc_list = [eventForm.start_location] + eventForm.other_location + [eventForm.end_location]
    num_loc = len(total_loc_list)

    #assume no repeated location
    if len(list(dict.fromkeys(total_loc_list))) < len(total_loc_list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="地點不可重複")

    stops = ",".join(eventForm.other_location)
    wholeLocation = ',' + eventForm.start_location + ',' + stops + ',' + eventForm.end_location + ','
    addEvent = Event(initiator=user_id,
                    joiner=',' + str(user_id) + ',',
                    location=wholeLocation,
                    start_time=start_time,
                    is_self_drive=self_drive_or_not,
                    number_of_people=number_of_people,
                    available_seats=number_of_people-1,
                    accounts_payable=acc_payable,
                    joiner_to_location=f"0-{num_loc-1}",   #此attribute第一格為initiator之start, end地點
                )
    db.add(addEvent)
    db.commit()
    # return success or fail
    return {"event_id" : addEvent.id}

             
# User Page Info
@app.put("/update-user-info", status_code=status.HTTP_200_OK)
async def update_user(
    userinfoForm: UserView,
    db: Session = Depends(get_db)):

    user_id, password, phone, display_name, mail = (
        userinfoForm.user_id,
        userinfoForm.password,
        userinfoForm.phone,
        userinfoForm.display_name,
        userinfoForm.mail,
    )

    #check user_id
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")

    #hash the new password
    if password:
        salt = bcrypt.gensalt()
        password = bcrypt.hashpw(password.encode('utf8'), salt)

    #ensure no repeated phone, mail, d_name
    if display_name:
        same_name_user = db.query(User).filter_by(display_name=display_name).first()
        if same_name_user and same_name_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此使用者名稱已被使用")

    if phone:
        user_with_phone = db.query(User).filter_by(phone=phone).first()
        if user_with_phone and user_with_phone.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此手機號碼已被使用")

    if mail:
        user_with_mail = db.query(User).filter_by(mail=mail).first()
        if user_with_mail and user_with_mail.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此信箱已被使用")
        
    update_dict = {"password": password, 
                   "phone": phone, 
                   "display_name": display_name, 
                   "mail": mail,
                   }
    update_dict_notnull = {key: update_dict[key] for key in update_dict if update_dict[key] is not None}


    if update_dict_notnull:
        db.query(User).filter_by(id=user_id).update(update_dict_notnull)
        db.commit()

    return {"user_id": user_id}

@app.get("/get-user-info/{userid}", status_code=status.HTTP_200_OK)
async def get_user(
    userid: int,
    db: Session = Depends(get_db)):

    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")

    res = {"user_id": user.id, "phone": user.phone, "display_name": user.display_name, "mail": user.mail}
    return res

@app.post("/update-user-license", status_code=status.HTTP_200_OK)  #assume license_file != NULL
async def update_license(
        userid: int,
        license_file: Annotated[UploadFile, File()],
        db: Session = Depends(get_db),
    ):

    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")

    #Read and Save the license_file content
    save_path = ""

    if license_file.content_type not in ['image/jpeg', 'image/png']:
        raise HTTPException(status_code=406, detail="Please upload only .jpeg files")

    #generate random string as the file name
    random_source = string.ascii_letters + string.digits
    random_str = ''.join((random.choice(random_source) for i in range(10)))
    content_type = license_file.content_type.split('/')[1]
    random_license_name = ''.join((str(userid), "_", random_str, ".", content_type))  #file name = {userid}_{random_str}.{png/jpeg}


    save_path = os.path.join(Config.LICENSE_UPLOAD_PATH, random_license_name)
    with open(save_path, "wb") as file:
        file.write(license_file.file.read())

    db.query(User).filter_by(id=userid).update(dict(
        license=random_license_name
    ))
    db.commit()

    return {"license_file": userid}

@app.get("/get-user-license/{userid}", status_code=status.HTTP_200_OK)
async def get_license(
    userid: int,
    db: Session = Depends(get_db)):

    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")
    
    if not user.license:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此使用者未上傳駕照")
        
    license_path = os.path.join(Config.LICENSE_UPLOAD_PATH, user.license)
    return FileResponse(license_path, media_type='image',filename=user.license)

@app.delete("/delete-user-license/{userid}", status_code=status.HTTP_200_OK)
async def delete_license(
    userid: int,
    db: Session = Depends(get_db)):

    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")

    user.license = None
    db.commit()

    return {"user_id": userid}


# Payment
@app.put("/payment", status_code=status.HTTP_200_OK)
async def update_user_account(
    userid: int,
    eventid: int,
    db: Session = Depends(get_db)):

    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")
    
    #check event_id
    event = db.query(Event).filter_by(id=eventid).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此共乘事件")
    
    
    

    return {"total_paid": "test"}

@app.get("/payment/{userid}", status_code=status.HTTP_200_OK)
async def get_user_account(
    userid: int,
    db: Session = Depends(get_db)):

    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")
    
    res = {"user_id": user.id, "account": user.carpool_money}
    return res

@app.get("/payable/{userid}", status_code=status.HTTP_200_OK)
async def get_event_payable_info(
    userid: int,
    eventid: int,
    db: Session = Depends(get_db)):

    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")
    
    #check event_id
    event = db.query(Event).filter_by(id=eventid).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此共乘事件")
    
    payable = db.query(Payment).filter_by(user_id=userid, event_id=eventid).first()
    
    if not payable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此共乘尚未結束")
        
    res = {"user_id": userid, "event_id": eventid, "payable": payable.money, "isCompleted": payable.isCompleted}
    return res



@app.post("/linepay-request", status_code=status.HTTP_200_OK)
async def linepay_request_payment(
    userid: int,
    eventid: int,
    db: Session = Depends(get_db)):
    
    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")
    
    #check event_id
    event = db.query(Event).filter_by(id=eventid).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此共乘事件")
    
    #link to the LinePay API
    linepay_payload = create_order(user, event, db)
    
    async with AsyncClient() as client:
        response = await client.post(linepay_payload["url"], headers=linepay_payload["headers"], json=linepay_payload["body"])
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    print(response.__dict__)
    print("--------------------")
    
    # payment_url = response.json()["info"]["paymentUrl"]["web"]
    # transaction_id = response.json()["info"]["transactionId"]
    # db.query(Payment).filter_by(user_id=userid, event_id=eventid).update(dict(
    #     transaction_id=transaction_id
    # ))
    # db.commit()
    
    # return {"payment_url": payment_url}
    return 1


@app.post("/linepay-confirm", status_code=status.HTTP_200_OK)
async def linepay_confirm_payment(
    userid: int,
    eventid: int,
    db: Session = Depends(get_db)):
    
    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")
    
    #check event_id
    event = db.query(Event).filter_by(id=eventid).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此共乘事件")

    linepay_confirm = create_confirm(user, event, db)
    
    async with AsyncClient() as client:
        response = await client.post(linepay_confirm["url"], headers=linepay_confirm["headers"], json=linepay_confirm["body"])
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    db.query(Payment).filter_by(user_id=userid, event_id=eventid).update(dict(
        isCompleted=1
    ))
    db.commit()
    
    
    return 1
    
    
    
    
    
    


#notification
@app.post("/send-reward/{userid}", status_code=status.HTTP_200_OK)
async def send_reward_notification(
    userid: int, 
    db: Session = Depends(get_db)):
    
    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")
    
    #group name: "hello"
    payload = {
        "interests":["hello"],
        "web":{
            "notification":{
                "title":"通知",
                "body":"您有新獎勵!!!"
            }
        }
    }

    result = await send_push_notification(Config.PUSHER_INSTANCE_ID, Config.PUSHER_SECRET, payload)
    return {"result": result}

@app.post("/send-payable/{userid}", status_code=status.HTTP_200_OK)
async def send_payment_notification(
    userid: int, 
    db: Session = Depends(get_db)):
    
    #check user_id
    user = db.query(User).filter_by(id=userid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此使用者")
    
    #group name: "hello"
    payload = {
        "interests":["hello"],
        "web":{
            "notification":{
                "title":"繳款通知",
                "body":"您有未付清款項!!!"
            }
        }
    }

    result = await send_push_notification(Config.PUSHER_INSTANCE_ID, Config.PUSHER_SECRET, payload)
    return {"result": result}
    
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0",port=8080, reload=True)
    

