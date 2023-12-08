from model import User, Event, Payment
from fastapi import FastAPI, Depends, status, HTTPException
from sqlalchemy.orm.session import Session
from database import SessionLocal, engine
from config import Config
import uuid
import hmac, base64
import json
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
import hashlib
from datetime import datetime
import random

'''
<request payment: payload format>
{
    "amount" : 1,
    "currency" : "TWD",
    "orderId" : "TEST_2023_12",
    "packages" : [
        {
            "id" : "1",
            "amount": 100,
            "products" : [
                {
                    "id" : "PEN-B-001",
                    "name" : "Carpool Payable",
                    "imageUrl" : "https://pay-store.line.com/images/pen_brown.jpg",
                    "quantity" : 2,
                    "price" : 50
                }
            ]
        }
    ],
    "redirectUrls" : {
        "confirmUrl" : "https://pay-store.line.com/order/payment/authorize",
        "cancelUrl" : "https://pay-store.line.com/order/payment/cancel"
    }
}
'''

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_order(user: User, event: Event, payable: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter_by(user_id=user.id, event_id=event.id).first()
    req_uri = "payments/request"
    req_url = f"{Config.LINE_PAY_SITE}/{Config.LINE_PAY_VERSION}/{req_uri}"

    #check repeated order
    if payment.isCompleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此訂單先前已完成付款")
    order_id = generate_random_orderid() #unique order id
    
    order = {
        "amount" : payable,
        "currency" : "TWD",
        "orderId" : order_id,
        "packages" : [
            {
                "id" : "1",
                "amount": payable,
                "products" : [
                    {
                        "id" : payment.id,
                        "name" : "Carpool Payable",
                        # "imageUrl" : "https://pay-store.line.com/images/pen_brown.jpg",
                        "quantity" : 1,
                        "price" : payable
                    }
                ]
            }
        ],
        "redirectUrls" : {
            "confirmUrl" : f"http://localhost:3000/confirm?event_id={event.id}",
            "cancelUrl" : "https://4ff7-59-115-198-214.ngrok-free.app/loginstate/ended"
        }
    }
    
    headers = create_header(req_uri, order)
    return {"headers": headers, "body": order, "url": req_url, "order_id": order_id}

def create_confirm(user: User, event: Event, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter_by(user_id=user.id, event_id=event.id).first()
    if not payment.transaction_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此訂單尚未完成付款程序")

    req_uri = f"payments/{payment.transaction_id}/confirm"
    req_url = f"{Config.LINE_PAY_SITE}/{Config.LINE_PAY_VERSION}/{req_uri}"

    if payment.useCarpoolmoney:
        if payment.money > user.carpool_money:
            payable = payment.money - user.carpool_money
        else:
            payable = 0
    else:
        payable = payment.money
    
    body = {
        "amount": int(payable),
        "currency" : "TWD"
    }
    
    headers = create_header(req_uri, body)
    return {"headers": headers, "body": body, "url": req_url}

def create_header(uri: str, body: dict):
    nonce = uuid.uuid4().hex
    ChannelSecret = Config.LINE_PAY_SECRET
    req_uri = f"/{Config.LINE_PAY_VERSION}/{uri}"
    str_body = json.dumps(body)
    
    datawithsecret = f"{ChannelSecret}{req_uri}{str_body}{nonce}"
    signature = encrypt(ChannelSecret, datawithsecret)
    
    header = {
        "Content-Type": "application/json",
        "X-LINE-ChannelId": Config.LINE_PAY_CHANNELID,
        "X-LINE-Authorization-Nonce": nonce,
        "X-LINE-Authorization": signature,
    }
    
    return header
    
def encrypt(keys, data):
    hmac_obj = hmac.new(keys.encode('utf-8'), data.encode('utf-8'), 'sha256')
    return base64.b64encode(hmac_obj.digest()).decode('utf-8')

def generate_random_orderid(length=8):
    return ''.join([str(random.randint(0, 9)) for i in range(length)])
