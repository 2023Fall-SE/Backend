from pydantic import BaseModel, validator, Field, confloat, constr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9]+$")
    password: str = Field(min_length=8, pattern=r"^[A-Za-z0-9@$!%*?&_.]+$")
    display_name: str = Field(min_length=3, max_length=20)


class UserCreate(UserBase):
    phone: Optional[str] = Field(min_length=10, max_length=10, pattern=r"[0-9]", default=None)


class CreateEventBase(BaseModel):
    user_id: int
    start_time : datetime
    self_drive_or_not : bool
    number_of_people : int = Field(ge=2, le=7)
    start_location : str
    end_location : str
    other_location : list[str]

class UserId(BaseModel):
    user_id : int
    
class EventId(BaseModel):
    event_id : int
    
class FindLocationForm(BaseModel):
    start_location:str
    end_location:str