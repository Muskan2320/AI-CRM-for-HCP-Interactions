from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from .database import get_db
from . import models, schemas

router = APIRouter()

@router.post("/log-interaction")
def log_interaction(data: schemas.InteractionCreate, db: Session = Depends(get_db)):
    hcp_created = False

    # SEARCH DOCTOR
    hcp = db.query(models.HCP).filter(
        models.HCP.name == data.doctor_name,
        models.HCP.hospital == data.hospital
    ).first()

    # IF DOCTOR NOT FOUND, CREATE NEW
    if not hcp:
        hcp = models.HCP(
            name=data.doctor_name,
            hospital=data.hospital,
            specialization=data.specialization,
            city=data.city
        )
        db.add(hcp)
        db.flush()
        
        hcp_created = True
    else:
        if data.specialization and not hcp.specialization:
            hcp.specialization = data.specialization

        if data.city and not hcp.city:
            hcp.city = data.city

    # LOG INTERACTION
    interaction = models.Interaction(
        hcp_id=hcp.id,
        Interaction_date=data.interaction_date,
        topic=data.topic,
        follow_up_action=data.follow_up_action,
        follow_up_date=data.follow_up_date,
        notes=data.notes
    )

    db.add(interaction)
    db.commit()

    db.refresh(hcp)
    db.refresh(interaction)

    return {
        "message": "Interaction logged successfully",
        "interaction_id": interaction.id,
        "hcp_id": hcp.id,
        "hcp_created": hcp_created
    }

@router.get("/pending-follow-ups")
def get_pending_followups(db: Session = Depends(get_db)):
    today = date.today()

    followups = db.query(models.Interaction).filter(
        models.Interaction.follow_up_status == "pending",
        models.Interaction.follow_up_date != None,
        models.Interaction.follow_up_date <= today
    ).all()

    result = []

    for f in followups:
        result.append({
            "interaction_id": f.id,
            "hcp_id": f.hcp_id,
            "doctor_name": f.hcp.name,
            "hospital": f.hcp.hospital,
            "follow_up_action": f.follow_up_action,
            "follow_up_date": f.follow_up_date,
            "topic": f.topic
        })

    return result