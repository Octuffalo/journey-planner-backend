from fastapi import FastAPI
from routers import train_routes
from fastapi.middleware.cors import CORSMiddleware
from routers import itinerary_routes
from models.database import Base, engine
from routers import auth_routes
from routers import user_routes
from routers import station_routes
from routers import places_routes
from routers import journey_routes

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(train_routes.router)
app.include_router(itinerary_routes.router)
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(station_routes.router)
app.include_router(places_routes.router)
app.include_router(journey_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://journey-planner-ui.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Journey Planner API is running!"}