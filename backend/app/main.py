from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as api_router
from .admin import router as admin_router

app = FastAPI(title="Briefs API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router); app.include_router(admin_router)
@app.get("/health")
def health(): return {"status": "ok"}
