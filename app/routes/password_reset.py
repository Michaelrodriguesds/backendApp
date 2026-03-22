"""
Rotas de recuperação de senha via código de 6 dígitos por e-mail.

Fluxo:
  1. POST /auth/forgot-password   → recebe email, gera código, envia e-mail
  2. POST /auth/verify-code       → valida código (sem redefinir ainda)
  3. POST /auth/reset-password    → recebe código + nova senha, redefine

Segurança:
  - Código de 6 dígitos gerado com secrets.randbelow (não random)
  - Expiração de 15 minutos salva no MongoDB
  - Tentativas erradas incrementadas (máx 5 — bloqueia por segurança)
  - Hash do código salvo no banco (nunca o código em claro)
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.database import get_users_collection
from app.utils.email_service import send_email, build_reset_email
from app.utils.security import get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Password Reset"])

_CODE_EXPIRY_MINUTES = 15
_MAX_ATTEMPTS        = 5


def _generate_code() -> str:
    """Gera código de 6 dígitos criptograficamente seguro."""
    return str(secrets.randbelow(900000) + 100000)  # 100000–999999


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


# ── POST /auth/forgot-password ────────────────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(body: ForgotPasswordRequest):
    """
    Gera código de 6 dígitos e envia por e-mail.
    Retorna 200 mesmo se o e-mail não existir (evita enumeração de usuários).
    """
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"email": body.email})

    # Resposta genérica para não vazar se e-mail existe
    generic_ok = {"message": "Se o e-mail estiver cadastrado, você receberá o código em breve."}

    if not user:
        return generic_ok

    nome  = user.get("name", "Usuário")
    code  = _generate_code()
    expiry = datetime.utcnow() + timedelta(minutes=_CODE_EXPIRY_MINUTES)

    # Salva hash do código + expiração no documento do usuário
    await users_collection.update_one(
        {"email": body.email},
        {
            "$set": {
                "reset_code_hash":    _hash_code(code),
                "reset_code_expiry":  expiry,
                "reset_code_attempts": 0,
            }
        },
    )

    # Envia e-mail em background (não bloqueia a resposta)
    try:
        html = build_reset_email(nome, code)
        await send_email(body.email, "Código para redefinir sua senha — Financeiro App", html)
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail de recuperação para {body.email}: {e}")
        # Limpa código se e-mail falhou para não deixar lixo no banco
        await users_collection.update_one(
            {"email": body.email},
            {"$unset": {"reset_code_hash": "", "reset_code_expiry": "", "reset_code_attempts": ""}}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao enviar e-mail. Verifique as configurações de SMTP no servidor."
        )

    return generic_ok


# ── POST /auth/verify-code ────────────────────────────────────────────────────
class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


@router.post("/verify-code", status_code=status.HTTP_200_OK)
async def verify_code(body: VerifyCodeRequest):
    """
    Valida se o código está correto e não expirou.
    Chamado antes de mostrar o campo de nova senha (UX mais suave).
    """
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"email": body.email})

    if not user or "reset_code_hash" not in user:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    # Verifica tentativas
    attempts = user.get("reset_code_attempts", 0)
    if attempts >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas incorretas. Solicite um novo código."
        )

    # Verifica expiração
    expiry = user.get("reset_code_expiry")
    if not expiry or datetime.utcnow() > expiry:
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo.")

    # Verifica código
    if _hash_code(body.code.strip()) != user["reset_code_hash"]:
        await users_collection.update_one(
            {"email": body.email},
            {"$inc": {"reset_code_attempts": 1}}
        )
        remaining = _MAX_ATTEMPTS - attempts - 1
        raise HTTPException(
            status_code=400,
            detail=f"Código incorreto. {remaining} tentativa(s) restante(s)."
        )

    return {"message": "Código válido.", "valid": True}


# ── POST /auth/reset-password ─────────────────────────────────────────────────
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(body: ResetPasswordRequest):
    """
    Valida código e redefine a senha.
    Após sucesso, remove o código do banco (uso único).
    """
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter no mínimo 6 caracteres.")

    users_collection = await get_users_collection()
    user = await users_collection.find_one({"email": body.email})

    if not user or "reset_code_hash" not in user:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    attempts = user.get("reset_code_attempts", 0)
    if attempts >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Solicite um novo código."
        )

    expiry = user.get("reset_code_expiry")
    if not expiry or datetime.utcnow() > expiry:
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo.")

    if _hash_code(body.code.strip()) != user["reset_code_hash"]:
        await users_collection.update_one(
            {"email": body.email},
            {"$inc": {"reset_code_attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Código incorreto.")

    # Atualiza senha e limpa campos de reset
    new_hash = get_password_hash(body.new_password)
    await users_collection.update_one(
        {"email": body.email},
        {
            "$set":   {"hashed_password": new_hash, "updated_at": datetime.utcnow()},
            "$unset": {
                "reset_code_hash":     "",
                "reset_code_expiry":   "",
                "reset_code_attempts": "",
            },
        },
    )

    logger.info(f"✅ Senha redefinida para: {body.email}")
    return {"message": "Senha redefinida com sucesso!"}