import requests
res = requests.get('http://127.0.0.1:8000/api/health')
print("Status:", res.status_code)
print("Body:", res.text)
