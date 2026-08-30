import httpx
r = httpx.get('http://localhost:8000/api/accounts/')
print(r.status_code)