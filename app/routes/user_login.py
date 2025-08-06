from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.database import get_users_collection
from app.models.user import Token, TokenUser  # Incluímos o modelo TokenUser
from app.utils.security import verify_password, create_access_token
from bson import ObjectId

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    users_collection = await get_users_collection()

    # Busca o usuário no banco pelo email (form_data.username)
    user = await users_collection.find_one({"email": form_data.username})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Cria o token JWT com o ID do usuário como subject (sub)
    access_token = create_access_token(data={"sub": str(user["_id"])})

    # Prepara dados do usuário (sem expor hashed_password)
    user_response = {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "theme": user.get("theme"),
        "disabled": user.get("disabled", False),
        "projects_count": user.get("projects_count", 0),
        "total_invested": user.get("total_invested", 0.0),
        "is_admin": user.get("is_admin", False)
    }

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response  # Retorna também os dados do usuário autenticado
    }
