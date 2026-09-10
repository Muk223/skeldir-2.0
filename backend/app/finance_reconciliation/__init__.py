"""B2.6 semantic authority boundary.

P1 deliberately exports contract identity only. Reconciliation state,
computation, workers, APIs, exports, and TrustEnvelope fields begin in later
dependency-ordered phases.
"""

from .semantic_contract import (
    B26_DISCREPANCY_TAXONOMY_V1,
    B26_KNOWN_AUTHORITY_CLASSES,
    B26_P1_CONTRACT_VERSION,
    B26_P1_SEMANTIC_CONTRACT_PATH,
    B26_P1_SUPERSEDES_VERSION,
    B26_REQUIRED_DISCREPANCY_REASONS,
    B26_REQUIRED_FUTURE_INSERTION_SEAM,
    B26_REQUIRED_SCOPE_DISPOSITIONS,
    B26_REQUIRED_TRUTH_STATE_VOCABULARY,
    B26_SUCCESSOR_STATUS_AUTHORIZED,
    B26_SUCCESSOR_STATUS_NONE,
    SemanticContractError,
    SemanticContractIdentity,
    load_b26_p1_semantic_contract,
    semantic_contract_identity,
)

__all__ = [
    "B26_DISCREPANCY_TAXONOMY_V1",
    "B26_KNOWN_AUTHORITY_CLASSES",
    "B26_P1_CONTRACT_VERSION",
    "B26_P1_SEMANTIC_CONTRACT_PATH",
    "B26_P1_SUPERSEDES_VERSION",
    "B26_REQUIRED_DISCREPANCY_REASONS",
    "B26_REQUIRED_FUTURE_INSERTION_SEAM",
    "B26_REQUIRED_SCOPE_DISPOSITIONS",
    "B26_REQUIRED_TRUTH_STATE_VOCABULARY",
    "B26_SUCCESSOR_STATUS_AUTHORIZED",
    "B26_SUCCESSOR_STATUS_NONE",
    "SemanticContractError",
    "SemanticContractIdentity",
    "load_b26_p1_semantic_contract",
    "semantic_contract_identity",
]
