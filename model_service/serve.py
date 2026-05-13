from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import torch
import torch.nn as nn
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from torch.utils.data import TensorDataset, DataLoader
from pydantic import BaseModel
import os

IRIS_CLASSES = ["setosa", "versicolor", "virginica"]
MODEL_PATH = "/app/model/iris_model.pth"


class SimpleClassifier(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super().__init__()
        self.l1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.l2 = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        x = self.relu(self.l1(x))
        x = self.l2(x)
        return x


def train_and_save() -> SimpleClassifier:
    iris = load_iris()
    x = torch.tensor(iris.data, dtype=torch.float32)
    y = torch.tensor(iris.target, dtype=torch.long)
    x_train, _, y_train, _ = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)
    train_loader = DataLoader(TensorDataset(x_train, y_train), batch_size=16, shuffle=True)

    model = SimpleClassifier(4, 16, 3)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    for _ in range(100):
        model.train()
        for x_batch, y_batch in train_loader:
            logits = model(x_batch)
            loss = loss_fn(logits, y_batch)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    model.eval()
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)
    print("Model trained and saved.")
    return model


ml_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    model = SimpleClassifier(4, 16, 3)
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
        model.eval()
        print("Model loaded from disk.")
    else:
        model = train_and_save()
    ml_state["model"] = model
    yield
    ml_state.clear()


app = FastAPI(lifespan=lifespan)


class PredictionRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": "model" in ml_state}


@app.post("/predict")
def predict(req: PredictionRequest):
    if len(req.features) != 4:
        raise HTTPException(
            status_code=400,
            detail="features must have exactly 4 values: sepal length, sepal width, petal length, petal width",
        )

    model = ml_state["model"]
    x = torch.tensor(req.features, dtype=torch.float32).unsqueeze(0)

    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)
        confidence, pred_idx = torch.max(probs, dim=1)

    return {
        "prediction": IRIS_CLASSES[pred_idx.item()],
        "confidence": round(confidence.item(), 4),
        "probabilities": {
            cls: round(p, 4)
            for cls, p in zip(IRIS_CLASSES, probs.squeeze().tolist())
        },
        "model": "iris-classifier-v1",
    }
