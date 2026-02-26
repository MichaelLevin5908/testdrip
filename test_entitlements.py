"""
test_entitlements.py — Full entitlement system E2E test against production.

Tests the complete entitlement lifecycle:
  1.  POST   /entitlement-plans          — Create a plan
  2.  GET    /entitlement-plans           — List plans
  3.  GET    /entitlement-plans/:id       — Get a specific plan
  4.  PATCH  /entitlement-plans/:id       — Update a plan
  5.  POST   /entitlement-plans/:id/rules — Add rules to a plan
  6.  GET    /entitlement-plans/:id/rules — List rules for a plan
  7.  PATCH  /entitlement-rules/:ruleId   — Update a rule
  8.  PUT    /customers/:id/entitlement   — Assign plan to customer
  9.  GET    /customers/:id/entitlement   — Get customer entitlement + usage
  10. POST   /entitlements/check          — Check entitlement (allowed)
  11. POST   /entitlements/check          — Check entitlement (denied - over quota)
  12. GET    /customers/:id/entitlement/usage — Get usage summary
  13. DELETE /entitlement-rules/:ruleId   — Delete a rule
  14. DELETE /entitlement-plans/:id       — Soft-delete a plan
  15. POST   /entitlement-plans (409)     — Duplicate slug returns 409
"""

import httpx
import uuid
import sys

# ── Config ──────────────────────────────────────────────────────────────────
API_KEY = "pk_live_ba96b6e6-95d2-4969-baf3-ab117b5c0bb7"
BASE_URL = "https://drip-app-hlunj.ondigitalocean.app/v1"
CUSTOMER_ID = "cmm3eut3b0001ew6l0ivjabgh"  # existing provisioned customer

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

RUN_ID = uuid.uuid4().hex[:8]

passed = 0
failed = 0
results: list[tuple[str, bool, str]] = []


def test(name: str, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        results.append((name, True, ""))
        print(f"  ✅ {name}")
    except Exception as e:
        failed += 1
        results.append((name, False, str(e)))
        print(f"  ❌ {name}: {e}")


def api(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{BASE_URL}{path}"
    return httpx.request(method, url, headers=HEADERS, timeout=30, **kwargs)


# ── State (populated during tests) ─────────────────────────────────────────
plan_id: str = ""
rule_id_search: str = ""
rule_id_tokens: str = ""
plan_slug = f"test-plan-{RUN_ID}"


# ── Tests ───────────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print(f"  ENTITLEMENT E2E TESTS  (run_id={RUN_ID})")
print(f"{'='*60}\n")


# --- 1. Create entitlement plan ---
def t01_create_plan():
    global plan_id
    r = api("POST", "/entitlement-plans", json={
        "name": f"Test Plan {RUN_ID}",
        "slug": plan_slug,
        "description": "E2E test plan for entitlement system",
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    plan_id = body["id"]
    assert body["name"] == f"Test Plan {RUN_ID}"
    assert body["slug"] == plan_slug
    assert body["isActive"] is True
    assert body["isDefault"] is False

test("1. Create entitlement plan", t01_create_plan)


# --- 2. List entitlement plans ---
def t02_list_plans():
    r = api("GET", "/entitlement-plans")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert "data" in body
    assert "count" in body
    assert body["count"] >= 1
    slugs = [p["slug"] for p in body["data"]]
    assert plan_slug in slugs, f"Plan slug '{plan_slug}' not in list: {slugs}"

test("2. List entitlement plans", t02_list_plans)


# --- 3. Get specific plan ---
def t03_get_plan():
    r = api("GET", f"/entitlement-plans/{plan_id}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["id"] == plan_id
    assert body["slug"] == plan_slug

test("3. Get specific plan", t03_get_plan)


# --- 4. Update plan ---
def t04_update_plan():
    r = api("PATCH", f"/entitlement-plans/{plan_id}", json={
        "description": "Updated description for E2E test",
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["description"] == "Updated description for E2E test"

test("4. Update plan (PATCH)", t04_update_plan)


# --- 5. Add rule: search (DAILY, COUNT, limit 100) ---
def t05_add_rule_search():
    global rule_id_search
    r = api("POST", f"/entitlement-plans/{plan_id}/rules", json={
        "featureKey": "search",
        "limitType": "COUNT",
        "period": "DAILY",
        "limitValue": 100,
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    rule_id_search = body["id"]
    assert body["featureKey"] == "search"
    assert body["limitValue"] == "100"
    assert body["period"] == "DAILY"

test("5. Add rule: search (DAILY, 100)", t05_add_rule_search)


# --- 6. Add rule: tokens (MONTHLY, COUNT, limit 50000) ---
def t06_add_rule_tokens():
    global rule_id_tokens
    r = api("POST", f"/entitlement-plans/{plan_id}/rules", json={
        "featureKey": "tokens",
        "limitType": "COUNT",
        "period": "MONTHLY",
        "limitValue": 50000,
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    rule_id_tokens = body["id"]
    assert body["featureKey"] == "tokens"
    assert body["limitValue"] == "50000"

test("6. Add rule: tokens (MONTHLY, 50000)", t06_add_rule_tokens)


# --- 7. List rules for plan ---
def t07_list_rules():
    r = api("GET", f"/entitlement-plans/{plan_id}/rules")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["count"] == 2
    keys = sorted([r["featureKey"] for r in body["data"]])
    assert keys == ["search", "tokens"], f"Expected ['search', 'tokens'], got {keys}"

test("7. List rules for plan", t07_list_rules)


# --- 8. Update rule (increase search limit to 500) ---
def t08_update_rule():
    r = api("PATCH", f"/entitlement-rules/{rule_id_search}", json={
        "limitValue": 500,
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["limitValue"] == "500"

test("8. Update rule (search limit → 500)", t08_update_rule)


# --- 9. Assign plan to customer ---
def t09_assign_plan():
    r = api("PUT", f"/customers/{CUSTOMER_ID}/entitlement", json={
        "planId": plan_id,
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["customerId"] == CUSTOMER_ID
    assert body["planId"] == plan_id
    assert "assigned" in body.get("message", "").lower() or "plan" in body.get("message", "").lower()

test("9. Assign plan to customer", t09_assign_plan)


# --- 10. Get customer entitlement ---
def t10_get_customer_entitlement():
    r = api("GET", f"/customers/{CUSTOMER_ID}/entitlement")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["customerId"] == CUSTOMER_ID
    assert body["plan"]["id"] == plan_id
    assert body["plan"]["slug"] == plan_slug

test("10. Get customer entitlement", t10_get_customer_entitlement)


# --- 11. Check entitlement: allowed ---
def t11_check_entitlement_allowed():
    r = api("POST", "/entitlements/check", json={
        "customerId": CUSTOMER_ID,
        "featureKey": "search",
        "quantity": 1,
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["allowed"] is True, f"Expected allowed=true, got: {body}"
    assert body["featureKey"] == "search"
    assert "remaining" in body
    assert "limit" in body

test("11. Check entitlement: allowed", t11_check_entitlement_allowed)


# --- 12. Check entitlement: feature with no rule (should be allowed/unlimited) ---
def t12_check_no_rule_feature():
    r = api("POST", "/entitlements/check", json={
        "customerId": CUSTOMER_ID,
        "featureKey": "nonexistent_feature",
        "quantity": 1,
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["allowed"] is True, f"Expected allowed=true for undefined feature, got: {body}"
    assert body["unlimited"] is True

test("12. Check entitlement: no-rule feature (unlimited)", t12_check_no_rule_feature)


# --- 13. Get customer entitlement usage ---
def t13_get_usage_summary():
    r = api("GET", f"/customers/{CUSTOMER_ID}/entitlement/usage")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["customerId"] == CUSTOMER_ID
    assert "usage" in body
    assert isinstance(body["usage"], list)

test("13. Get customer entitlement usage", t13_get_usage_summary)


# --- 14. Assign plan with overrides ---
def t14_assign_with_overrides():
    r = api("PUT", f"/customers/{CUSTOMER_ID}/entitlement", json={
        "planId": plan_id,
        "overrides": {
            "search": {"dailyLimit": 10000},
        },
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["overrides"] is not None
    assert body["overrides"]["search"]["dailyLimit"] == 10000

test("14. Assign plan with overrides", t14_assign_with_overrides)


# --- 15. Verify override reflected in entitlement check ---
def t15_check_with_override():
    r = api("POST", "/entitlements/check", json={
        "customerId": CUSTOMER_ID,
        "featureKey": "search",
        "quantity": 1,
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["allowed"] is True
    # Override should bump limit to 10000 (from 500)
    assert body["limit"] == 10000, f"Expected limit=10000 with override, got {body['limit']}"

test("15. Check entitlement with override (limit=10000)", t15_check_with_override)


# --- 16. Duplicate slug returns 409 ---
def t16_duplicate_slug():
    r = api("POST", "/entitlement-plans", json={
        "name": "Duplicate Plan",
        "slug": plan_slug,
    })
    assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("code") == "DUPLICATE_PLAN"

test("16. Duplicate slug returns 409", t16_duplicate_slug)


# --- 17. Duplicate rule returns 409 ---
def t17_duplicate_rule():
    r = api("POST", f"/entitlement-plans/{plan_id}/rules", json={
        "featureKey": "search",
        "limitType": "COUNT",
        "period": "DAILY",
        "limitValue": 200,
    })
    assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("code") == "DUPLICATE_RULE"

test("17. Duplicate rule returns 409", t17_duplicate_rule)


# --- 18. Check entitlement: nonexistent customer → 404 ---
def t18_check_bad_customer():
    r = api("POST", "/entitlements/check", json={
        "customerId": "cust_does_not_exist_99999",
        "featureKey": "search",
    })
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

test("18. Check entitlement: bad customer → 404", t18_check_bad_customer)


# --- 19. Get entitlement: nonexistent customer → 404 ---
def t19_get_entitlement_bad_customer():
    r = api("GET", "/customers/cust_does_not_exist_99999/entitlement")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

test("19. Get entitlement: bad customer → 404", t19_get_entitlement_bad_customer)


# --- 20. Delete rule ---
def t20_delete_rule():
    r = api("DELETE", f"/entitlement-rules/{rule_id_tokens}")
    assert r.status_code == 204, f"Expected 204, got {r.status_code}: {r.text}"
    # Verify it's gone
    r2 = api("GET", f"/entitlement-plans/{plan_id}/rules")
    body = r2.json()
    assert body["count"] == 1, f"Expected 1 rule after delete, got {body['count']}"

test("20. Delete rule (tokens)", t20_delete_rule)


# --- 21. Delete (deactivate) plan ---
def t21_delete_plan():
    r = api("DELETE", f"/entitlement-plans/{plan_id}")
    assert r.status_code == 204, f"Expected 204, got {r.status_code}: {r.text}"
    # Verify it's deactivated (not fully deleted)
    r2 = api("GET", f"/entitlement-plans/{plan_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["isActive"] is False, f"Expected isActive=false after delete, got {body['isActive']}"

test("21. Soft-delete plan (deactivate)", t21_delete_plan)


# --- 22. Delete nonexistent plan → 404 ---
def t22_delete_nonexistent_plan():
    r = api("DELETE", "/entitlement-plans/plan_does_not_exist")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

test("22. Delete nonexistent plan → 404", t22_delete_nonexistent_plan)


# --- 23. Delete nonexistent rule → 404 ---
def t23_delete_nonexistent_rule():
    r = api("DELETE", "/entitlement-rules/rule_does_not_exist")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

test("23. Delete nonexistent rule → 404", t23_delete_nonexistent_rule)


# ── Summary ─────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RESULTS: {passed}/{passed+failed} passed")
print(f"{'='*60}")

if failed:
    print("\n  FAILURES:")
    for name, ok, err in results:
        if not ok:
            print(f"    ❌ {name}: {err}")
    print()

sys.exit(0 if failed == 0 else 1)
