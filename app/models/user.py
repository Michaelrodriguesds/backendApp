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
class UserDB(BaseModel):
    id: str
    name: str
    email: EmailStr
    theme: Optional[str]
    hashed_password: Optional[str]
    created_at: datetime
    updated_at: datetime
    disabled: bool
    projects_count: int
    total_invested: float
    is_admin: bool

    class Config:
        orm_mode = True

# Modelo usado internamente no banco
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
    user: TokenUser  # ✅ Incluído o usuário na resposta do login
