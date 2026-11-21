import requests

url = "http://localhost:11434/api/generate"

payload = {
	
	"model": "qwen2.5-coder:7b",
	"prompt": "Reply with only the word: ready",
	"stream": False,
} 

reply = requests.post(url, json=payload, timeout=300)
data = reply.json()
print(data["response"])
