# P14 production conduction contract

Authority is conserved across signed Trust, explicit request and proposal. The
original audit ledger identifies the pre-signing audit stage and remains immutable.
`trust_final_issuance_identity` maps that stage through the same tenant/audit/attempt
to the retained final signed artifact. It exposes both identities explicitly; no
provisional identity is represented as a final artifact hash.

Tenant policy is operator configuration, not model output or a machine caller's
scope. The supported deployment command is `python -m app.trust.policy_configuration`
in the production image, using the separately held `TRUST_POLICY_ADMIN_DATABASE_URL`
credential for `app_trust_policy_admin`. This principal belongs to no runtime role.
Only this deployment principal may append tenant policy decisions, with an approval
reference. It has no financial, signing, request or solver write authority. Its
credential must never be delivered to API, signer, workers or LLM processes.
The authenticated database principal is the recorded publisher; an approval
reference records the operator's supplied reference, not independent proof of a
human approval event. Missing configuration means `read_only`. Every one of
`blocked`, `read_only`, `simulation_only`, `proposal_required`, `approval_required`
is typed. None grants platform execution. Current policy may restrict old Trust;
it may never raise the authority of an old Trust.

The production HTTP consumer uses machine authentication, tenant binding,
X-Correlation-ID and a single-use X-Trust-Nonce. POST `/api/trust/v1/simulations`
accepts only a final envelope identifier, an integer budget, and a request reference.
The server resolves retained issuance and derives channel evidence from verified
allocations for that Trust's fit window and currency. Client-authored evidence,
policy, requester identities and result allocations are not request inputs.
GET `/api/trust/v1/simulations/{request_id}` returns durable request status, result
and proposal without writing authority. Foreign-tenant identifiers return 404.
Results describe deterministic what-if consequences, never counterfactual lift.
Proposals always require human review and cannot execute on an external platform.

Possession freshness uses elapsed wall-clock time at authentication and consumption.
`authenticated_at`, `requested_at` and consequence `created_at` record database
wall-clock row construction, not transaction start or commit. The 900-second limit
is not configurable by a request. Commit time is not claimed.

Production readiness compares authority-bearing catalog state to a manifest shipped
in the image, in addition to checking the migration revision. Functions, constraints,
triggers, RLS policies, owners, grants and runtime role memberships are covered.
The manifest is constructed from migration replay, reviewed with source changes,
and is never learned from the serving database at startup.
