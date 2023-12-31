from pydantic import BaseModel, validator, Field, confloat, constr
from typing import Optional
from datetime import datetime
from fastapi import UploadFile

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9]+$")
    password: str = Field(min_length=8, pattern=r"^[A-Za-z0-9@$!%*?&_.]+$")
    display_name: str = Field(min_length=3, max_length=20)

class UserCreate(UserBase):
    phone: Optional[str] = Field(None, max_length=10, pattern=r"^[0-9]*$")
    mail: Optional[str] = Field(None, max_length=100, pattern=r"^(?:[a-zA-Z0-9]+@[a-zA-Z0-9]+\.[a-zA-Z]{2,3})?$",examples=["abcde1234@gmail.com"])

class CreateEventBase(BaseModel):
    user_id: int
    start_time : datetime
    self_drive_or_not : bool
    number_of_people : int = Field(ge=2, le=7)
    start_location : str
    end_location : str
    other_location : list[str]  
    acc_payable: confloat(ge=1, le=1000) = Field(default=100)

class UserId(BaseModel):
    user_id : int

class EventJoin(BaseModel):
    event_id : int
    user_id: int
    start_loc: str
    end_loc: str

class EventId(BaseModel):
    event_id: int

class EventIdAndUserId(BaseModel):
    event_id: int
    user_id: int

class FindLocationForm(BaseModel):
    start_location:str
    end_location:str

class UserView(BaseModel):
    user_id: int
    password: Optional[str] = Field(None, min_length=8, pattern=r"^[A-Za-z0-9@$!%*?&_.]+$")
    display_name: Optional[str] = Field(None, min_length=0, max_length=20)
    phone: Optional[str] = Field(None, max_length=10, pattern=r"^[0-9]*$")
    mail: Optional[str] = Field(None, max_length=100, pattern=r"^(?:[a-zA-Z0-9]+@[a-zA-Z0-9]+\.[a-zA-Z]{2,3})?$",examples=["abcde1234@gmail.com"])

class UserLicense(BaseModel):
    name: str
    image: UploadFile

class LinePayPayload(BaseModel):
    userid: int
    eventid: int
    payable: int


class messageForm(BaseModel):
    event_id : int
    sender_id : int
    time : datetime
    content : str