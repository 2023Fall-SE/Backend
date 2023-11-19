from pydantic import BaseModel, validator, Field, confloat, constr
from typing import Optional

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=r"[A-Za-z0-9]", default=None)
    password: str = Field(min_length=8, pattern=r"[A-Za-z0-9]", default=None)
    display_name: str = Field(min_length=3, max_length=20, default=None)

class UserCreate(UserBase):
    phone: Optional[str] = Field(min_length=10, max_length=10, pattern=r"[0-9]", default=None)

