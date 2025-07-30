from fastapi import APIRouter, HTTPException, status
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

@router.post("/register", response_model=UserDB, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    users_collection = await get_users_collection()

    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user.password)
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

    result = await users_collection.insert_one(user_data)
    created_user = await users_collection.find_one({"_id": result.inserted_id})

    created_user["id"] = str(created_user["_id"])
    del created_user["_id"]

    return UserDB(**created_user)
