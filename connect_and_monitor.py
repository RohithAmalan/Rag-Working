#!/usr/bin/env python3
"""
Complete flow: Login → Query → Monitor
Shows requests flowing through Backend → Prometheus → Grafana
"""

import requests
import json
import time
from typing import Optional

# Configuration
API_URL = "http://localhost:8001"
PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3003"

class RAGClient:
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.token: Optional[str] = None
        self.session = requests.Session()
    
    def login(self, username: str = "admin", password: str = "admin123") -> bool:
        """Step 1: Login and get token"""
        print("\n" + "="*60)
        print("STEP 1: LOGIN")
        print("="*60)
        try:
            response = self.session.post(
                f"{self.api_url}/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                print(f"✓ Login successful!")
                print(f"  Token: {self.token[:50]}...")
                return True
            else:
                print(f"✗ Login failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def query(self, query_text: str, top_k: int = 5) -> bool:
        """Step 2: Make RAG query"""
        print("\n" + "="*60)
        print("STEP 2: MAKE RAG QUERY")
        print("="*60)
        if not self.token:
            print("✗ Not logged in!")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "question": query_text,
                "top_k": top_k
            }
            print(f"Question: '{query_text}'")
            print(f"Top K: {top_k}")
            
            response = self.session.post(
                f"{self.api_url}/query",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Query successful!")
                print(f"  Answer: {result.get('answer', 'N/A')[:100]}...")
                print(f"  Sources found: {len(result.get('sources', []))}")
                print(f"  Confidence: {result.get('confidence', 'N/A')}")
                return True
            else:
                print(f"✗ Query failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Query error: {e}")
            return False
    
    def upload_file(self, file_path: str) -> bool:
        """Step 2b: Upload a document (optional)"""
        print("\n" + "="*60)
        print("STEP 2b: UPLOAD DOCUMENT (Optional)")
        print("="*60)
        if not self.token:
            print("✗ Not logged in!")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = self.session.post(
                    f"{self.api_url}/upload",
                    files=files,
                    headers=headers
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Upload successful!")
                print(f"  File: {file_path}")
                print(f"  Response: {result}")
                return True
            else:
                print(f"✗ Upload failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        except FileNotFoundError:
            print(f"✗ File not found: {file_path}")
            return False
        except Exception as e:
            print(f"✗ Upload error: {e}")
            return False


def check_prometheus_metrics():
    """Step 3: Check Prometheus collected metrics"""
    print("\n" + "="*60)
    print("STEP 3: CHECK PROMETHEUS METRICS")
    print("="*60)
    
    try:
        # Query total HTTP requests
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "rag_http_requests_total"}
        )
        
        if response.status_code == 200:
            results = response.json()["data"]["result"]
            print("✓ Prometheus has collected metrics!")
            print(f"  Total metrics found: {len(results)}")
            
            # Show top endpoints
            for metric in results[:5]:
                endpoint = metric["metric"].get("endpoint", "unknown")
                status = metric["metric"].get("status", "unknown")
                value = metric["value"][1]
                print(f"  • {endpoint} [{status}]: {value} requests")
            
            return True
        else:
            print(f"✗ Prometheus query failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Prometheus error: {e}")
        return False


def show_grafana_access():
    """Step 4: Guide to Grafana"""
    print("\n" + "="*60)
    print("STEP 4: VIEW LIVE METRICS IN GRAFANA")
    print("="*60)
    print(f"\n🎯 Open Grafana Dashboard:")
    print(f"   URL: {GRAFANA_URL}")
    print(f"   Login: admin / admin123")
    print(f"\n📊 Navigate to:")
    print(f"   Dashboards → RAG → RAG Monitoring Overview")
    print(f"\n📈 You should see:")
    print(f"   • HTTP Request Throughput (live updates)")
    print(f"   • Average Request Latency")
    print(f"   • HTTP Request Status Rate")
    print(f"   • Upload File Rate")
    print(f"\n💡 Metrics auto-update every 10 seconds")


def main():
    print("\n" + "█"*60)
    print("█  RAG APPLICATION - BACKEND CONNECTION & MONITORING")
    print("█"*60)
    
    # Step 1: Health check
    print("\n" + "="*60)
    print("HEALTH CHECK")
    print("="*60)
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✓ Backend is running!")
            print(f"  Status: {health.get('status')}")
            print(f"  App: {health.get('app')}")
        else:
            print(f"✗ Backend returned: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Cannot connect to backend at {API_URL}")
        print(f"  Error: {e}")
        print(f"\n💡 Fix:")
        print(f"  1. Run: docker compose ps")
        print(f"  2. Ensure backend container is running")
        print(f"  3. Try again")
        return
    
    # Step 2: Create client and login
    client = RAGClient()
    if not client.login():
        print("\n💡 Hint: Default credentials are admin/admin123")
        return
    
    time.sleep(1)
    
    # Step 3: Make a query
    if not client.query("What documents do we have in the system?", top_k=3):
        print("⚠️  Query failed, but continuing to show monitoring setup...")
    
    time.sleep(2)
    
    # Step 4: Check Prometheus
    check_prometheus_metrics()
    
    time.sleep(1)
    
    # Step 5: Show Grafana access
    show_grafana_access()
    
    print("\n" + "█"*60)
    print("█  ✓ FLOW COMPLETE - Metrics should be visible in Grafana")
    print("█"*60 + "\n")


if __name__ == "__main__":
    main()
