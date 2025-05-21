from fastapi import APIRouter, Depends, HTTPException
from fastapi import Body
from sqlalchemy.orm import Session
from models.itinerary import Itinerary
from schemas.itinerary import ItineraryCreate, ItineraryResponse
from typing import List
from models.database import get_db

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])

@router.post("/", response_model=ItineraryResponse)
def save_itinerary(itin: ItineraryCreate, db: Session = Depends(get_db)):
    existing = db.query(Itinerary).filter_by(service_id=itin.service_id).first()
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

@router.get("/{user_id}", response_model=List[ItineraryResponse])
def get_user_itineraries(user_id: str, db: Session = Depends(get_db)):
    return db.query(Itinerary).filter_by(user_id=user_id).order_by(Itinerary.saved_at.desc()).all()

@router.put("/{service_id}", response_model=ItineraryResponse)
def update_itinerary(
    service_id: str,
    updated_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    itin = db.query(Itinerary).filter_by(service_id=service_id).first()
    if not itin:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    for key, value in updated_data.items():
        if hasattr(itin, key):
            setattr(itin, key, value)

    db.commit()
    db.refresh(itin)
    return itin

@router.delete("/{itinerary_id}")
def delete_itinerary(itinerary_id: int, db: Session = Depends(get_db)):
    itin = db.query(Itinerary).filter_by(id=itinerary_id).first()
    if not itin:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    db.delete(itin)
    db.commit()
    return {"message": "Itinerary deleted"}