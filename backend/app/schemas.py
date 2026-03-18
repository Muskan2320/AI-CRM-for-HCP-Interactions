from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class InteractionCreate(BaseModel):
    doctor_name: str
    hospital: str

    specialization: Optional[str] = None
    city: Optional[str] = None

    interaction_date: date = Field(default_factory=date.today)
    topic: str
    
    follow_up_action: Optional[str] = None
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None