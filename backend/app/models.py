from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
from datetime import datetime
from .database import Base

class HCP(Base):
    __tablename__ = "hcps"
    __table_args__ = (UniqueConstraint("name", "hospital", name="unique_doctor_hospital"),)

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, index=True)
    hospital = Column(String, index=True)

    specialization = Column(String, nullable=True)
    city = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp")

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    hcp_id = Column(Integer, ForeignKey("hcps.id"))

    Interaction_date = Column(Date)
    topic = Column(String)

    follow_up_action = Column(String)
    follow_up_date = Column(Date)

    follow_up_status = Column(String, default="pending")
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")