import requests

res = requests.post('http://localhost:8000/api/queue/token/fd5de059-6192-4bb2-aa0f-c79df56d3d55')
print(f"Status: {res.status_code}")
print(f"Body: {res.text}")
