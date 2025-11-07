
from pydantic import BaseModel, Field, model_validator

from backend.core.enums import ThreatLevels, ThreatStatus

class ThreatBase(BaseModel):
    threat_level: ThreatLevels
    threat_status: ThreatStatus