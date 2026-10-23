from fastapi import FastAPI
from app.models import Item

app = FastAPI()

@app.get("/items")
def get_items():
    return [Item("sample")]
