import sys
import os
sys.path.insert(0, os.path.abspath('.'))
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import threading
import requests
import time

app = FastAPI()

class RespModel(BaseModel):
    name: str

@app.get("/test", response_model=RespModel)
def test_route():
    return {"wrong_key": "value"} # This will fail validation

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(2)

response = requests.get("http://127.0.0.1:8001/test")
print("Status:", response.status_code)
print("Headers:", response.headers)
print("Body:", response.text)

