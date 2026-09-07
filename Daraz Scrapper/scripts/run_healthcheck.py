"""CLI verification script to perform a quick health check validation."""

import asyncio
import sys
import httpx


async def check_health(url: str = "http://127.0.0.1:8000/health"):
    print(f"Checking health on {url}...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            print(f"Status Code: {resp.status_code}")
            print(f"Response Body: {resp.text}")
            if resp.status_code == 200 and resp.json().get("status") == "healthy":
                print(">> Health check PASSED!")
                return 0
            else:
                print(">> Health check FAILED: Unexpected response")
                return 1
    except Exception as e:
        print(f">> Health check FAILED with error: {e}")
        return 1


if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/health"
    sys.exit(asyncio.run(check_health(url_arg)))
