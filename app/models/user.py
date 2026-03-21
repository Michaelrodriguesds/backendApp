from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# Modelo para criação de usuário via /register
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    theme: Optional[str] = "light"


# Modelo de retorno ao buscar ou criar usuário
# ALTERAÇÃO: hashed_password REMOVIDO — nunca deve ser exposto na resposta
# Antes era Optional[str] e ia parar na resposta do /register e /users/{id}
class UserDB(BaseModel):
    id: str
    name: str
    email: EmailStr
    theme: Optional[str] = "light"
    created_at: datetime
    updated_at: datetime
    disabled: bool = False
    projects_count: int = 0
    total_invested: float = 0.0
    is_admin: bool = False

    class Config:
        orm_mode = True          # Pydantic v1
        from_attributes = True   # Pydantic v2


# Modelo usado internamente no banco (com hash — nunca retornado ao cliente)
class UserInDB(BaseModel):
    name: str
    email: EmailStr
    hashed_password: str
    theme: Optional[str] = "light"
    created_at: datetime
    updated_at: datetime
    disabled: bool = False
    projects_count: int = 0
    total_invested: float = 0.0
    is_admin: bool = False


# Modelo para atualizações parciais
class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    theme: Optional[str] = None


# Dados extraídos do token JWT
class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None


# Modelo simplificado para retornar dados do usuário no login
class TokenUser(BaseModel):
    id: str
    email: EmailStr
    name: str
    theme: Optional[str] = None
    disabled: Optional[bool] = None
    projects_count: Optional[int] = 0
    total_invested: Optional[float] = 0.0
    is_admin: Optional[bool] = False


# Modelo de resposta da autenticação JWT
class Token(BaseModel):
    access_token: str
    token_type: str
    user: TokenUser