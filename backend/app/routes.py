from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from .database import get_db
from . import models, schemas
from app.langgraph.agent import graph
from app.auth import hash_password, verify_password, create_access_token, verify_access_token, get_current_user

router = APIRouter()

@router.post("/signup")
def signup(
    data: schemas.UserCreate,
    db: Session = Depends(get_db)
):

    try:

        existing_user = db.query(models.User).filter(
            models.User.email == data.email
        ).first()

        if existing_user:

            return {
                "success": False,
                "error": "Email already registered"
            }

        hashed_password = hash_password(data.password)

        user = models.User(
            email=data.email,
            hashed_password=hashed_password
        )

        db.add(user)

        db.commit()

        db.refresh(user)

        return {
            "success": True,
            "message": "User created successfully",
            "user_id": user.id
        }

    except Exception as e:

        db.rollback()

        return {
            "success": False,
            "error": str(e)
        }
    
@router.post("/login")
def login(
    data: schemas.UserLogin,
    db: Session = Depends(get_db)
):

    try:

        user = db.query(models.User).filter(
            models.User.email == data.email
        ).first()

        if not user or not verify_password(data.password, user.hashed_password):

            return {
                "success": False,
                "error": "Invalid email or password"
            }

        token = create_access_token({"user_id": user.id, "email": user.email})

        return {
            "success": True,
            "access_token": token
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
    
@router.post("/chat")
def chat(request: schemas.ChatRequest, current_user: dict = Depends(get_current_user)):
    try:
        result = graph.invoke({"input": request.message})

        return {
            "success": True,
            "response": result.get("output", "Sorry, I couldn't process your request.")
        }
    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


@router.post("/log-interaction")
def log_interaction(data: schemas.InteractionCreate, db: Session = Depends(get_db)):
    try:
        hcp_created = False

        # SEARCH DOCTOR
        hcp = db.query(models.HCP).filter(
            models.HCP.name == data.name,
            models.HCP.hospital == data.hospital
        ).first()

        # IF DOCTOR NOT FOUND, CREATE NEW
        if not hcp:
            hcp = models.HCP(
                name=data.name,
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
            interaction_date=data.interaction_date,
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
            "success": True,
            "data": {
                "message": "Interaction logged successfully",
                "interaction_id": interaction.id,
                "hcp_id": hcp.id,
                "hcp_created": hcp_created
            }
        }
    except Exception as e:

        db.rollback()

        return {
            "success": False,
            "error": str(e)
        }

@router.put("/interaction/{interaction_id}")
def update_interaction(interaction_id: int, data: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    try:
        interaction = db.query(models.Interaction).filter(
            models.Interaction.id == interaction_id
        ).first()

        if not interaction:
            return {"success": False, "error": "Interaction not found"}
        
        updated_fields = []

        if data.topic is not None:
            interaction.topic = data.topic
            updated_fields.append("topic")

        if data.follow_up_action is not None:
            interaction.follow_up_action = data.follow_up_action
            updated_fields.append("follow_up_action")

        if data.follow_up_date is not None:
            interaction.follow_up_date = data.follow_up_date
            updated_fields.append("follow_up_date")

        if data.follow_up_status is not None:
            interaction.follow_up_status = data.follow_up_status
            updated_fields.append("follow_up_status")

        if data.notes is not None:
            interaction.notes = data.notes
            updated_fields.append("notes")

        db.commit()
        db.refresh(interaction)

        return {
            "success": True,
            "data": {
                "message": "Interaction updated successfully",
                "interaction_id": interaction.id,
                "updated_fields": updated_fields
            }
        }
    except Exception as e:

        db.rollback()

        return {
            "success": False,
            "error": str(e)
        }

@router.get("/pending-follow-ups")
def get_pending_followups(target_date: date = Query(None), db: Session = Depends(get_db)):
    try:
        query = db.query(models.Interaction).filter(
            models.Interaction.follow_up_status == "pending",
            models.Interaction.follow_up_date.isnot(None)
        )

        if target_date:
            query = query.filter(models.Interaction.follow_up_date <= target_date)

        query = query.order_by(models.Interaction.follow_up_date.asc())
        followups = query.all()

        result = []
        for f in followups:
            result.append({
                "interaction_id": f.id,
                "hcp_id": f.hcp_id,
                "name": f.hcp.name,
                "hospital": f.hcp.hospital,
                "follow_up_action": f.follow_up_action,
                "follow_up_date": f.follow_up_date,
                "topic": f.topic
            })

        return {
            "success": True,
            "data": result
        }
    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }

@router.get("/hcp/{hcp_id}/interaction-history")
def get_hcp_interaction_history(hcp_id: int, db: Session = Depends(get_db)):
    try:
        interactions = db.query(models.Interaction).filter(models.Interaction.hcp_id == hcp_id).all()

        if not interactions:
            return {"success": True, "data": [], "message": "No interactions found for this HCP"}
        
        result = []
        for i in interactions:
            result.append({
                "interaction_id": i.id,
                "interaction_date": i.interaction_date,
                "topic": i.topic,
                "follow_up_action": i.follow_up_action,
                "follow_up_date": i.follow_up_date,
                "follow_up_status": i.follow_up_status,
                "notes": i.notes
            })

        return {
            "success": True,
            "data": result
        }
    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }

@router.get("/hcp/search")
def search_hcp(hcp_id: int = None,name: str = None, hospital: str = None, limit: int = 10, db: Session = Depends(get_db)):
    try:
        query = db.query(models.HCP)

        if hcp_id is not None:
            hcp = query.filter(models.HCP.id == hcp_id).first()

            if not hcp:
                return {"success": False, "error": "HCP not found"}
            
            results = [hcp]
            
        elif not name and not hospital:
            results = query.order_by(models.HCP.created_at.desc()).limit(limit=limit).all()

        else:
            if name and hospital:
                query = query.filter(
                    models.HCP.name.ilike(f"%{name}%"),
                    models.HCP.hospital.ilike(f"%{hospital}%")
                )
            elif name:
                query = query.filter(models.HCP.name.ilike(f"%{name}%"))
            elif hospital:
                query = query.filter(models.HCP.hospital.ilike(f"%{hospital}%"))

            results = query.all()

        return {
            "success": True,
            "data": [
                {
                    "hcp_id": hcp.id,
                    "name": hcp.name,
                    "hospital": hcp.hospital,
                    "specialization": hcp.specialization,
                    "city": hcp.city
                }
                for hcp in results
            ]
        }
    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
