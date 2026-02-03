import os
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.auth import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from src.api.core.settings import get_settings
from src.api.core.storage import JsonStore
from src.api.models import (
    AuthResponse,
    EventCreate,
    EventOut,
    EventUpdate,
    LoginRequest,
    SignupRequest,
)

openapi_tags = [
    {"name": "Health", "description": "Service health endpoints."},
    {"name": "Auth", "description": "User authentication endpoints."},
    {"name": "Events", "description": "CRUD for calendar events."},
    {"name": "Views", "description": "Calendar views (day/week/month) for events."},
]

settings = get_settings()
users_store = JsonStore(os.path.join(settings.data_dir, "users.json"))
events_store = JsonStore(os.path.join(settings.data_dir, "events.json"))

app = FastAPI(
    title="Unified Calendar Scheduler API",
    description="Backend API for a calendar app with authentication, event CRUD, and calendar views.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_user_by_email(email: str) -> dict | None:
    data = users_store.read_all()
    for u in data.get("items", []):
        if u["email"].lower() == email.lower():
            return u
    return None


def _get_user_by_id(user_id: str) -> dict | None:
    data = users_store.read_all()
    for u in data.get("items", []):
        if u["id"] == user_id:
            return u
    return None


def _persist_user(user: dict) -> None:
    data = users_store.read_all()
    items = data.get("items", [])
    items.append(user)
    data["items"] = items
    users_store.write_all(data)


def _list_events_for_user(user_id: str) -> list[dict]:
    data = events_store.read_all()
    return [e for e in data.get("items", []) if e["user_id"] == user_id]


def _save_events(all_events: list[dict]) -> None:
    data = events_store.read_all()
    data["items"] = all_events
    events_store.write_all(data)


def _event_dict_to_out(e: dict) -> EventOut:
    return EventOut(
        id=e["id"],
        user_id=e["user_id"],
        title=e["title"],
        description=e.get("description"),
        start=datetime.fromisoformat(e["start"]),
        end=datetime.fromisoformat(e["end"]),
        all_day=bool(e.get("all_day", False)),
        reminder_minutes_before=e.get("reminder_minutes_before"),
        created_at=datetime.fromisoformat(e["created_at"]),
        updated_at=datetime.fromisoformat(e["updated_at"]),
    )


@app.get("/", tags=["Health"], summary="Health check", operation_id="health_check")
def health_check():
    """Health check endpoint.

    Returns:
        JSON message indicating service is up.
    """
    return {"message": "Healthy"}


@app.post(
    "/auth/signup",
    response_model=AuthResponse,
    tags=["Auth"],
    summary="Create user account",
    operation_id="auth_signup",
)
def signup(payload: SignupRequest):
    """Register a new user and return an access token."""
    existing = _get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": user_id,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "created_at": now,
    }
    _persist_user(user)
    token = create_access_token(user_id, settings.access_token_exp_minutes)
    return AuthResponse(access_token=token)


@app.post(
    "/auth/login",
    response_model=AuthResponse,
    tags=["Auth"],
    summary="Login",
    operation_id="auth_login",
)
def login(payload: LoginRequest):
    """Authenticate a user and return an access token."""
    user = _get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user["id"], settings.access_token_exp_minutes)
    return AuthResponse(access_token=token)


@app.get(
    "/auth/me",
    tags=["Auth"],
    summary="Get current user",
    operation_id="auth_me",
)
def me(user_id: str = Depends(get_current_user_id)):
    """Return current authenticated user basic info."""
    user = _get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return {"id": user["id"], "email": user["email"]}


@app.post(
    "/events",
    response_model=EventOut,
    tags=["Events"],
    summary="Create event",
    operation_id="create_event",
)
def create_event(payload: EventCreate, user_id: str = Depends(get_current_user_id)):
    """Create a new event for the authenticated user."""
    if payload.end < payload.start:
        raise HTTPException(status_code=400, detail="end must be after start")

    now = datetime.now(timezone.utc)
    event_id = str(uuid.uuid4())
    event = {
        "id": event_id,
        "user_id": user_id,
        "title": payload.title,
        "description": payload.description,
        "start": payload.start.isoformat(),
        "end": payload.end.isoformat(),
        "all_day": payload.all_day,
        "reminder_minutes_before": payload.reminder_minutes_before,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    data = events_store.read_all()
    items = data.get("items", [])
    items.append(event)
    data["items"] = items
    events_store.write_all(data)

    return _event_dict_to_out(event)


@app.get(
    "/events",
    response_model=list[EventOut],
    tags=["Events"],
    summary="List events",
    operation_id="list_events",
)
def list_events(user_id: str = Depends(get_current_user_id)):
    """List all events for the authenticated user."""
    events = _list_events_for_user(user_id)
    return [_event_dict_to_out(e) for e in events]


@app.get(
    "/events/{event_id}",
    response_model=EventOut,
    tags=["Events"],
    summary="Get event",
    operation_id="get_event",
)
def get_event(event_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a single event by id (must belong to current user)."""
    events = _list_events_for_user(user_id)
    for e in events:
        if e["id"] == event_id:
            return _event_dict_to_out(e)
    raise HTTPException(status_code=404, detail="Event not found")


@app.put(
    "/events/{event_id}",
    response_model=EventOut,
    tags=["Events"],
    summary="Update event",
    operation_id="update_event",
)
def update_event(event_id: str, payload: EventUpdate, user_id: str = Depends(get_current_user_id)):
    """Update an event by id (must belong to current user)."""
    data = events_store.read_all()
    items = data.get("items", [])
    updated = None
    now = datetime.now(timezone.utc).isoformat()

    for idx, e in enumerate(items):
        if e["id"] == event_id and e["user_id"] == user_id:
            # Merge fields
            merged = dict(e)
            for k, v in payload.model_dump(exclude_unset=True).items():
                if k in ("start", "end") and v is not None:
                    merged[k] = v.isoformat()
                else:
                    merged[k] = v
            # Validate time
            start_dt = datetime.fromisoformat(merged["start"])
            end_dt = datetime.fromisoformat(merged["end"])
            if end_dt < start_dt:
                raise HTTPException(status_code=400, detail="end must be after start")
            merged["updated_at"] = now
            items[idx] = merged
            updated = merged
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")

    data["items"] = items
    events_store.write_all(data)
    return _event_dict_to_out(updated)


@app.delete(
    "/events/{event_id}",
    tags=["Events"],
    summary="Delete event",
    operation_id="delete_event",
)
def delete_event(event_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete an event by id (must belong to current user)."""
    data = events_store.read_all()
    items = data.get("items", [])
    new_items = [e for e in items if not (e["id"] == event_id and e["user_id"] == user_id)]
    if len(new_items) == len(items):
        raise HTTPException(status_code=404, detail="Event not found")
    data["items"] = new_items
    events_store.write_all(data)
    return {"deleted": True}


def _range_filter(events: list[dict], start_dt: datetime, end_dt: datetime) -> list[dict]:
    out: list[dict] = []
    for e in events:
        e_start = datetime.fromisoformat(e["start"])
        e_end = datetime.fromisoformat(e["end"])
        # Overlap condition
        if e_start < end_dt and e_end > start_dt:
            out.append(e)
    return out


@app.get(
    "/views/day",
    response_model=list[EventOut],
    tags=["Views"],
    summary="Day view",
    operation_id="day_view",
)
def day_view(
    day: date = Query(..., description="Day (YYYY-MM-DD)"),
    user_id: str = Depends(get_current_user_id),
):
    """Return events overlapping a specific day."""
    start_dt = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)
    events = _range_filter(_list_events_for_user(user_id), start_dt, end_dt)
    return [_event_dict_to_out(e) for e in events]


@app.get(
    "/views/week",
    response_model=list[EventOut],
    tags=["Views"],
    summary="Week view",
    operation_id="week_view",
)
def week_view(
    week_start: date = Query(..., description="Week start date (YYYY-MM-DD), typically Monday"),
    user_id: str = Depends(get_current_user_id),
):
    """Return events overlapping a 7-day week starting at week_start."""
    start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=7)
    events = _range_filter(_list_events_for_user(user_id), start_dt, end_dt)
    return [_event_dict_to_out(e) for e in events]


@app.get(
    "/views/month",
    response_model=list[EventOut],
    tags=["Views"],
    summary="Month view",
    operation_id="month_view",
)
def month_view(
    year: int = Query(..., ge=1970, le=2100, description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month number"),
    user_id: str = Depends(get_current_user_id),
):
    """Return events overlapping a calendar month."""
    start_day = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(next_month, datetime.min.time(), tzinfo=timezone.utc)

    events = _range_filter(_list_events_for_user(user_id), start_dt, end_dt)
    return [_event_dict_to_out(e) for e in events]
