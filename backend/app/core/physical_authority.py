"""Compare live authority catalogs to the reviewed production-image manifest."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text

from app.core.construction_authority import ConstructionAuthorityError

MANIFEST_PATH = Path(__file__).resolve().parents[3] / "contracts/trust-api/authority-schema.v1.json"

# Catalog reads require no schema-owner credentials. Object identifiers are
# rendered as names/definitions so independent migration universes compare equal.
CATALOG_SQL = """
WITH relations AS (
 SELECT c.* FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND (c.relname LIKE 'b27_%' OR c.relname LIKE 'b28_%'
 OR c.relname IN ('trust_access_log','trust_issuance_attempts','trust_envelope_issuance_log',
                 'trust_final_issuance_identity','trust_tenant_policy_events'))
 AND c.relkind IN ('r','p','v')
), objects AS (
 SELECT 'relation' AS kind, relname::text AS identity,
 jsonb_build_object('owner',pg_get_userbyid(relowner),'rls',relrowsecurity,
 'force',relforcerowsecurity,'kind',relkind,'acl',
 (SELECT jsonb_agg(v ORDER BY v) FROM unnest(COALESCE(relacl,acldefault('r',relowner))) a,
 LATERAL (SELECT a::text v) s),
 'view',CASE WHEN relkind='v' THEN pg_get_viewdef(oid,true) ELSE NULL END,
 'options',reloptions) AS definition FROM relations
 UNION ALL
 SELECT 'column',r.relname||'.'||a.attname,
 jsonb_build_object('type',format_type(a.atttypid,a.atttypmod),'notnull',a.attnotnull,
 'identity',a.attidentity,'default',pg_get_expr(d.adbin,d.adrelid),'acl',a.attacl::text,
 'semantics',col_description(a.attrelid,a.attnum))
 FROM relations r JOIN pg_attribute a ON a.attrelid=r.oid
 LEFT JOIN pg_attrdef d ON d.adrelid=r.oid AND d.adnum=a.attnum
 WHERE a.attnum>0 AND NOT a.attisdropped
 UNION ALL
 SELECT 'constraint',r.relname||'.'||c.conname,
 jsonb_build_object('definition',pg_get_constraintdef(c.oid,true),'validated',c.convalidated)
 FROM relations r JOIN pg_constraint c ON c.conrelid=r.oid
 UNION ALL
 SELECT 'index',r.relname||'.'||c.relname,
 jsonb_build_object('definition',pg_get_indexdef(i.indexrelid),'valid',i.indisvalid)
 FROM relations r JOIN pg_index i ON i.indrelid=r.oid JOIN pg_class c ON c.oid=i.indexrelid
 UNION ALL
 SELECT 'trigger',r.relname||'.'||t.tgname,
 jsonb_build_object('definition',pg_get_triggerdef(t.oid,true),'enabled',t.tgenabled)
 FROM relations r JOIN pg_trigger t ON t.tgrelid=r.oid WHERE NOT t.tgisinternal
 UNION ALL
 SELECT 'policy',r.relname||'.'||p.polname,
 jsonb_build_object('using',pg_get_expr(p.polqual,p.polrelid),
 'check',pg_get_expr(p.polwithcheck,p.polrelid),'command',p.polcmd,'permissive',p.polpermissive,
 'roles',(SELECT jsonb_agg(CASE WHEN v=0 THEN 'PUBLIC' ELSE pg_get_userbyid(v)::text END ORDER BY v)
 FROM unnest(p.polroles) v)) FROM relations r JOIN pg_policy p ON p.polrelid=r.oid
 UNION ALL
 SELECT 'function',p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
 jsonb_build_object('definition',pg_get_functiondef(p.oid),'owner',pg_get_userbyid(p.proowner),
 'acl',(SELECT jsonb_agg(a::text ORDER BY a::text) FROM unnest(COALESCE(p.proacl,acldefault('f',p.proowner))) a))
 FROM pg_proc p WHERE p.pronamespace='public'::regnamespace AND
 (p.proname LIKE 'b27_%' OR p.proname LIKE 'b28_%' OR p.proname LIKE 'trust_tenant_policy_%'
 OR p.oid IN (SELECT tgfoid FROM pg_trigger WHERE tgrelid IN (SELECT oid FROM relations)))
 UNION ALL
 SELECT 'role',rolname,
 jsonb_build_object('super',rolsuper,'bypassrls',rolbypassrls,'createrole',rolcreaterole,
 'createdb',rolcreatedb,'inherit',rolinherit,
 'memberships',(SELECT jsonb_agg(pg_get_userbyid(roleid) ORDER BY pg_get_userbyid(roleid))
 FROM pg_auth_members WHERE member=pg_roles.oid))
 FROM pg_roles WHERE rolname LIKE 'app_%'
)
SELECT kind,identity,definition FROM objects ORDER BY kind,identity
"""


@lru_cache(maxsize=1)
def expected_authority() -> list:
    """Load only the shipped manifest; never bootstrap trust from the live DB."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["objects"]


async def assert_physical_authority(connection) -> None:
    """Fail readiness when a serving database has lost any covered authority."""
    try:
        rows = await connection.execute(text(CATALOG_SQL))
        observed = [list(row) for row in rows.fetchall()]
        if observed != expected_authority():
            raise ConstructionAuthorityError("database_physical_authority_mismatch")
    except ConstructionAuthorityError:
        raise
    except Exception as exc:
        raise ConstructionAuthorityError("database_physical_authority_unreadable") from exc
