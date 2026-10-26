import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

app = FastAPI()

class RespModel(BaseModel):
    name: str

@app.get("/test", response_model=RespModel)
def test_route():
    return {"wrong_key": "value"} # This will fail validation

client = TestClient(app)
try:
    response = client.get("/test")
    print(response.status_code)
    print(response.text)
except Exception as e:
    print("Exception thrown:", str(e))
