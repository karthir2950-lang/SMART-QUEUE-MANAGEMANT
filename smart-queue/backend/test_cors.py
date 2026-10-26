import requests

url = "http://localhost:8000/api/auth/me"
headers = {
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "GET"
}
response = requests.options(url, headers=headers)
print("Status:", response.status_code)
print("Headers:", response.headers)
print("Text:", response.text)
