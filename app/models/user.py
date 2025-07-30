from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Modelo para criação de usuário (entrada via POST)
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    theme: Optional[str] = "light"  # Tema padrão

# Modelo retornado após criação/leitura do usuário
class UserDB(BaseModel):
    id: str  # ID do MongoDB convertido para string
    email: EmailStr
    name: str
    theme: Optional[str]
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    disabled: bool
    projects_count: int
    total_invested: float
    is_admin: bool

# Modelo interno usado no banco de dados (sem ID externo)
class UserInDB(BaseModel):
    email: EmailStr
    name: str
    theme: Optional[str]
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    disabled: bool
    projects_count: int
    total_invested: float
    is_admin: bool

# Modelo para atualizar dados parcialmente
class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    theme: Optional[str] = None

# Modelo com dados extraídos do token JWT
class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None

# ✅ Modelo de resposta do token JWT
class Token(BaseModel):
    access_token: str
    token_type: str
