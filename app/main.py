from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.api.v1.router import api_router
# Importa do scheduler atualizado
from app.services.scheduler import start_scheduler, stop_scheduler, check_race_status_job 

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicia o agendador em background
    start_scheduler()
    
    print("--- 🚀 Executando verificação inicial de status (Boot) ---")
    try:
        # Roda uma verificação imediata para não esperar 1 minuto
        check_race_status_job()
    except Exception as e:
        print(f"Erro na verificação inicial: {e}")
        
    yield
    # Para o agendador ao desligar
    stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan 
)

# ... (Resto das configurações de CORS e StaticFiles iguais ao seu original) ...
origins = [
    "http://localhost:4200",
    "http://localhost:8080",
    settings.FRONTEND_URL,
]
origins = list(set(origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.getcwd()
uploads_dir = os.path.join(base_dir, "uploads")
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "API do Bolão F1 está rodando com Scheduler (Brasília) Ativo!"}