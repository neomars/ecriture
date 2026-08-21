from ai_client import AIClient
client = AIClient()
try:
    print(client.generate_chat([{"role": "user", "content": "salut"}]))
except Exception as e:
    import traceback
    traceback.print_exc()
