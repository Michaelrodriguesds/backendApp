from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from app.database import get_projects_collection, get_users_collection
from app.models.project import ProjectCreate, ProjectDB, ProjectUpdate
from app.models.user import UserDB
from app.utils.security import get_current_user
from bson import ObjectId
from datetime import datetime
from typing import List

router = APIRouter(
    prefix="/projects",  # Ajustado para melhor organização
    tags=["Projects"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
    },
)

def calculate_progress(applied: float, required: float) -> float:
    if required == 0:
        return 0.0
    return min(round((applied / required) * 100, 2), 100.0)

@router.post("/", response_model=ProjectDB, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    current_user: UserDB = Depends(get_current_user),
):
    projects_collection = await get_projects_collection()
    users_collection = await get_users_collection()

    project_dict = project.dict()
    project_dict.update({
        "user_id": current_user.id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "progress": calculate_progress(project.applied_value, project.required_value),
    })

    result = await projects_collection.insert_one(project_dict)
    project_dict["id"] = str(result.inserted_id)

    # Atualiza contador de projetos do usuário
    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$inc": {"projects_count": 1}}
    )

    return ProjectDB(**project_dict)

@router.get("/", response_model=List[ProjectDB])
async def list_user_projects(current_user: UserDB = Depends(get_current_user)):
    projects_collection = await get_projects_collection()
    projects = []
    async for project in projects_collection.find({"user_id": current_user.id}):
        project["id"] = str(project["_id"])
        projects.append(ProjectDB(**project))
    return projects

@router.get("/{project_id}", response_model=ProjectDB)
async def get_project(project_id: str, current_user: UserDB = Depends(get_current_user)):
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
    return ProjectDB(**project)

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

    applied = update_data.get("applied_value", existing_project.get("applied_value", 0.0))
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
    return ProjectDB(**updated_project)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, current_user: UserDB = Depends(get_current_user)):
    projects_collection = await get_projects_collection()
    users_collection = await get_users_collection()

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
