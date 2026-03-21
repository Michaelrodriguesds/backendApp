from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from app.database import get_projects_collection, get_users_collection
from app.models.project import (
    ProjectCreate, ProjectDB, ProjectUpdate,
    DepositResponse, TransactionDB,          # ← NOVOS imports
)
from app.models.user import UserDB
from app.utils.security import get_current_user
from bson import ObjectId
from datetime import datetime
from typing import List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
    },
)


def calculate_progress(applied: float, required: float) -> float:
    """Idêntico ao original."""
    if required == 0:
        return 0.0
    return min(round((applied / required) * 100, 2), 100.0)


# ── POST /projects/ ─────────────────────────── ORIGINAL + inicializa transactions
@router.post("/", response_model=ProjectDB, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    current_user: UserDB = Depends(get_current_user),
):
    projects_collection = await get_projects_collection()
    users_collection    = await get_users_collection()

    project_dict = project.dict()
    project_dict.update({
        "user_id":      current_user.id,
        "created_at":   datetime.utcnow(),
        "updated_at":   datetime.utcnow(),
        "progress":     calculate_progress(project.applied_value, project.required_value),
        "transactions": [],    # ← NOVO campo: lista vazia ao criar
    })

    result = await projects_collection.insert_one(project_dict)
    project_dict["id"] = str(result.inserted_id)

    # Atualiza contador de projetos do usuário
    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$inc": {"projects_count": 1}}
    )

    return ProjectDB(**project_dict)


# ── GET /projects/ ────────────────────── ORIGINAL + retrocompatibilidade transactions
@router.get("/", response_model=List[ProjectDB])
async def list_user_projects(current_user: UserDB = Depends(get_current_user)):
    projects_collection = await get_projects_collection()
    projects = []
    async for project in projects_collection.find({"user_id": current_user.id}):
        project["id"] = str(project["_id"])
        if "transactions" not in project:
            project["transactions"] = []    # projetos antigos sem o campo
        projects.append(ProjectDB(**project))
    return projects


# ── GET /projects/{project_id} ───────── ORIGINAL + retrocompatibilidade transactions
@router.get("/{project_id}", response_model=ProjectDB)
async def get_project(
    project_id: str,
    current_user: UserDB = Depends(get_current_user)
):
    projects_collection = await get_projects_collection()
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID do projeto inválido")

    project = await projects_collection.find_one({
        "_id": obj_id,
        "user_id": current_user.id
    })
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project["id"] = str(project["_id"])
    if "transactions" not in project:
        project["transactions"] = []
    return ProjectDB(**project)


# ── PUT /projects/{project_id} ──────────────────────────────────── ORIGINAL
@router.put("/{project_id}", response_model=ProjectDB)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: UserDB = Depends(get_current_user),
):
    projects_collection = await get_projects_collection()
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID do projeto inválido")

    update_data = project_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    existing_project = await projects_collection.find_one({
        "_id": obj_id,
        "user_id": current_user.id
    })
    if not existing_project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    applied  = update_data.get("applied_value",  existing_project.get("applied_value",  0.0))
    required = update_data.get("required_value", existing_project.get("required_value", 0.0))
    update_data["progress"] = calculate_progress(applied, required)

    result = await projects_collection.update_one(
        {"_id": obj_id, "user_id": current_user.id},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Projeto não encontrado ou sem alterações")

    updated_project = await projects_collection.find_one({"_id": obj_id})
    updated_project["id"] = str(updated_project["_id"])
    if "transactions" not in updated_project:
        updated_project["transactions"] = []
    return ProjectDB(**updated_project)


# ── DELETE /projects/{project_id} ───────────────────────────────── ORIGINAL
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: UserDB = Depends(get_current_user)
):
    projects_collection = await get_projects_collection()
    users_collection    = await get_users_collection()

    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID do projeto inválido")

    project = await projects_collection.find_one({
        "_id": obj_id,
        "user_id": current_user.id
    })
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    await projects_collection.delete_one({"_id": obj_id})

    # Atualiza contador de projetos do usuário
    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$inc": {"projects_count": -1}}
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS NOVOS — exigidos pelo frontend Flutter
# ══════════════════════════════════════════════════════════════════════════════

class DepositBody(BaseModel):
    amount: float
    note: str = ""


# ── POST /projects/{project_id}/deposit ──────────────────────────────── NOVO
# Chamado por ProjetoService.depositar() no Flutter
# Recebe apenas o valor do APORTE — nunca o total
# Backend soma ao applied_value, salva transação, atualiza total_invested do usuário
@router.post("/{project_id}/deposit", response_model=DepositResponse)
async def deposit(
    project_id: str,
    body: DepositBody,
    current_user: UserDB = Depends(get_current_user),
):
    if body.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor do aporte deve ser maior que zero"
        )

    projects_collection = await get_projects_collection()
    users_collection    = await get_users_collection()

    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    project = await projects_collection.find_one({
        "_id": obj_id,
        "user_id": current_user.id
    })
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    previous  = project.get("applied_value", 0.0)
    required  = project.get("required_value", 0.0)
    new_value = round(previous + body.amount, 2)
    progress  = calculate_progress(new_value, required)

    # Registro da transação embutido no documento do projeto
    transaction = {
        "id":         str(ObjectId()),
        "amount":     body.amount,
        "note":       body.note,
        "created_at": datetime.utcnow(),
    }

    await projects_collection.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "applied_value": new_value,
                "progress":      progress,
                "updated_at":    datetime.utcnow(),
            },
            "$push": {"transactions": transaction},
        },
    )

    # Incrementa total_invested do usuário
    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$inc": {"total_invested": body.amount}}
    )

    return DepositResponse(
        project_id=    project_id,
        previous_value=previous,
        deposited=     body.amount,
        new_value=     new_value,
        progress=      progress,
        required_value=required,
    )


# ── GET /projects/{project_id}/transactions ───────────────────────────── NOVO
# Chamado por TransacaoService.listar() no Flutter
# Retorna histórico de aportes do projeto
@router.get("/{project_id}/transactions", response_model=List[TransactionDB])
async def list_transactions(
    project_id: str,
    current_user: UserDB = Depends(get_current_user),
):
    projects_collection = await get_projects_collection()

    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    project = await projects_collection.find_one({
        "_id": obj_id,
        "user_id": current_user.id
    })
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    return [
        TransactionDB(
            id=         t.get("id", str(ObjectId())),
            project_id= project_id,
            user_id=    current_user.id,
            amount=     t["amount"],
            note=       t.get("note", ""),
            created_at= t["created_at"],
        )
        for t in project.get("transactions", [])
    ]