"""Canonical tenant-scoped Billing V1 service for ONE NINA."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

import persistence_backend


PLAN_TABLE = "nina_billing_plans"
ENTITLEMENT_TABLE = "nina_billing_plan_entitlements"
SUBSCRIPTION_TABLE = "nina_workspace_subscriptions"
OVERRIDE_TABLE = "nina_workspace_entitlement_overrides"
COUNTER_TABLE = "nina_billing_usage_counters"
USAGE_TABLE = "nina_billing_usage_events"
EVENT_TABLE = "nina_billing_events"
CUSTOMER_TABLE = "nina_billing_customers"
INVOICE_TABLE = "nina_billing_invoices"
REQUIRED_TABLES = frozenset({PLAN_TABLE, ENTITLEMENT_TABLE, SUBSCRIPTION_TABLE,
    OVERRIDE_TABLE, COUNTER_TABLE, USAGE_TABLE, EVENT_TABLE, CUSTOMER_TABLE,
    INVOICE_TABLE})


class BillingError(RuntimeError): pass
class BillingValidationError(BillingError): pass
class BillingLimitError(BillingError): pass


def _sql(value): return persistence_backend.sql(value)
def _now(): return datetime.now(timezone.utc).isoformat()
def _id(value, field="id"):
    value = str(value or "").strip()
    if not value or len(value) > 128 or not all(c.isalnum() or c in "_.:-" for c in value):
        raise BillingValidationError(f"billing_{field}_invalid")
    return value


def _event(cur, workspace_id, event_type, actor, data=None):
    cur.execute(_sql(f"INSERT INTO {EVENT_TABLE} (event_id,workspace_id,event_type,actor,safe_metadata,created_at) VALUES (%s,%s,%s,%s,%s,%s)"),
        ("billing_event_" + secrets.token_hex(16), workspace_id, event_type,
         _id(actor, "actor"), json.dumps(data or {}, sort_keys=True), _now()))


def list_plans(public_only=False):
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        where = " WHERE is_public=1" if public_only else ""
        cur.execute(f"SELECT plan_id,code,display_name,description,status,version,is_public,price_minor,currency,billing_period,created_at,updated_at FROM {PLAN_TABLE}{where} ORDER BY price_minor,code")
        rows = cur.fetchall() or []
        cur.close()
        return tuple({"plan_id": r[0], "code": r[1], "display_name": r[2], "description": r[3], "status": r[4], "version": r[5], "is_public": bool(r[6]), "price_minor": r[7], "currency": r[8], "billing_period": r[9], "created_at": r[10], "updated_at": r[11]} for r in rows)
    finally: conn.close()


def get_plan(plan_id):
    identifier = _id(plan_id, "plan_id")
    return next((p for p in list_plans() if p["plan_id"] == identifier or p["code"] == identifier), None)


def create_plan(code, display_name, *, description="", price_minor=0,
                currency="EUR", billing_period="month", is_public=True,
                actor="platform_admin"):
    code = _id(code, "plan_code"); display_name = str(display_name or "").strip()
    if not display_name or len(display_name) > 200: raise BillingValidationError("billing_display_name_invalid")
    plan_id = "plan_" + secrets.token_hex(12); now = _now()
    conn = persistence_backend.connect()
    try:
        cur=conn.cursor(); cur.execute(_sql(f"INSERT INTO {PLAN_TABLE} (plan_id,code,display_name,description,status,version,is_public,price_minor,currency,billing_period,created_at,updated_at) VALUES (%s,%s,%s,%s,'active',1,%s,%s,%s,%s,%s,%s)"), (plan_id,code,display_name,str(description)[:1000],1 if is_public else 0,int(price_minor),_id(currency,"currency").upper(),_id(billing_period,"billing_period"),now,now))
        _event(cur,"platform","plan_created",actor,{"plan_id":plan_id}); conn.commit(); cur.close(); return get_plan(plan_id)
    except Exception: conn.rollback(); raise
    finally: conn.close()


def update_plan(plan_id, *, display_name=None, description=None, status=None,
                is_public=None, price_minor=None, actor="platform_admin"):
    plan=get_plan(plan_id)
    if not plan: raise BillingValidationError("billing_plan_not_found")
    values={"display_name":display_name,"description":description,"status":status,"is_public":None if is_public is None else (1 if is_public else 0),"price_minor":price_minor}
    allowed={"active","inactive"}
    if status is not None and status not in allowed: raise BillingValidationError("billing_plan_status_invalid")
    fields=[]; params=[]
    for key,value in values.items():
        if value is not None: fields.append(f"{key}=%s"); params.append(value)
    fields.extend(["version=version+1","updated_at=%s"]); params.extend([_now(),plan["plan_id"]])
    conn=persistence_backend.connect()
    try:
        cur=conn.cursor(); cur.execute(_sql(f"UPDATE {PLAN_TABLE} SET {','.join(fields)} WHERE plan_id=%s"),tuple(params)); _event(cur,"platform","plan_updated",actor,{"plan_id":plan["plan_id"]}); conn.commit(); cur.close(); return get_plan(plan["plan_id"])
    except Exception: conn.rollback(); raise
    finally: conn.close()


def set_plan_entitlement(plan_id, key, value, actor="platform_admin"):
    plan=get_plan(plan_id); key=_id(key,"entitlement_key")
    if not plan: raise BillingValidationError("billing_plan_not_found")
    conn=persistence_backend.connect(); now=_now()
    try:
        cur=conn.cursor(); cur.execute(_sql(f"SELECT entitlement_id FROM {ENTITLEMENT_TABLE} WHERE plan_id=%s AND entitlement_key=%s"),(plan["plan_id"],key)); row=cur.fetchone()
        if row: cur.execute(_sql(f"UPDATE {ENTITLEMENT_TABLE} SET value_json=%s,updated_at=%s WHERE entitlement_id=%s"),(json.dumps(value),now,row[0]))
        else: cur.execute(_sql(f"INSERT INTO {ENTITLEMENT_TABLE} (entitlement_id,plan_id,entitlement_key,value_json,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s)"),("entitlement_"+secrets.token_hex(16),plan["plan_id"],key,json.dumps(value),now,now))
        _event(cur,"platform","plan_entitlement_set",actor,{"plan_id":plan["plan_id"],"entitlement_key":key}); conn.commit(); cur.close()
    except Exception: conn.rollback(); raise
    finally: conn.close()


def get_plan_entitlements(plan_id):
    plan = get_plan(plan_id)
    if not plan: raise BillingValidationError("billing_plan_not_found")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor(); cur.execute(_sql(f"SELECT entitlement_key,value_json FROM {ENTITLEMENT_TABLE} WHERE plan_id=%s"), (plan["plan_id"],))
        result = {str(k): json.loads(v) for k, v in (cur.fetchall() or [])}; cur.close(); return result
    finally: conn.close()


def _legacy_subscription(workspace_id, actor="system"):
    workspace = _id(workspace_id, "workspace_id")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor(); cur.execute(_sql(f"SELECT subscription_id,plan_id,status,source,started_at,ends_at FROM {SUBSCRIPTION_TABLE} WHERE workspace_id=%s AND status='active' LIMIT 1"), (workspace,)); row = cur.fetchone()
        if not row:
            now = _now(); sid = "subscription_" + secrets.token_hex(16)
            cur.execute(_sql(f"INSERT INTO {SUBSCRIPTION_TABLE} (subscription_id,workspace_id,plan_id,status,source,started_at,ends_at,created_at,updated_at) VALUES (%s,%s,'plan_legacy','active','grandfathered',%s,'',%s,%s)"), (sid, workspace, now, now, now))
            _event(cur, workspace, "legacy_compatibility_assigned", actor, {"plan_id": "plan_legacy"}); conn.commit()
            row = (sid, "plan_legacy", "active", "grandfathered", now, "")
        cur.close(); return {"subscription_id": row[0], "workspace_id": workspace, "plan_id": row[1], "status": row[2], "source": row[3], "started_at": row[4], "ends_at": row[5]}
    except Exception: conn.rollback(); raise
    finally: conn.close()


def get_workspace_subscription(workspace_id): return _legacy_subscription(workspace_id)
def get_workspace_plan(workspace_id): return get_plan(get_workspace_subscription(workspace_id)["plan_id"])


def change_workspace_plan(workspace_id, plan_id, actor="platform_admin"):
    workspace = _id(workspace_id, "workspace_id"); plan = get_plan(plan_id)
    if not plan or plan["status"] != "active": raise BillingValidationError("billing_plan_unavailable")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor(); now = _now()
        cur.execute(_sql(f"UPDATE {SUBSCRIPTION_TABLE} SET status='replaced',updated_at=%s WHERE workspace_id=%s AND status='active'"), (now, workspace))
        sid = "subscription_" + secrets.token_hex(16)
        cur.execute(_sql(f"INSERT INTO {SUBSCRIPTION_TABLE} (subscription_id,workspace_id,plan_id,status,source,started_at,ends_at,created_at,updated_at) VALUES (%s,%s,%s,'active','manual',%s,'',%s,%s)"), (sid, workspace, plan["plan_id"], now, now, now))
        _event(cur, workspace, "plan_changed", actor, {"plan_id": plan["plan_id"]}); conn.commit(); cur.close()
        return get_workspace_subscription(workspace)
    except Exception: conn.rollback(); raise
    finally: conn.close()


def _set_subscription_status(workspace_id, status, actor="platform_admin"):
    status = str(status or "").lower()
    if status not in {"trialing","active","past_due","suspended","cancelled","expired","incomplete"}:
        raise BillingValidationError("billing_subscription_status_invalid")
    workspace=_id(workspace_id,"workspace_id"); current=get_workspace_subscription(workspace); now=_now(); conn=persistence_backend.connect()
    try:
        cur=conn.cursor(); cur.execute(_sql(f"UPDATE {SUBSCRIPTION_TABLE} SET status=%s,cancelled_at=%s,updated_at=%s WHERE workspace_id=%s AND subscription_id=%s"),(status,now if status=="cancelled" else "",now,workspace,current["subscription_id"])); _event(cur,workspace,"subscription_status_changed",actor,{"status":status}); conn.commit(); cur.close(); current["status"]=status; return current
    except Exception: conn.rollback(); raise
    finally: conn.close()


def activate_subscription(workspace_id, plan_id=None, actor="platform_admin"):
    if plan_id: return change_workspace_plan(workspace_id, plan_id, actor)
    return _set_subscription_status(workspace_id,"active",actor)
def suspend_subscription(workspace_id, actor="platform_admin"): return _set_subscription_status(workspace_id,"suspended",actor)
def cancel_subscription(workspace_id, actor="platform_admin"): return _set_subscription_status(workspace_id,"cancelled",actor)


def set_override(workspace_id, key, value, actor="platform_admin", expires_at=""):
    workspace = _id(workspace_id, "workspace_id"); key = _id(key, "entitlement_key"); now = _now()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor(); cur.execute(_sql(f"UPDATE {OVERRIDE_TABLE} SET active=0,updated_at=%s WHERE workspace_id=%s AND entitlement_key=%s AND active=1"), (now, workspace, key))
        oid = "override_" + secrets.token_hex(16)
        cur.execute(_sql(f"INSERT INTO {OVERRIDE_TABLE} (override_id,workspace_id,entitlement_key,value_json,active,expires_at,created_by,created_at,updated_at) VALUES (%s,%s,%s,%s,1,%s,%s,%s,%s)"), (oid, workspace, key, json.dumps(value), str(expires_at or ""), _id(actor, "actor"), now, now))
        _event(cur, workspace, "entitlement_override_set", actor, {"entitlement_key": key}); conn.commit(); cur.close(); return oid
    except Exception: conn.rollback(); raise
    finally: conn.close()


def deactivate_override(workspace_id, key, actor="platform_admin"):
    workspace=_id(workspace_id,"workspace_id"); key=_id(key,"entitlement_key"); conn=persistence_backend.connect()
    try:
        cur=conn.cursor(); cur.execute(_sql(f"UPDATE {OVERRIDE_TABLE} SET active=0,updated_at=%s WHERE workspace_id=%s AND entitlement_key=%s AND active=1"),(_now(),workspace,key)); changed=cur.rowcount
        if changed: _event(cur,workspace,"entitlement_override_deactivated",actor,{"entitlement_key":key})
        conn.commit(); cur.close(); return bool(changed)
    except Exception: conn.rollback(); raise
    finally: conn.close()


def get_effective_entitlements(workspace_id):
    workspace = _id(workspace_id, "workspace_id"); subscription = get_workspace_subscription(workspace)
    result = get_plan_entitlements(subscription["plan_id"])
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor(); cur.execute(_sql(f"SELECT entitlement_key,value_json,expires_at FROM {OVERRIDE_TABLE} WHERE workspace_id=%s AND active=1 ORDER BY created_at"), (workspace,))
        now = _now()
        for key, value, expiry in (cur.fetchall() or []):
            if not expiry or str(expiry) > now: result[str(key)] = json.loads(value)
        cur.close()
    finally: conn.close()
    return result


def check_entitlement(workspace_id, key): return bool(get_effective_entitlements(workspace_id).get(_id(key, "entitlement_key"), False))
def get_effective_entitlement(workspace_id, key): return get_effective_entitlements(workspace_id).get(_id(key,"entitlement_key"))
def list_effective_entitlements(workspace_id): return get_effective_entitlements(workspace_id)
def has_entitlement(workspace_id, key): return check_entitlement(workspace_id, key)
def get_limit(workspace_id, key):
    value=get_effective_entitlement(workspace_id,key)
    return value if isinstance(value,(int,float)) or value=="unlimited" else 0
def require_entitlement(workspace_id, key):
    if not has_entitlement(workspace_id,key):
        raise BillingLimitError("billing_entitlement_required")
    return True


def get_usage(workspace_id, metric, period_start, period_end):
    workspace = _id(workspace_id, "workspace_id"); metric = _id(metric, "metric")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor(); cur.execute(_sql(f"SELECT quantity FROM {COUNTER_TABLE} WHERE workspace_id=%s AND metric=%s AND period_start=%s AND period_end=%s"), (workspace, metric, period_start, period_end)); row=cur.fetchone(); cur.close(); return int(row[0]) if row else 0
    finally: conn.close()


def record_usage(workspace_id, metric, quantity=1, idempotency_key=None, period_start="all", period_end="all", source_type="system", source_id="", unit="count"):
    workspace = _id(workspace_id, "workspace_id"); metric = _id(metric, "metric"); idem = _id(idempotency_key or ("usage_" + secrets.token_hex(12)), "idempotency_key")
    quantity = int(quantity)
    if quantity <= 0: raise BillingValidationError("billing_quantity_invalid")
    conn = persistence_backend.connect()
    try:
        cur=conn.cursor()
        event_id="usage_"+secrets.token_hex(16); now=_now()
        cur.execute(_sql(f"INSERT INTO {USAGE_TABLE} (usage_event_id,workspace_id,metric,quantity,unit,source_type,source_id,idempotency_key,occurred_at,safe_metadata,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'{{}}',%s) ON CONFLICT (workspace_id,metric,idempotency_key) DO NOTHING"), (event_id,workspace,metric,quantity,_id(unit,"unit"),_id(source_type,"source_type"),str(source_id or "")[:128],idem,now,now))
        if cur.rowcount == 0: conn.rollback(); cur.close(); return {"recorded": False, "quantity": get_usage(workspace, metric, period_start, period_end)}
        cur.execute(_sql(f"INSERT INTO {COUNTER_TABLE} (counter_id,workspace_id,metric,period_start,period_end,quantity,unit,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (workspace_id,metric,period_start,period_end) DO UPDATE SET quantity={COUNTER_TABLE}.quantity+excluded.quantity,updated_at=excluded.updated_at"), ("counter_"+secrets.token_hex(16),workspace,metric,period_start,period_end,quantity,_id(unit,"unit"),now,now))
        conn.commit(); cur.close(); return {"recorded": True, "quantity": get_usage(workspace,metric,period_start,period_end)}
    except Exception: conn.rollback(); raise
    finally: conn.close()


def check_limit(workspace_id, metric, period_start="all", period_end="all"):
    value = get_effective_entitlements(workspace_id).get(f"limit.{_id(metric, 'metric')}")
    used = get_usage(workspace_id, metric, period_start, period_end)
    allowed = value in (None, "unlimited", -1) or used < int(value)
    return {"allowed": allowed, "reason": "allowed" if allowed else "limit_reached", "entitlement_key": f"limit.{metric}", "usage": used, "used": used, "limit": value, "upgrade_required": not allowed}


change_plan = change_workspace_plan
apply_override = set_override
remove_override = deactivate_override


def list_billing_events(workspace_id, limit=100):
    workspace=_id(workspace_id,"workspace_id"); conn=persistence_backend.connect()
    try:
        cur=conn.cursor(); cur.execute(_sql(f"SELECT event_id,event_type,actor,safe_metadata,created_at FROM {EVENT_TABLE} WHERE workspace_id=%s ORDER BY created_at DESC LIMIT %s"),(workspace,min(int(limit),100))); rows=cur.fetchall() or []; cur.close(); return tuple(rows)
    finally: conn.close()


def initialize_billing_service(require_schema=None):
    strict = persistence_backend.HOSTED if require_schema is None else bool(require_schema)
    conn = persistence_backend.connect()
    try:
        cur=conn.cursor()
        if persistence_backend.USE_POSTGRES:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema()")
        else: cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables={str(row[0]) for row in cur.fetchall()}; cur.close()
        return {"ok": REQUIRED_TABLES.issubset(tables) or not strict}
    finally: conn.close()
