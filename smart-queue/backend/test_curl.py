import sys
import os
sys.path.insert(0, os.path.abspath('.'))
import requests

# We need a valid appointment_id. Let's just use a fake UUID to see if we get 401 or 404
import uuid
fake_id = str(uuid.uuid4())

response = requests.post(f"http://127.0.0.1:8000/api/queue/token/{fake_id}")
print("Status:", response.status_code)
print("Body:", response.text)
