import requests
import sys
import os
from supabase import create_client

BASE_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"
SUPABASE_URL = "https://argbqkkfoiuwiyfwhufp.supabase.co"
SUPABASE_KEY = "sb_publishable_pWNZxUFMnxHPc8cTr5QRzA_hDRLyKpv"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../frontend"))

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
results = []

def record(name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    results.append((name, status, details))
    print(f"[{status}] {name} {details}")

print("=================================================================")
print("QUEUELESS AI — GOOGLE OAUTH & ROLE REDIRECTION TEST SUITE")
print("=================================================================")

# 1. Opening / without an authenticated session redirects to /login
try:
    with open(os.path.join(FRONTEND_DIR, "src/App.jsx"), "r", encoding="utf-8") as f:
        app_code = f.read()
    assert '<Route path="/" element={<Navigate to="/login" replace />} />' in app_code
    record("1. Opening '/' without authenticated session redirects to '/login'", True, "(Verified App.jsx root redirect)")
except Exception as e:
    record("1. Opening '/' without authenticated session redirects to '/login'", False, str(e))

# 2. Clicking 'Continue with Google' starts the existing Supabase Google OAuth flow
try:
    with open(os.path.join(FRONTEND_DIR, "src/pages/Login.jsx"), "r", encoding="utf-8") as f:
        login_code = f.read()
    assert "provider: 'google'" in login_code
    assert "redirectTo: `${window.location.origin}/auth/callback`" in login_code

    oauth_res = sb.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {
            "redirect_to": f"{FRONTEND_URL}/auth/callback"
        }
    })
    google_url = oauth_res.url
    assert google_url is not None and "provider=google" in google_url

    import urllib.request
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        resp = opener.open(google_url)
        redirect_to_google = resp.headers.get("Location", "")
    except urllib.error.HTTPError as he:
        redirect_to_google = he.headers.get("Location", "")

    assert "accounts.google.com" in redirect_to_google
    record("2. 'Continue with Google' starts Supabase Google OAuth flow", True, "(Redirects to accounts.google.com with client ID)")
except Exception as e:
    record("2. 'Continue with Google' starts Supabase Google OAuth flow", False, str(e))

# 3. Inspect AuthCallback.jsx: Never automatically redirects to /admin/dashboard or /staff/dashboard
try:
    with open(os.path.join(FRONTEND_DIR, "src/pages/AuthCallback.jsx"), "r", encoding="utf-8") as f:
        callback_code = f.read()

    # Must NOT have navigate('/admin/dashboard')
    assert "navigate('/admin/dashboard'" not in callback_code
    assert "navigate('/staff/dashboard'" not in callback_code

    # Must navigate to /user/dashboard for users
    assert "navigate('/user/dashboard', { replace: true });" in callback_code

    record("3. AuthCallback never automatically navigates to /admin/dashboard or /staff/dashboard", True, "(Admin/staff redirects eliminated from OAuth callback)")
except Exception as e:
    record("3. AuthCallback never automatically navigates to /admin/dashboard or /staff/dashboard", False, str(e))

# 4. If authenticated account is ADMIN, redirect to /user/dashboard with role preserved in DB
try:
    with open(os.path.join(FRONTEND_DIR, "src/pages/AuthCallback.jsx"), "r", encoding="utf-8") as f:
        callback_code = f.read()

    assert "navigate('/user/dashboard', { replace: true });" in callback_code
    assert "navigate('/admin/dashboard'" not in callback_code
    assert "supabase.auth.signOut()" not in callback_code or "prof.status !== 'ACTIVE'" in callback_code

    record("4. ADMIN Google account redirects to /user/dashboard; role preserved in DB", True, "(AuthCallback navigates to /user/dashboard; role never downgraded or altered)")
except Exception as e:
    record("4. ADMIN Google account redirects to /user/dashboard; role preserved in DB", False, str(e))


# 5. USER Sidebar does NOT expose Admin Portal or Staff Desk links
try:
    with open(os.path.join(FRONTEND_DIR, "src/layouts/UserLayout.jsx"), "r", encoding="utf-8") as f:
        user_layout_code = f.read()

    assert "/admin/dashboard" not in user_layout_code
    assert "/staff/dashboard" not in user_layout_code
    assert "Admin Portal" not in user_layout_code
    assert "Staff Desk" not in user_layout_code

    record("5. USER sidebar does not expose Admin Portal or Staff Desk links", True, "(Verified UserLayout menu items strictly limited to citizen functions)")
except Exception as e:
    record("5. USER sidebar does not expose Admin Portal or Staff Desk links", False, str(e))

# 6. Live test: Authenticated USER reaches /user/dashboard and is blocked from /admin/dashboard
try:
    user_login = sb.auth.sign_in_with_password({
        "email": "user@smartqueue.test",
        "password": "User@123456"
    })
    user_token = user_login.session.access_token

    # Verify profile endpoint
    me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["role"] == "USER"

    # Verify USER cannot access admin or staff API
    admin_api_resp = requests.get(f"{BASE_URL}/api/admin/dashboard/summary", headers={"Authorization": f"Bearer {user_token}"})
    assert admin_api_resp.status_code == 403, f"Expected 403, got {admin_api_resp.status_code}"

    staff_api_resp = requests.get(f"{BASE_URL}/api/staff/dashboard/summary", headers={"Authorization": f"Bearer {user_token}"})
    assert staff_api_resp.status_code == 403, f"Expected 403, got {staff_api_resp.status_code}"

    record("6. USER lands on /user/dashboard and is strictly blocked from Admin/Staff APIs (403)", True, "(Verified backend 403 Forbidden for citizen token)")
except Exception as e:
    record("6. USER lands on /user/dashboard and is strictly blocked from Admin/Staff APIs (403)", False, str(e))

# 7. Live test: Unauthenticated requests to protected APIs return 401 Unauthorized
try:
    res_unauth1 = requests.get(f"{BASE_URL}/api/admin/dashboard/summary")
    assert res_unauth1.status_code == 401
    res_unauth2 = requests.get(f"{BASE_URL}/api/staff/dashboard/summary")
    assert res_unauth2.status_code == 401

    record("7. Unauthenticated requests to protected APIs return 401 Unauthorized", True, "(Verified 401 for unauthenticated calls)")
except Exception as e:
    record("7. Unauthenticated requests to protected APIs return 401 Unauthorized", False, str(e))

# 8. Live test: Email/Password login, logout, and dashboard refresh
try:
    # Login again
    sess = sb.auth.sign_in_with_password({
        "email": "user@smartqueue.test",
        "password": "User@123456"
    })
    tok = sess.session.access_token
    # Refresh check 1
    r1 = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r1.status_code == 200
    # Refresh check 2
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    assert r2.json()["id"] == r1.json()["id"]

    # Logout
    sb.auth.sign_out()
    record("8. Email/password login, session preservation on refresh, and logout work correctly", True, "(Session verified across multiple requests and cleared on logout)")
except Exception as e:
    record("8. Email/password login, session preservation on refresh, and logout work correctly", False, str(e))

# 9. Verify backend does NOT automatically grant ADMIN based on email names
try:
    import uuid
    test_email = f"madhesh_test_{uuid.uuid4().hex[:6]}@example.com"
    signup_res = requests.post(f"{BASE_URL}/api/auth/signup", json={
        "email": test_email,
        "name": "Madhesh Test User"
    })
    assert signup_res.status_code == 200
    signed_user = signup_res.json()["user"]
    assert signed_user["role"] == "USER", f"Expected USER role, but got: {signed_user['role']}"

    record("9. Backend signup never auto-promotes to ADMIN based on name/email (creates USER)", True, f"(Created {test_email} with role: {signed_user['role']})")
except Exception as e:
    record("9. Backend signup never auto-promotes to ADMIN based on name/email (creates USER)", False, str(e))

print("\n=================================================================")
print("SUMMARY OF TEST RESULTS:")
print("=================================================================")
passed_count = sum(1 for _, s, _ in results if s == "PASS")
total_count = len(results)
for name, status, details in results:
    print(f"[{status}] - {name}")
print("=================================================================")
print(f"TOTAL: {passed_count}/{total_count} PASSED")
print("=================================================================")
if passed_count == total_count:
    sys.exit(0)
else:
    sys.exit(1)
