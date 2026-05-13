# APIProject

### Screenshot of the project running: screenshots/ItemsPage.png

An API Project for AIE300. 

The purpose of this expanded project is to meet the requirements defined by the "[L2] Full-Stack App with Docker " assignment.

Database chosen: postgres
Reason: Easy to set up in python, but still a bit harder than a basic SQLLite so the assignment isn't too easy. 

## To run:
```
cat > .env << 'EOF'
DATABASE_URL=<URL>
PASSWORD=<PASS>
EOF

sudo docker compose up --build
```


## Example .env file:
```
DATABASE_URL=postgresql://<USERNAME>:<PASS>@db:5432/items
PASSWORD=<PASS>
```

### Architecture:

```
Client
  │
  ▼
API (:8000)  ──────────────────────────────────────────────────────────────────────
  │                        │                                   │
  │  GET/POST /items       │  POST /predict                    │  /health checks
  ▼                        ▼                                   ▼
Database (:5432)    Model Service (:8001)              Model Service (:8001)
(PostgreSQL)          (PyTorch Iris                     GET /health
                       Classifier)
                          │
                          ▼
                      prediction
                      (JSON response)
```

Request flow:
- `Client → API (:8000) → Database (:5432)` for CRUD operations
- `Client → API (:8000) → Model Service (:8001) → prediction` for ML inference
- The client never talks directly to the model container


### API: 
| Method  | Endpoint    | Description                                     | Status Code     |
|---------|-------------|-------------------------------------------------|-----------------|
| GET     | /items      | Return a list of all items                      | 200             |
| GET     | /items/{id} | Return a single item by ID, or 404 if not found | 200 / 404       |
| POST    | /items      | Create a new item from JSON body                | 201             |
| PUT     | /items/{id} | Update an existing item, or 404 if not found    | 200 / 404       |
| DELETE  | /items/{id} | Delete an item by ID, or 404 if not found       | 200 / 404       |    
| PREDICT | /predict    | Predict with the iris model                     | 503 / 400 / 200 |

### L3/L4: PyTorch Model Service:
The model runs in its own container (`model_service/`). On startup it trains the Iris classifier if no saved weights are found, then serves predictions over HTTP. The main API proxies `/predict` to this service — it no longer imports PyTorch directly.

```python
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

```
Used via: `SimpleClassifier(4, 16, 3)`. Trained model is saved, and can be inferenced later.
**Try it:**                                                                            

```bash                                                                                          
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"features":[5.1,3.5,1.4,0.2]}'                                                       
``` 

```json
{
  "prediction": "setosa",
  "confidence": 0.9876,
  "probabilities": {
    "setosa": 0.9876,
    "versicolor": 0.0123,
    "virginica": 0.0001
  }
}
```


# AI Disclaimers
index.html is largely AI assisted.
dbformats was slightly AI assisted in terms of how to create the items.
main.py is only AI assisted where marked.
