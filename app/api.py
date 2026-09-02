from collections.abc import Generator
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.auth import (
    DUMMY_PASSWORD_HASH,
    LoginRateLimiter,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import Settings
from app.discovery import ReaderDiscovery, validate_reader_ip
from app.models import ApiUser, Reader
from app.epc import parse_epc
from app.models import TagRead

bearer_scheme = HTTPBearer(auto_error=False)
templates = Jinja2Templates(directory="app/templates")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    new_password: str | None = Field(default=None, min_length=12, max_length=1024)

    def has_changes(self) -> bool:
        return self.username is not None or self.new_password is not None


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=1024)
    role: str = Field(default="read_only", pattern="^(administrator|api_client|read_only)$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    enabled: bool


class ReaderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    ip_address: str
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    mac_address: str | None = Field(default=None, pattern=r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")
    firmware_version: str | None = Field(default=None, max_length=100)
    enabled: bool = True

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str) -> str:
        return validate_reader_ip(value)


class ReaderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    mac_address: str | None = Field(default=None, pattern=r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")
    firmware_version: str | None = Field(default=None, max_length=100)


class ReaderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    ip_address: str
    model: str | None
    serial_number: str | None
    mac_address: str | None
    firmware_version: str | None
    status: str
    enabled: bool
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    last_data_at: datetime | None
    last_error: str | None
    tag_read_count: int = 0


class ReaderDiscoveryRequest(BaseModel):
    addresses: list[str] = Field(min_length=1, max_length=256)

    @field_validator("addresses")
    @classmethod
    def validate_addresses(cls, values: list[str]) -> list[str]:
        return [validate_reader_ip(value) for value in values]


class ReaderDiscoveryResponse(BaseModel):
    ip_address: str
    status: str
    model: str | None
    firmware_version: str | None
    serial_number: str | None
    mac_address: str | None


class TagReadCreate(BaseModel):
    reader_id: int = Field(gt=0)
    epc_hex: str
    antenna: int | None = Field(default=None, ge=0)
    rssi: float | None = None
    raw_payload: str = ""

    @field_validator("epc_hex")
    @classmethod
    def normalize_epc_hex(cls, value: str) -> str:
        return parse_epc(value).hex_value


class TagReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reader_id: int
    reader_ip: str
    epc_hex: str
    epc_decimal: str
    epc_bit_length: int
    antenna: int | None
    rssi: float | None
    received_at: datetime
    seen_count: int


def create_api(settings: Settings, session_factory: sessionmaker[Session]) -> FastAPI:
    app = FastAPI(title="Zebra RFID Server")
    rate_limiter = LoginRateLimiter(
        settings.login_rate_limit_attempts,
        settings.login_rate_limit_window_seconds,
    )

    def get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        session: Session = Depends(get_session),
    ) -> ApiUser:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        try:
            claims = decode_access_token(credentials.credentials, settings.jwt_secret)
            user = session.get(ApiUser, int(claims["sub"]))
        except (ValueError, TypeError):
            user = None
        if user is None or not user.enabled:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return user

    def administrator(user: ApiUser = Depends(current_user)) -> ApiUser:
        if user.role != "administrator":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
        return user

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "dashboard.html")

    @app.post("/api/v1/auth/login", response_model=TokenResponse)
    def login(payload: LoginRequest, request: Request, session: Session = Depends(get_session)) -> TokenResponse:
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

        user = session.scalar(select(ApiUser).where(ApiUser.username == payload.username))
        user_enabled = user is not None and user.enabled
        password_hash = user.password_hash if user_enabled else DUMMY_PASSWORD_HASH
        password_valid = verify_password(password_hash, payload.password)
        if not user_enabled or not password_valid:
            rate_limiter.record_failure(client_ip)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        rate_limiter.record_success(client_ip)
        user.last_login_at = datetime.now(timezone.utc)
        session.commit()
        return TokenResponse(
            access_token=create_access_token(
                user.id,
                user.username,
                user.role,
                settings.jwt_secret,
                settings.jwt_access_token_minutes,
            )
        )

    @app.get("/api/v1/auth/me")
    def me(user: ApiUser = Depends(current_user)) -> dict[str, str | int]:
        return {"id": user.id, "username": user.username, "role": user.role}

    @app.patch("/api/v1/auth/me")
    def update_me(
        payload: UserUpdate, session: Session = Depends(get_session), user: ApiUser = Depends(current_user)
    ) -> dict[str, str | int]:
        if not payload.has_changes() or not verify_password(user.password_hash, payload.current_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid update request")
        if user.username == "admin" and payload.username is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The admin username cannot be changed")
        if payload.username is not None:
            user.username = payload.username
        if payload.new_password is not None:
            user.password_hash = hash_password(payload.new_password)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists") from error
        return {"id": user.id, "username": user.username, "role": user.role}

    @app.post("/api/v1/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    def create_user(
        payload: UserCreate, session: Session = Depends(get_session), _: ApiUser = Depends(administrator)
    ) -> ApiUser:
        user = ApiUser(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=payload.role,
            enabled=True,
        )
        session.add(user)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists") from error
        session.refresh(user)
        return user

    @app.get("/api/v1/users", response_model=list[UserResponse])
    def list_users(
        session: Session = Depends(get_session), _: ApiUser = Depends(administrator)
    ) -> list[ApiUser]:
        return list(session.scalars(select(ApiUser).order_by(ApiUser.username)))

    @app.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_user(
        user_id: int, session: Session = Depends(get_session), administrator_user: ApiUser = Depends(administrator)
    ) -> None:
        user = session.get(ApiUser, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.username == "admin" or user.id == administrator_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This user cannot be deleted")
        session.delete(user)
        session.commit()

    @app.get("/api/v1/readers", response_model=list[ReaderResponse])
    def list_readers(
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        session: Session = Depends(get_session),
        _: ApiUser = Depends(current_user),
    ) -> list[ReaderResponse]:
        statement = (
            select(Reader, func.count(TagRead.id).label("tag_read_count"))
            .outerjoin(TagRead, TagRead.reader_id == Reader.id)
            .group_by(Reader.id)
            .order_by(Reader.id)
            .offset(offset)
            .limit(limit)
        )
        return [
            ReaderResponse.model_validate(reader).model_copy(update={"tag_read_count": tag_read_count})
            for reader, tag_read_count in session.execute(statement)
        ]

    @app.get("/api/v1/readers/{reader_id}", response_model=ReaderResponse)
    def get_reader(
        reader_id: int, session: Session = Depends(get_session), _: ApiUser = Depends(current_user)
    ) -> Reader:
        reader = session.get(Reader, reader_id)
        if reader is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader not found")
        return reader

    @app.post("/api/v1/readers", response_model=ReaderResponse, status_code=status.HTTP_201_CREATED)
    def create_reader(
        payload: ReaderCreate, session: Session = Depends(get_session), _: ApiUser = Depends(administrator)
    ) -> Reader:
        reader = Reader(
            name=payload.name,
            ip_address=payload.ip_address,
            model=payload.model,
            serial_number=payload.serial_number,
            mac_address=payload.mac_address,
            firmware_version=payload.firmware_version,
            enabled=payload.enabled,
        )
        session.add(reader)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reader name or IP already exists") from error
        session.refresh(reader)
        return reader

    @app.patch("/api/v1/readers/{reader_id}", response_model=ReaderResponse)
    def update_reader(
        reader_id: int,
        payload: ReaderUpdate,
        session: Session = Depends(get_session),
        _: ApiUser = Depends(administrator),
    ) -> Reader:
        reader = session.get(Reader, reader_id)
        if reader is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader not found")
        for field_name, value in payload.model_dump(exclude_unset=True).items():
            setattr(reader, field_name, value)
        session.commit()
        session.refresh(reader)
        return reader

    @app.post("/api/v1/readers/discover", response_model=list[ReaderDiscoveryResponse])
    async def discover_readers(
        payload: ReaderDiscoveryRequest, _: ApiUser = Depends(administrator)
    ) -> list[ReaderDiscoveryResponse]:
        return [ReaderDiscoveryResponse(**reader.__dict__) for reader in await ReaderDiscovery().discover(payload.addresses)]

    @app.get("/api/v1/tag-reads", response_model=list[TagReadResponse])
    def list_tag_reads(
        epc_hex: str | None = None,
        epc_decimal: str | None = None,
        reader_id: int | None = Query(default=None, gt=0),
        antenna: int | None = Query(default=None, ge=0),
        received_after: datetime | None = None,
        received_before: datetime | None = None,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        session: Session = Depends(get_session),
        _: ApiUser = Depends(current_user),
    ) -> list[TagRead]:
        if received_after and received_before and received_after > received_before:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid time range")
        statement = select(TagRead).order_by(TagRead.received_at.desc())
        if epc_hex is not None:
            statement = statement.where(TagRead.epc_hex == parse_epc(epc_hex).hex_value)
        if epc_decimal is not None:
            statement = statement.where(TagRead.epc_decimal == epc_decimal)
        if reader_id is not None:
            statement = statement.where(TagRead.reader_id == reader_id)
        if antenna is not None:
            statement = statement.where(TagRead.antenna == antenna)
        if received_after is not None:
            statement = statement.where(TagRead.received_at >= received_after)
        if received_before is not None:
            statement = statement.where(TagRead.received_at <= received_before)
        return list(session.scalars(statement.offset(offset).limit(limit)))

    @app.post("/api/v1/tag-reads", response_model=TagReadResponse, status_code=status.HTTP_201_CREATED)
    def create_tag_read(
        payload: TagReadCreate, session: Session = Depends(get_session), _: ApiUser = Depends(current_user)
    ) -> TagRead:
        reader = session.get(Reader, payload.reader_id)
        if reader is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader not found")
        epc = parse_epc(payload.epc_hex)
        tag_read = TagRead(
            reader_id=reader.id,
            reader_ip=reader.ip_address,
            epc_hex=epc.hex_value,
            epc_decimal=epc.decimal_value,
            epc_bit_length=epc.bit_length,
            antenna=payload.antenna,
            rssi=payload.rssi,
            raw_payload=payload.raw_payload,
        )
        session.add(tag_read)
        session.commit()
        session.refresh(tag_read)
        return tag_read

    @app.get("/api/v1/tag-reads/latest", response_model=TagReadResponse)
    def latest_tag_read(session: Session = Depends(get_session), _: ApiUser = Depends(current_user)) -> TagRead:
        tag_read = session.scalar(select(TagRead).order_by(TagRead.received_at.desc()).limit(1))
        if tag_read is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tag reads found")
        return tag_read

    @app.get("/api/v1/tag-reads/{tag_read_id}", response_model=TagReadResponse)
    def get_tag_read(
        tag_read_id: int, session: Session = Depends(get_session), _: ApiUser = Depends(current_user)
    ) -> TagRead:
        tag_read = session.get(TagRead, tag_read_id)
        if tag_read is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag read not found")
        return tag_read

    return app