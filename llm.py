import requests

url = "https://petri-crowbar-occupier.ngrok-free.dev/api/generate"

payload = {
    "model": "gemma4:e2b",
    "prompt": "Explain autonomous driving",
    "stream": False
}

r = requests.post(url, json=payload)

print(r.json()["response"])