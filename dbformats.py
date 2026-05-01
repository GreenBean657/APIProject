from sqlmodel import SQLModel, Field
from pydantic import BaseModel

class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = Field(default=None)

class ItemCreate(BaseModel):
    name: str
    description: str | None = None

class ItemRead(BaseModel):
    id: int
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


def init_db(engine):
    SQLModel.metadata.create_all(engine)