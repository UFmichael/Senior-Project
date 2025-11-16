import asyncio
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

# --- 1. Import your settings ---
from core.config import get_settings

# --- 2. Get settings at the module level ---
try:
    settings = get_settings()
    # --- 3. Create the ASYNC database URL ---
    # We must use an async driver like 'asyncpg'
    ASYNC_DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}/{settings.DB_NAME}"

    async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
    
    # --- 4. Create the ASYNC session factory ---
    # This is what the service will use to get sessions
    AsyncSessionFactory = async_sessionmaker(
        async_engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    print("Async database engine for ThreatService created successfully.")

except Exception as e:
    print(f"Failed to create async database engine for ThreatService: {e}")
    print("Database logging will be disabled.")
    AsyncSessionFactory = None


# Import your existing Threat model
# Make sure the path is correct
try:
    from entities.common.models.model_threat import Threat
    from core.enums import ThreatLevels, ThreatStatus
except ImportError:
    print("Warning: Could not import Threat model. Using placeholder.")
    # This is a placeholder so the file can be read.
    # Replace with your actual model imports.
    from enum import Enum
    class Base: pass
    class ThreatLevels(Enum): LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"
    class ThreatStatus(Enum): MONITORING="MONITORING"; CLEARED="CLEARED"
    class Threat(Base):
        def __init__(self, **kwargs):
            self.id = 1 # Dummy id for refresh

class ThreatService:
    def __init__(self):
        """
        Initializes the ThreatService.
        It will use the module-level AsyncSessionFactory.
        """
        if AsyncSessionFactory is None:
            print("Warning: ThreatService initialized, but DB connection is not available.")
        # No self.session or self.engine needed here,
        # we will get sessions from the factory.

    async def log_new_threat(self, person_data: Dict[str, Any], stream_id: str):
        """
        Logs a new threat event to the database based on a Person object's data.
        """
        if AsyncSessionFactory is None:
            print("Database not initialized. Skipping threat log.")
            return

        # --- 1. Map Person data to Threat model ---
        primary_weapon = None
        if person_data.get("weapons"):
            primary_weapon = max(person_data["weapons"], key=lambda w: w.get("confidence", 0))
        face_data = person_data.get("face")
        
        # --- 2. Create the Threat database object ---
        new_threat = Threat(
            # TODO: Replace '1' with a real admin/user ID from your context
            admin=1, 
            
            threat_level=ThreatLevels.HIGH if primary_weapon else ThreatLevels.LOW,
            threat_status=ThreatStatus.MONITORING,
            
            predicted_emotion=face_data.get("dominant_emotion") if face_data else None,
            face_confidence=int(face_data.get("confidence", 0) * 100) if face_data else None,
            
            predicted_weapon=primary_weapon.get("original_class") if primary_weapon else None,
            weapon_confidence=int(primary_weapon.get("confidence", 0) * 100) if primary_weapon else None,
        )

        # --- 3. Save to database asynchronously ---
        try:
            # Get a new session from the factory for this one task
            async with AsyncSessionFactory() as session:
                async with session.begin():
                    session.add(new_threat)
                
                # Refresh to get the ID and timestamp
                await session.refresh(new_threat) 
                
                print(f"✅ Successfully logged Threat ID: {new_threat.id} "
                      f"for Person: {person_data.get('id')}")
                return new_threat
                
        except Exception as e:
            print(f"❌ Error logging threat to database: {e}")
            
            import traceback
            traceback.print_exc()