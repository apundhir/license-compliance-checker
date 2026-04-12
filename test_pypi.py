import sys
import requests

url = "https://pypi.org/pypi/requests/json"
try:
    response = requests.get(url, timeout=10)
    print("Status:", response.status_code)
    data = response.json()
    print("Keys:", list(data.keys()))
    print("Info license:", data.get("info", {}).get("license"))
except Exception as e:
    print("Error:", e)
