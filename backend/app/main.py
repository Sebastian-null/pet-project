import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .admin import router as admin_router
from .api import router as api_router
from .config import Settings, settings
from .maintenance import sweep_periodically
from .payments import router as payments_router

if settings.environment == "production" and settings.jwt_secret == Settings.model_fields["jwt_secret"].default:
    raise RuntimeError("JWT_SECRET is still the development default — set a real secret before deploying")

@asynccontextmanager
async def lifespan(_: FastAPI):
    sweeper = asyncio.create_task(sweep_periodically())
    yield
    sweeper.cancel()

app = FastAPI(title="Briefs API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.storefront_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router); app.include_router(payments_router); app.include_router(admin_router)
Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
MAX_BODY_BYTES = 8 * 1024 * 1024

@app.middleware("http")
async def guard_and_harden(request: Request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "Request body is too large"}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

@app.exception_handler(StarletteHTTPException)
async def crm_sends_guests_to_the_login_page(request: Request, exception: StarletteHTTPException):
    if request.url.path.startswith("/admin"):
        if exception.status_code == 401:
            return RedirectResponse("/admin/login", status_code=303)
        if exception.status_code == 403:
            return HTMLResponse(f'<p style="font:15px system-ui;padding:28px">{exception.detail} — <a href="/admin">back to the CRM</a></p>', status_code=403)
    return await http_exception_handler(request, exception)

@app.get("/health")
def health(): return {"status": "ok"}
