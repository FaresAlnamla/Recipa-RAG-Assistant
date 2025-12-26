import httpx

def main():
    r = httpx.get("http://127.0.0.1:9000/health", timeout=10)
    print("GET /health:", r.status_code)
    print(r.json())

if __name__ == "__main__":
    main()
