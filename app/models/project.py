from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── Modelos originais (sem alteração) ─────────────────────────────────────────

class ProjectBase(BaseModel):
    title: str
    description: str
    category: str
    required_value: float
    applied_value: float = 0.0
    start_date: datetime


class ProjectCreate(ProjectBase):
    pass


# ALTERAÇÃO: adicionado campo transactions
# O frontend lê json['transactions'] em Projeto.fromJson() para montar histórico
class ProjectDB(ProjectBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    progress: float = 0.0
    transactions: List[dict] = []    # ← NOVO: lista de aportes


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    required_value: Optional[float] = None
    applied_value: Optional[float] = None
    start_date: Optional[datetime] = None


# ── Modelos novos exigidos pelo frontend ───────────────────────────────────────

# Resposta de POST /projects/{id}/deposit
# Campos mapeados exatamente com DepositResponse.fromJson() no Flutter
class DepositResponse(BaseModel):
    project_id: str
    previous_value: float
    deposited: float
    new_value: float
    progress: float
    required_value: float


# Transação individual — GET /projects/{id}/transactions
# Mapeado com Transacao.fromJson() no Flutter
class TransactionDB(BaseModel):
    id: str
    project_id: str
    user_id: str
    amount: float
    note: Optional[str] = ""
    created_at: datetime