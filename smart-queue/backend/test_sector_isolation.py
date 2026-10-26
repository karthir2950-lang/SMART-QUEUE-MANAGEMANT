import urllib.request
import json

base_url = "http://localhost:8000"
sectors = ["hospital", "bank", "restaurant", "government-office", "retail", "supermarket"]

print("=== SECTOR ISOLATION TEST ===")
for slug in sectors:
    res = urllib.request.urlopen(f"{base_url}/api/sectors/{slug}")
    sec = json.loads(res.read().decode())
    sec_id = sec["id"]
    
    org_res = urllib.request.urlopen(f"{base_url}/api/organizations?sector_id={sec_id}")
    orgs = json.loads(org_res.read().decode())
    
    svc_res = urllib.request.urlopen(f"{base_url}/api/services?sector_id={sec_id}")
    services = json.loads(svc_res.read().decode())
    
    # Assert all returned organizations belong to this sector
    for o in orgs:
        assert o["sector_id"] == sec_id, f"Cross-contamination detected in org {o['name']}"
        
    # Assert all returned services belong to this sector
    for s in services:
        assert s["sector_id"] == sec_id, f"Cross-contamination detected in service {s['name']}"
        
    print(f"PASS: Sector '{sec['name']}' ({slug}) - ID: {sec_id}")
    print(f"      Orgs: {len(orgs)} | Services: {len(services)}")
    if services:
        print(f"      Sample Services: {[s['name'] for s in services[:3]]}")
    print()

print("ALL 6 SECTORS VERIFIED AND ISOLATED!")
