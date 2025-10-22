import uuid
from datetime import datetime 
from sqlalchemy import  String, func, TIMESTAMP
from sqlalchemy.orm import mapped_column, Mapped 
from core.enums import ThreatLevels, ThreatStatus
from core.database import Base
from sqlalchemy import String, Enum as SQLEnum, ForeignKey, CheckConstraint, Integer, func, Float, Numeric, event, text

class Threat(Base):
    __tablename__ = "Threats" 

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    admin: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    threat_level: Mapped[ThreatLevels] = mapped_column(SQLEnum(ThreatLevels), default=ThreatLevels.LOW, nullable=False)
    threat_status: Mapped[ThreatStatus] = mapped_column(SQLEnum(ThreatStatus), default=ThreatStatus.MONITORING, nullable=False)
    predicted_age: Mapped[int] = mapped_column(Integer, nullable=True)
    predicted_sex: Mapped[str] = mapped_column(String(10), nullable=True)
    predicted_emotion: Mapped[str] = mapped_column(String(255), nullable=True)
    face_confidence: Mapped[int] = mapped_column(Integer, nullable=True)
    weapon_confidence: Mapped[int] = mapped_column(Integer, nullable=True)
    predicted_weapon: Mapped[str] = mapped_column(String(255), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
   
