from ai_client import AIClient
client = AIClient()
print(client.get_fallback_response("chat", [{"role": "user", "content": "salut"}], lang="fr"))
