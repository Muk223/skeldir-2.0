-- Recreate fn_enforce_pii_guardrail with table-safe metadata handling
CREATE OR REPLACE FUNCTION public.fn_enforce_pii_guardrail() RETURNS trigger AS $func$
DECLARE
    detected_key TEXT;
    metadata_payload JSONB;
BEGIN
    IF TG_TABLE_NAME IN ('attribution_events', 'dead_events') THEN
        IF fn_detect_pii_keys(NEW.raw_payload) THEN
            SELECT key INTO detected_key
            FROM jsonb_object_keys(NEW.raw_payload) key
            WHERE key IN (
                'email', 'email_address',
                'phone', 'phone_number',
                'ssn', 'social_security_number',
                'ip_address', 'ip',
                'first_name', 'last_name', 'full_name',
                'address', 'street_address'
            )
            LIMIT 1;

            RAISE EXCEPTION 'PII key detected in %.raw_payload. Ingestion blocked by database policy (Layer 2 guardrail). Key found: %. Reference: ADR-003-PII-Defense-Strategy.md. Action: Remove PII key from payload before retry.',
                TG_TABLE_NAME,
                detected_key
            USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'revenue_ledger' THEN
        metadata_payload := to_jsonb(NEW)->'metadata';
        IF metadata_payload IS NOT NULL AND fn_detect_pii_keys(metadata_payload) THEN
            SELECT key INTO detected_key
            FROM jsonb_object_keys(metadata_payload) key
            WHERE key IN (
                'email', 'email_address',
                'phone', 'phone_number',
                'ssn', 'social_security_number',
                'ip_address', 'ip',
                'first_name', 'last_name', 'full_name',
                'address', 'street_address'
            )
            LIMIT 1;

            RAISE EXCEPTION 'PII key detected in revenue_ledger.metadata. Write blocked by database policy (Layer 2 guardrail). Key found: %. Reference: ADR-003-PII-Defense-Strategy.md. Action: Remove PII key from metadata before retry.',
                detected_key
            USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$func$ LANGUAGE plpgsql;

