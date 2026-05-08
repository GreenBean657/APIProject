import torch
import torch.nn as nn
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from torch.utils.data import TensorDataset, DataLoader
from pydantic import BaseModel
import os


IRIS_CLASSES = ["setosa", "versicolor", "virginica"]
MODEL_DIR = os.getenv("MODEL_DIR", "/app/models")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pth")

def pytorch_basics():
    # Tensor creation from list and via torch.randn
    a = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    b = torch.randn(2, 2)
    print("a =\n", a)
    print("b =\n", b)

    # Basic operations: addition and matrix multiplication
    print("a + b =\n", a + b)
    print("a @ b =\n", a @ b)

    # Autograd demo: y = x^2 + 2x + 1, dy/dx = 2x + 2
    x = torch.tensor(3.0, requires_grad=True)
    y = x ** 2 + 2 * x + 1
    y.backward()
    print(f"x = {x.item()}, dy/dx = {x.grad.item()}")  # x = 3.0, dy/dx = 8.0


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


def train_classifier(epochs: int = 100):
    iris = load_iris()
    x = torch.tensor(iris.data, dtype=torch.float32)
    y = torch.tensor(iris.target, dtype=torch.long)

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    train_loader = DataLoader(TensorDataset(x_train, y_train), batch_size=16, shuffle=True)

    model = SimpleClassifier(4, 16, 3)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        for x_batch, y_batch in train_loader:
            logits = model(x_batch)
            loss = loss_fn(logits, y_batch)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * x_batch.size(0)
        epoch_loss /= len(train_loader.dataset)

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{epochs} - loss: {epoch_loss:.4f}")

    model.eval()
    with torch.no_grad():
        test_logits = model(x_test)
        test_preds = torch.argmax(test_logits, dim=1)
        accuracy = (test_preds == y_test).float().mean().item()
    print(f"Test accuracy: {accuracy * 100:.2f}%")

    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)
    return model, accuracy


def load_model():
    model = SimpleClassifier(4, 16, 3)
    try:
        model.load_state_dict(torch.load(MODEL_PATH))
    except FileNotFoundError:
        train_classifier()
        model.load_state_dict(torch.load(MODEL_PATH))

    model.eval()
    return model


class PredictionRequest(BaseModel):
    features: list[float]


def predict(model, req: PredictionRequest):
    if len(req.features) != 4:
        raise ValueError("features must have exactly 4 values: sepal length, sepal width, petal length, petal width")

    x = torch.tensor(req.features, dtype=torch.float32).unsqueeze(0)

    model.eval()
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
    }


if __name__ == "__main__":
    pytorch_basics()