import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Instância principal do FastAPI
app = FastAPI(
    title="Financeiro API",
    version="1.0.0",
    description="API for personal financial management",
    docs_url="/docs",     # Documentação Swagger
    redoc_url="/redoc"    # Documentação alternativa Redoc
)

# Middleware CORS para permitir requisições de outros domínios (ex: Flutter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Em produção, restrinja isso ao domínio do app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialização do banco de dados ao iniciar a aplicação
@app.on_event("startup")
async def startup_event() -> None:
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise

# Importação das rotas
from app.routes import (
    project,
    note,
    user_login,
    user_register
)

# Inclusão dos routers
app.include_router(user_login.router, prefix="/api", tags=["Authentication"])  # POST /api/auth/login
app.include_router(user_register.router, prefix="/api", tags=["Users"])        # GET/POST /api/users/...
app.include_router(project.router, prefix="/api", tags=["Projects"])           # /api/projects/...
app.include_router(note.router, prefix="/api", tags=["Notes"])                 # /api/notes/...

# Rota raiz de boas-vindas
@app.get("/", tags=["Root"])
async def root() -> dict:
    return {"message": "Welcome to Finance API"}

# Rota para health check (útil para monitoramento)
@app.get("/health", tags=["Health Check"])
async def health_check() -> dict:
    try:
        db = await init_db()
        await db.client.admin.command("ping")
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
