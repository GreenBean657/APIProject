from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, create_engine, select
from pydantic import BaseModel
import os
import requests
from contextlib import asynccontextmanager
from dbformats import ItemCreate, ItemRead, Item, init_db

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/items"
)
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")

engine = create_engine(DATABASE_URL, echo=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware( # AI ASSISTED
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/items", status_code=200, response_model=list[ItemRead])
def items_get():
    with Session(engine) as session:
        return session.exec(select(Item)).all()


@app.get("/items/{item_id}", response_model=ItemRead)
def get_item(item_id: int):
    with Session(engine) as session:
        item = session.get(Item, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item


@app.post("/items", status_code=201, response_model=ItemRead)
def items_push(payload: ItemCreate):
    with Session(engine) as session:
        item = Item(**payload.model_dump())
        session.add(item)
        session.commit()
        session.refresh(item)
        return item


@app.put("/items/{item_id}", response_model=ItemRead)
def items_put(item_id: int, payload: ItemCreate):
    with Session(engine) as session:
        item = session.get(Item, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item.name = payload.name
        item.description = payload.description
        session.add(item)
        session.commit()
        session.refresh(item)
        return item


@app.delete("/items/{item_id}", status_code=204)
def items_delete(item_id: int):
    with Session(engine) as session:
        item = session.get(Item, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        session.delete(item)
        session.commit()


class PredictionRequest(BaseModel):
    features: list[float]


@app.post("/predict")
def predict_endpoint(req: PredictionRequest):
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/predict",
            json={"features": req.features},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Model service unavailable")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail", str(e)))


app.mount("/", StaticFiles(directory="static", html=True), name="static")
