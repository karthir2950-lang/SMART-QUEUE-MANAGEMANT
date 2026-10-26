import sys
import os
sys.path.insert(0, os.path.abspath('.'))
import requests

response = requests.post("http://127.0.0.1:8000/api/queue/token/undefined")
print("Status:", response.status_code)
print("Body:", response.text)
