from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models.itinerary import Itinerary
from schemas.itinerary import ItineraryCreate, ItineraryResponse
from typing import List
from models.database import get_db
from utils.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])

# ✅ Save or update an itinerary (must be logged in)
@router.post("/", response_model=ItineraryResponse)
def save_itinerary(
    itin: ItineraryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if itin.user_id != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to save for another user")

    existing = db.query(Itinerary).filter_by(service_id=itin.service_id, user_id=current_user.username).first()
    if existing:
        for key, value in itin.dict().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    new_itin = Itinerary(**itin.dict())
    db.add(new_itin)
    db.commit()
    db.refresh(new_itin)
    return new_itin

# ✅ Secure route: Get only *your* itineraries
@router.get("/me", response_model=List[ItineraryResponse])
def get_user_itineraries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Itinerary).filter_by(user_id=current_user.username).order_by(Itinerary.saved_at.desc()).all()

# ✅ Update itinerary (only by owner)
@router.put("/{service_id}", response_model=ItineraryResponse)
def update_itinerary(
    service_id: str,
    updated_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    itin = db.query(Itinerary).filter_by(service_id=service_id, user_id=current_user.username).first()
    if not itin:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    for key, value in updated_data.items():
        if hasattr(itin, key):
            setattr(itin, key, value)

    db.commit()
    db.refresh(itin)
    return itin

# ✅ Delete itinerary (only by owner)
@router.delete("/{itinerary_id}")
def delete_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    itin = db.query(Itinerary).filter_by(id=itinerary_id, user_id=current_user.username).first()
    if not itin:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    db.delete(itin)
    db.commit()
    return {"message": "Itinerary deleted"}