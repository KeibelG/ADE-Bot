import sys
from fastapi.testclient import TestClient
from main import app

sys.stdout.reconfigure(encoding='utf-8')

def test_dashboard():
    with TestClient(app) as client:
        res = client.get("/api/dashboard/metrics")
        print("Metrics Status:", res.status_code)
        print("Metrics Body:", res.json())
        assert res.status_code == 200
        
        res = client.get("/api/dashboard/logs/recent")
        print("Logs Status:", res.status_code)
        print("Logs Body:", res.json())
        assert res.status_code == 200
        
        res = client.get("/api/dashboard/topics")
        print("Topics Status:", res.status_code)
        print("Topics Body:", res.json())
        assert res.status_code == 200

if __name__ == "__main__":
    test_dashboard()
