from typing import Optional
from pydantic import BaseModel

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = "client"

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: Optional[str] = None
    email: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None
