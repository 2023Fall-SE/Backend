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

'''
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

def create_order(user: User, event: Event, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter_by(user_id=user.id, event_id=event.id).first()
    req_uri = "payments/request"
    req_url = f"{Config.LINE_PAY_SITE}/{Config.LINE_PAY_VERSION}/{req_uri}"
    
    order = {
        "amount" : 1,
        "currency" : "TWD",
        "orderId" : "TEST_2023_12",
        "packages" : [
            {
                "id" : "1",
                "amount": int(payment.money),
                "products" : [
                    {
                        "id" : payment.id,
                        "name" : "Carpool Payable",
                        # "imageUrl" : "https://pay-store.line.com/images/pen_brown.jpg",
                        "quantity" : 1,
                        "price" : int(payment.money)
                    }
                ]
            }
        ],
        "redirectUrls" : {
            "confirmUrl" : "https://pay-store.line.com/order/payment/authorize",
            "cancelUrl" : "https://pay-store.line.com/order/payment/cancel"
        }
    }
    
    headers = create_header(req_uri, order)
    return {"headers": headers, "body": order, "url": req_url}
    

def create_header(uri: str, body: dict):
    nonce = uuid.uuid4().hex
    ChannelSecret = Config.LINE_PAY_SECRET
    req_uri = f"/{Config.LINE_PAY_VERSION}/{uri}"
    # json_body = json.dumps(body.__dict__)
    # json_body = jsonable_encoder(body.dict)
    str_body = json.dumps(body)
    
    # print(type(json_body))
    
    datawithsecret = f"{ChannelSecret}{req_uri}{str_body}{nonce}"
    signature = encrypt(ChannelSecret, datawithsecret)
    
    # print("---------------")
    # print(signature1)
    # print("---------------")
    # print(signature2)
    
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
    
