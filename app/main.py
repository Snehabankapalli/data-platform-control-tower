from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .models import ApiEnvelope, ApprovalRequest
from .services import ControlTowerService, NotFoundError, ValidationError


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

app = FastAPI(title="Data Platform Control Tower", version="1.0.0", docs_url="/api/docs", redoc_url=None)
service = ControlTowerService.demo()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:"
    )
    return response


def envelope(data: object | None = None, error: str | None = None) -> dict[str, object | None]:
    return {"success": error is None, "data": data, "error": error}


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = ", ".join(str(error["loc"][-1]) for error in exc.errors())
    return JSONResponse(status_code=422, content=envelope(error=f"Invalid request field: {fields}"))


@app.exception_handler(ValidationError)
async def domain_validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content=envelope(error=str(exc)))


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content=envelope(error=str(exc)))


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health", response_model=ApiEnvelope)
def health() -> dict[str, object | None]:
    return envelope({"status": "ok", "mode": "demo"})


@app.get("/api/dashboard", response_model=ApiEnvelope)
def dashboard() -> dict[str, object | None]:
    return envelope(service.get_dashboard())


@app.get("/api/pipelines", response_model=ApiEnvelope)
def pipelines(
    status: str | None = Query(default=None, max_length=20),
    query: str | None = Query(default=None, max_length=100),
) -> dict[str, object | None]:
    return envelope(service.list_pipelines(status=status, query=query))


@app.get("/api/incidents", response_model=ApiEnvelope)
def incidents() -> dict[str, object | None]:
    return envelope(service.list_incidents())


@app.post("/api/incidents/{incident_id}/approve", response_model=ApiEnvelope)
def approve_incident(incident_id: str, approval: ApprovalRequest) -> dict[str, object | None]:
    return envelope(service.approve_remediation(incident_id, approval.actor, datetime.now(UTC)))


@app.get("/api/costs/recommendations", response_model=ApiEnvelope)
def cost_recommendations() -> dict[str, object | None]:
    return envelope(service.list_cost_recommendations())


@app.get("/api/lineage", response_model=ApiEnvelope)
def lineage() -> dict[str, object | None]:
    return envelope(service.get_lineage())
