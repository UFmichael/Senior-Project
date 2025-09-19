import uuid
from datetime import datetime 
from sqlalchemy import  String, func, TIMESTAMP
from sqlalchemy.orm import mapped_column, Mapped 
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from core.database import Base

class User(Base):
    __tablename__ = "Users"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)