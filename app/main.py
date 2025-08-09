import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
import os

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configurações baseadas no ambiente (desenvolvimento ou produção)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # Padrão: desenvolvimento
IS_PRODUCTION = ENVIRONMENT == "production"

# Configurações do CORS baseadas no ambiente
ALLOWED_ORIGINS = [
    "*"  # Permite tudo em desenvolvimento
] if not IS_PRODUCTION else [
    "https://seu-frontend.com",  # Substitua pelo domínio do seu frontend em produção
    "https://www.seu-frontend.com"
]

# Instância principal do FastAPI com configurações condicionais
app = FastAPI(
    title="Financeiro API",
    version="1.0.0",
    description="API for personal financial management",
    docs_url="/docs" if not IS_PRODUCTION else None,  # Desativa docs em produção
    redoc_url="/redoc" if not IS_PRODUCTION else None  # Desativa redoc em produção
)

# Middleware CORS com configurações seguras para produção
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Métodos explícitos
    allow_headers=["Authorization", "Content-Type"],  # Headers explícitos
)

# Inicialização do banco de dados ao iniciar a aplicação
@app.on_event("startup")
async def startup_event() -> None:
    try:
        await init_db()
        logger.info(f"✅ Database initialized successfully in {ENVIRONMENT} environment")
        
        # Log adicional para ajudar no debug
        db_url = os.getenv("DATABASE_URL", "local database")
        logger.info(f"🔗 Database connection: {db_url[:15]}...")  # Log parcial da URL por segurança
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise

# Importação das rotas (mantido após startup para evitar import circular)
from app.routes import (
    project,
    note,
    user_login,
    user_register
)

# Inclusão dos routers com prefixo condicional se necessário
API_PREFIX = "/api" if not IS_PRODUCTION else ""  # Pode remover o prefixo em produção se necessário

app.include_router(user_login.router, prefix=API_PREFIX, tags=["Authentication"])
app.include_router(user_register.router, prefix=API_PREFIX, tags=["Users"])
app.include_router(project.router, prefix=API_PREFIX, tags=["Projects"])
app.include_router(note.router, prefix=API_PREFIX, tags=["Notes"])

# Rota raiz de boas-vindas com informações do ambiente
@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "message": "Welcome to Finance API",
        "environment": ENVIRONMENT,
        "status": "running",
        "time": datetime.utcnow().isoformat()
    }

# Rota para health check aprimorada
@app.get("/health", tags=["Health Check"])
async def health_check() -> dict:
    try:
        db = await init_db()
        await db.client.admin.command("ping")
        return {
            "status": "healthy",
            "environment": ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "environment": ENVIRONMENT,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Configuração para o Render (opcional)
if __name__ == "__main__":
    import uvicorn
    
    # Configurações diferentes para local vs produção
    if IS_PRODUCTION:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            workers=int(os.getenv("WEB_CONCURRENCY", 2)),
            log_level="info"
        )
    else:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,  # Auto-reload apenas em desenvolvimento
            log_level="debug"
        )