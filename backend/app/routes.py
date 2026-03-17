from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
        hcp = models.HCP(name=data.doctor_name, hospital=data.hospital)
        db.add(hcp)
        db.commit()
        db.refresh(hcp)

        hcp_created = True

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
    db.refresh(interaction)

    return {
        "message": "Interaction logged successfully",
        "interaction_id": interaction.id,
        "hcp_id": hcp.id,
        "hcp_created": hcp_created
    }