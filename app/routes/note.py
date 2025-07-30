from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from bson import ObjectId

from app.database import get_notes_collection
from app.models.note import NoteCreate, NoteDB, NoteUpdate
from app.models.user import UserDB
from app.utils.security import get_current_user

router = APIRouter(
    prefix="/notes",
    tags=["Notes"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"}
    },
)

@router.post("/", response_model=NoteDB, status_code=status.HTTP_201_CREATED)
async def create_note(
    note: NoteCreate,
    project_id: Optional[str] = None,
    current_user: UserDB = Depends(get_current_user)
):
    notes_collection = await get_notes_collection()
    note_dict = note.dict()
    note_dict.update({
        "user_id": current_user.id,
        "project_id": project_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    result = await notes_collection.insert_one(note_dict)
    note_dict["id"] = str(result.inserted_id)
    return NoteDB(**note_dict)

@router.get("/", response_model=List[NoteDB])
async def list_notes(
    project_id: Optional[str] = None,
    current_user: UserDB = Depends(get_current_user)
):
    notes_collection = await get_notes_collection()
    query = {"user_id": current_user.id}
    if project_id:
        query["project_id"] = project_id

    notes: List[NoteDB] = []
    async for note in notes_collection.find(query):
        note["id"] = str(note["_id"])
        notes.append(NoteDB(**note))
    return notes

@router.get("/{note_id}", response_model=NoteDB)
async def get_note(
    note_id: str,
    current_user: UserDB = Depends(get_current_user)
):
    notes_collection = await get_notes_collection()
    note = await notes_collection.find_one({
        "_id": ObjectId(note_id),
        "user_id": current_user.id
    })
    if not note:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    note["id"] = str(note["_id"])
    return NoteDB(**note)

@router.put("/{note_id}", response_model=NoteDB)
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    current_user: UserDB = Depends(get_current_user)
):
    notes_collection = await get_notes_collection()
    update_data = note_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    result = await notes_collection.update_one(
        {"_id": ObjectId(note_id), "user_id": current_user.id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    updated_note = await notes_collection.find_one({"_id": ObjectId(note_id)})
    updated_note["id"] = str(updated_note["_id"])
    return NoteDB(**updated_note)

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: UserDB = Depends(get_current_user)
):
    notes_collection = await get_notes_collection()
    note = await notes_collection.find_one({
        "_id": ObjectId(note_id),
        "user_id": current_user.id
    })

    if not note:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    await notes_collection.delete_one({"_id": ObjectId(note_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
