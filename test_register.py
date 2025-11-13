import requests
import json

url = "http://localhost:5000/auth/register"
data = {
    "username": "testuser2",
    "password": "testpass"
}

response = requests.post(url, json=data)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")