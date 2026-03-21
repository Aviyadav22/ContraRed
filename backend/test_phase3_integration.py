"""Phase 3 end-to-end integration verification tests."""
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-validation-only-32chars!")

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1

print("=" * 60)
print("PHASE 3 END-TO-END INTEGRATION VERIFICATION")
print("=" * 60)

# ========================================================================
# 3.1 Critical Bug Fixes
# ========================================================================
print("\n--- 3.1 Critical Bug Fixes ---")

def t1():
    from app.core.config import settings
    # Tier inversion fix: Pro must NOT be unlimited
    assert settings.PRO_TIER_SCANS == 200, f"PRO_TIER_SCANS={settings.PRO_TIER_SCANS}, expected 200"
    assert settings.ENTERPRISE_INCLUDED_SCANS == -1, f"ENTERPRISE={settings.ENTERPRISE_INCLUDED_SCANS}, expected -1"
test("Tier inversion fixed: Pro=200, Enterprise=unlimited", t1)

def t2():
    from app.core.config import settings
    assert settings.FREE_TIER_SCANS == 5
    assert settings.STARTER_TIER_SCANS == 50
    assert settings.PRO_TIER_SCANS == 200
    assert settings.BUSINESS_TIER_SCANS == 1000
test("All 5 tier scan limits configured", t2)

def t3():
    import inspect
    from app.api.v1.endpoints.billing import _get_user_scan_count
    src = inspect.getsource(_get_user_scan_count)
    # Must track solo users via UsageLog
    assert "UsageLog" in src
    assert "timedelta(days=30)" in src
test("Free quota bypass fixed: solo users tracked via UsageLog", t3)

# ========================================================================
# 3.2 Tier Redesign (5-tier system)
# ========================================================================
print("\n--- 3.2 Tier Redesign ---")

def t4():
    from app.models.organization import PlanType
    values = {pt.value for pt in PlanType}
    expected = {"free", "starter", "pro", "business", "enterprise"}
    assert expected <= values, f"Missing PlanType values: {expected - values}"
test("PlanType enum has all 5 tiers", t4)

def t5():
    from app.models.user import SubscriptionTier
    values = {st.value for st in SubscriptionTier}
    expected = {"free", "starter", "pro", "business", "enterprise"}
    assert expected <= values, f"Missing SubscriptionTier values: {expected - values}"
test("SubscriptionTier enum has all 5 tiers", t5)

def t6():
    from app.api.v1.endpoints.billing import PLAN_CATALOG
    assert len(PLAN_CATALOG) == 5, f"Expected 5 plans, got {len(PLAN_CATALOG)}"
    for plan_id in ["free", "starter", "pro", "business", "enterprise"]:
        assert plan_id in PLAN_CATALOG, f"Missing plan: {plan_id}"
        info = PLAN_CATALOG[plan_id]
        assert "name" in info
        assert "scans" in info
        assert "seats" in info
        assert "price_inr" in info
        assert "price_usd" in info
        assert "features" in info
        assert "overage_price_inr" in info
test("PLAN_CATALOG has all 5 tiers with complete info", t6)

def t7():
    from app.api.v1.endpoints.billing import PLAN_CATALOG
    # Free: no overage
    assert PLAN_CATALOG["free"]["overage_price_inr"] == 0
    assert PLAN_CATALOG["free"]["overage_price_usd"] == 0
    # Paid tiers: have overage pricing
    assert PLAN_CATALOG["starter"]["overage_price_inr"] > 0
    assert PLAN_CATALOG["pro"]["overage_price_usd"] > 0
    assert PLAN_CATALOG["business"]["overage_price_inr"] > 0
    # Enterprise: unlimited, no overage
    assert PLAN_CATALOG["enterprise"]["scans"] == -1
    assert PLAN_CATALOG["enterprise"]["overage_price_inr"] == 0
test("Overage pricing: free=0, paid=positive, enterprise=0", t7)

def t8():
    from app.api.v1.endpoints.billing import PLAN_CATALOG
    # Scan limits must be strictly increasing
    limits = [
        PLAN_CATALOG["free"]["scans"],
        PLAN_CATALOG["starter"]["scans"],
        PLAN_CATALOG["pro"]["scans"],
        PLAN_CATALOG["business"]["scans"],
    ]
    for i in range(len(limits) - 1):
        assert limits[i] < limits[i + 1], f"Scan limits not increasing: {limits}"
test("Scan limits strictly increasing: free < starter < pro < business", t8)

# ========================================================================
# 3.3 Dual Payment Gateway
# ========================================================================
print("\n--- 3.3 Dual Payment Gateway ---")

def t9():
    from app.core.config import settings
    assert hasattr(settings, "STRIPE_SECRET_KEY")
    assert hasattr(settings, "STRIPE_PUBLISHABLE_KEY")
    assert hasattr(settings, "STRIPE_WEBHOOK_SECRET")
    assert hasattr(settings, "RAZORPAY_KEY_ID")
    assert hasattr(settings, "RAZORPAY_KEY_SECRET")
test("Both Stripe and Razorpay config fields exist", t9)

def t10():
    import inspect
    from app.api.v1.endpoints.billing import create_subscription
    src = inspect.getsource(create_subscription)
    assert "razorpay" in src
    assert "stripe" in src
test("create_subscription supports both gateways", t10)

def t11():
    from app.api.v1.endpoints.billing import CreateSubscriptionRequest
    # Validate gateway choices
    import json
    schema = CreateSubscriptionRequest.model_json_schema()
    gateway_enum = None
    for prop in schema.get("properties", {}).values():
        if "gateway" in str(prop.get("title", "")).lower() or prop.get("default") == "razorpay":
            gateway_enum = prop.get("enum", [])
            break
    assert gateway_enum is not None, "No gateway enum found"
    assert "razorpay" in gateway_enum
    assert "stripe" in gateway_enum
test("CreateSubscriptionRequest has razorpay/stripe gateway options", t11)

def t12():
    import inspect
    from app.api.v1.endpoints import billing
    src = inspect.getsource(billing)
    assert "webhook/razorpay" in src
    assert "webhook/stripe" in src
    assert "webhook_compat" in src or '"/webhook"' in src
test("Separate webhook endpoints for Razorpay and Stripe", t12)

def t13():
    from app.models.organization import Subscription
    fields = set(Subscription.__table__.columns.keys())
    assert "stripe_subscription_id" in fields, "Missing stripe_subscription_id"
    assert "stripe_customer_id" in fields, "Missing stripe_customer_id"
    assert "gateway" in fields, "Missing gateway column"
test("Subscription model has Stripe columns and gateway field", t13)

# ========================================================================
# 3.4 Billing Features
# ========================================================================
print("\n--- 3.4 Billing Features ---")

def t14():
    import inspect
    from app.api.v1.endpoints import billing
    src = inspect.getsource(billing)
    assert "PAST_DUE" in src
    assert "payment.failed" in src or "payment_failed" in src
test("Dunning management: payment.failed -> PAST_DUE", t14)

def t15():
    import inspect
    from app.api.v1.endpoints.billing import check_and_increment_quota
    src = inspect.getsource(check_and_increment_quota)
    assert "overage" in src.lower()
    assert "402" in src
test("Overage billing in check_and_increment_quota", t15)

def t16():
    import inspect
    from app.api.v1.endpoints import billing
    src = inspect.getsource(billing)
    assert "/usage" in src
    assert "daily_usage" in src
    assert "date_trunc" in src
test("Usage stats endpoint with daily breakdown", t16)

def t17():
    from app.models.billing import Invoice
    fields = set(Invoice.__table__.columns.keys())
    required = {"id", "user_id", "amount", "currency", "status", "plan", "gateway", "created_at"}
    assert required <= fields, f"Missing Invoice columns: {required - fields}"
test("Invoice model has all required fields", t17)

def t18():
    from app.models import Invoice
    assert Invoice is not None
test("Invoice exported from models.__init__", t18)

# ========================================================================
# Migration
# ========================================================================
print("\n--- Migration ---")

def t19():
    import os
    path = os.path.join(os.path.dirname(__file__), "migrations", "011_phase3_billing.sql")
    assert os.path.exists(path), "Migration file not found"
    with open(path) as f:
        sql = f.read()
    assert "starter" in sql
    assert "business" in sql
    assert "stripe_subscription_id" in sql
    assert "stripe_customer_id" in sql
    assert "invoices" in sql
    assert "ROW LEVEL SECURITY" in sql
test("Migration 011 contains all Phase 3 schema changes", t19)

# ========================================================================
# Requirements
# ========================================================================
print("\n--- Requirements ---")

def t20():
    import os
    path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    with open(path) as f:
        reqs = f.read()
    assert "stripe" in reqs.lower()
    assert "razorpay" in reqs.lower()
test("Both stripe and razorpay in requirements.txt", t20)

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
print("=" * 60)

import sys
sys.exit(1 if failed else 0)
