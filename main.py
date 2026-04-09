from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

## MEMORY
class Item(BaseModel):
    name: str
    description: str = None

items_db: dict[int, dict] = {}
next_id: int = 1

## ENDPOINTS
@app.get("/items", status_code=200, response_model=list[dict])
def items_get():
    return [{"id": item_id, **item} for item_id, item in items_db.items()]


@app.get("/items/{item_id}", response_model=dict)
def get_item(item_id: int):
    if item_id in items_db:
        return {"id": item_id, **items_db[item_id]}
    else:
        raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", status_code=201, response_model=dict)
def items_push(item: Item):
    global next_id
    items_db[next_id] = item.model_dump()
    item_id = next_id
    next_id += 1
    return {"id": item_id, **items_db[item_id]}

@app.put("/items/{item_id}")
def items_put(item_id: int, item: Item):
    if item_id in items_db:
        items_db[item_id] = item.model_dump()
        return {"id": item_id, **items_db[item_id]}
    else:
        raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
def items_delete(item_id: int):
    if item_id in items_db:
        del items_db[item_id]
    else:
        raise HTTPException(status_code=404, detail="Item not found")