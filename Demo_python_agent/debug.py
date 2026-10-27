import os
from agent import client, BASE_URL, MODEL

print("BASE_URL:", repr(BASE_URL))
print("MODEL:   ", repr(MODEL))
print("Key set: ", bool(os.getenv("API_KEY")))

try:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Say hi"}],
    )
    print("SUCCESS:", r.choices[0].message.content)
except Exception as e:
    print("ERROR:", e)
    print("BODY:", getattr(e, "body", None))
