from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# Base para criação e retorno de notas
class NoteBase(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None               # Data associada à anotação (registro)
    reminder_at: Optional[datetime] = None        # ✅ Novo campo: lembrete agendado (opcional)

# Modelo para criação de nota (herda todos os campos de NoteBase)
class NoteCreate(NoteBase):
    pass

# Modelo para leitura (resposta ao cliente)
class NoteDB(NoteBase):
    id: str
    user_id: str
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Modelo para atualização parcial (todos os campos opcionais)
class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None       # ✅ Campo incluído no update
