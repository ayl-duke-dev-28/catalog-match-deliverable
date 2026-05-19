import json
import sys
from urllib import request


BASE_URL = "http://127.0.0.1:8000"


def get(path):
    with request.urlopen(BASE_URL + path, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    health = get("/api/health")
    assert health["status"] == "ok", health
    assert health["products"] >= 900, health
    assert health["customers"] >= 5, health

    cases = [
        {"query": "M8 flat washer"},
        {"query": "M8 x 50mm BHCS"},
        {"query": "the same washers as last time", "customer_id": "CUST-001"},
    ]
    for case in cases:
        payload = post("/api/match", case)
        assert len(payload["matches"]) == 3, payload
        assert payload["matches"][0]["confidence"] > 1, payload
        print(case["query"], "=>", payload["matches"][0]["sku"], payload["matches"][0]["confidence"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise
