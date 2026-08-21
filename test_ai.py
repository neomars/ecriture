import requests
res = requests.post("http://localhost:5000/api/ai/chat", json={"messages": [{"role": "user", "content": "salut"}]})
print(res.json())
