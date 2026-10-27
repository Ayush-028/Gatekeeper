from agent import client

for m in client.models.list():
    print(m.id)
