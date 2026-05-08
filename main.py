from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, create_engine, select
import os
from contextlib import asynccontextmanager
from dbformats import ItemCreate, ItemRead, Item, init_db

from pytorch_basics import load_model, predict, PredictionRequest

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/items"
)
engine = create_engine(DATABASE_URL, echo=True)

ml_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    ml_state["model"] = load_model()
    yield
    ml_state.clear()

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

@app.post("/predict")
def predict_endpoint(req: PredictionRequest):
    model = ml_state.get("model")
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        return predict(model, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


app.mount("/", StaticFiles(directory="static", html=True), name="static")
