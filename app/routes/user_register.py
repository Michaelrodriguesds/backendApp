from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from app.models.user import UserCreate, UserDB
from app.database import get_users_collection
from app.utils.security import get_password_hash
from datetime import datetime
import logging

router = APIRouter(
    prefix="/users",
    tags=["User Registration"]
)

logger = logging.getLogger(__name__)

# Rota para registrar novo usuário
@router.post("/register", response_model=UserDB, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    users_collection = await get_users_collection()

    # Verifica se já existe usuário com o mesmo e-mail
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Criptografa a senha
    hashed_password = get_password_hash(user.password)

    # Monta os dados para o MongoDB
    user_data = {
        "name": user.name,
        "email": user.email,
        "hashed_password": hashed_password,
        "theme": user.theme or "light",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "disabled": False,
        "projects_count": 0,
        "total_invested": 0.0,
        "is_admin": False
    }

    # Insere no banco
    result = await users_collection.insert_one(user_data)
    created_user = await users_collection.find_one({"_id": result.inserted_id})

    # Remove campos sensíveis antes de retornar
    created_user["id"] = str(created_user["_id"])
    del created_user["_id"]
    del created_user["hashed_password"]  # 🔐 Segurança

    return UserDB(**created_user)


# Rota para buscar um usuário pelo ID
@router.get("/{user_id}", response_model=UserDB)
async def get_user_by_id(user_id: str):
    users_collection = await get_users_collection()

    # Valida o ID do MongoDB
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Remove campos desnecessários/sensíveis antes de retornar
    user["id"] = str(user["_id"])
    del user["_id"]
    if "hashed_password" in user:
        del user["hashed_password"]  # 🔐 Segurança

    return UserDB(**user)
