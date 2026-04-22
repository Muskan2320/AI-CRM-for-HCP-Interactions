from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Literal

class ChatRequest(BaseModel):
    message: str
class InteractionCreate(BaseModel):
    doctor_name: str
    hospital: str

    specialization: Optional[str] = None
    city: Optional[str] = None

    interaction_date: date = Field(default_factory=date.today)
    topic: str
    
    follow_up_action: Optional[str] = None
    follow_up_date: Optional[date] = None

    follow_up_status: Literal["pending", "completed", "cancelled", "no_follow_up"] = None
    notes: Optional[str] = None

class InteractionUpdate(BaseModel):
    topic: Optional[str] = None
    follow_up_action: Optional[str] = None
    
    follow_up_date: Optional[date] = None
    follow_up_status: Optional[Literal["pending", "completed", "cancelled", "no_follow_up"]] = None
    
    notes: Optional[str] = None