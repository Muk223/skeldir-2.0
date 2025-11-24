"""
Channel Normalization Module

This module implements the canonical channel normalization logic for B0.4 ingestion.
It guarantees that all channel values are either valid taxonomy codes or the 'unknown' fallback.

Contract: normalize_channel() ALWAYS returns a valid channel_taxonomy.code value.
It NEVER returns None, empty strings, or arbitrary non-taxonomy values.

Related Documents:
- db/docs/channel_contract.md (Authoritative channel governance contract)
- db/channel_mapping.yaml (Vendor-to-canonical mapping source of truth)
- B0.3-P_CHANNEL_GOVERNANCE_REMEDIATION.md (Implementation evidence)
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

import yaml

# Configure structured logging
logger = logging.getLogger(__name__)

# Cache for channel mapping and taxonomy codes
_CHANNEL_MAPPING: Optional[Dict] = None
_VALID_TAXONOMY_CODES: Optional[set] = None


def load_channel_mapping() -> Dict:
    """
    Load channel mapping from db/channel_mapping.yaml.
    
    Returns:
        Dictionary with structure: {vendor: {vendor_indicator: canonical_code}}
        
    Raises:
        FileNotFoundError: If channel_mapping.yaml doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    global _CHANNEL_MAPPING
    
    if _CHANNEL_MAPPING is not None:
        return _CHANNEL_MAPPING
    
    # Find channel_mapping.yaml relative to project root
    # Assuming backend/app/ingestion/channel_normalization.py structure
    project_root = Path(__file__).parent.parent.parent.parent
    mapping_file = project_root / "db" / "channel_mapping.yaml"
    
    if not mapping_file.exists():
        raise FileNotFoundError(
            f"channel_mapping.yaml not found at {mapping_file}. "
            "This file is required for channel normalization."
        )
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    _CHANNEL_MAPPING = data.get('sources', {})
    logger.info(
        "Loaded channel mapping",
        extra={"vendor_count": len(_CHANNEL_MAPPING), "mapping_file": str(mapping_file)}
    )
    
    return _CHANNEL_MAPPING


def get_valid_taxonomy_codes() -> set:
    """
    Get the set of valid canonical channel codes from channel_taxonomy.
    
    In production, this would query the database. For now, we hardcode the
    canonical set based on current taxonomy state (post-migration 202511161120).
    
    Returns:
        Set of valid channel taxonomy codes
    """
    global _VALID_TAXONOMY_CODES
    
    if _VALID_TAXONOMY_CODES is not None:
        return _VALID_TAXONOMY_CODES
    
    # Canonical codes from channel_taxonomy (9 original + 1 'unknown')
    _VALID_TAXONOMY_CODES = {
        'unknown',            # Fallback for unmapped channels
        'direct',            # Direct traffic
        'email',             # Email campaigns
        'facebook_brand',    # Facebook brand awareness
        'facebook_paid',     # Facebook paid ads
        'google_display_paid',  # Google Display Network
        'google_search_paid',   # Google Search Ads
        'organic',           # Organic search/social
        'referral',          # Referral traffic
        'tiktok_paid',       # TikTok paid ads
    }
    
    logger.info(
        "Loaded valid taxonomy codes",
        extra={"taxonomy_code_count": len(_VALID_TAXONOMY_CODES)}
    )
    
    return _VALID_TAXONOMY_CODES


def log_unmapped_channel(
    raw_key: str,
    utm_source: Optional[str],
    utm_medium: Optional[str],
    vendor: Optional[str],
    tenant_id: Optional[str] = None
) -> None:
    """
    Log unmapped channel occurrence for data quality monitoring.
    
    This structured log enables investigation and remediation of mapping gaps.
    
    Args:
        raw_key: The combined key used for mapping lookup
        utm_source: Original UTM source parameter (if available)
        utm_medium: Original UTM medium parameter (if available)
        vendor: Vendor/integration identifier
        tenant_id: Tenant experiencing the unmapped channel (if available)
    """
    logger.info(
        "Unmapped channel encountered - falling back to 'unknown'",
        extra={
            "event_type": "unmapped_channel",
            "raw_key": raw_key,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "vendor": vendor,
            "tenant_id": tenant_id,
            "fallback_channel": "unknown",
        }
    )


def increment_unmapped_channel_metric(vendor: str, raw_key: str) -> None:
    """
    Increment unmapped channel metric for monitoring.
    
    In production, this would emit to Prometheus or similar observability platform.
    For now, we log at DEBUG level to indicate metric emission point.
    
    Args:
        vendor: Vendor identifier for metric tagging
        raw_key: Raw key for metric tagging
    """
    logger.debug(
        "Metric increment: unmapped_channel.count",
        extra={
            "metric_name": "unmapped_channel.count",
            "metric_type": "counter",
            "tags": {"vendor": vendor, "raw_key": raw_key},
        }
    )


def normalize_channel(
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    vendor: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> str:
    """
    Map vendor-specific channel indicators to canonical channel codes.
    
    This is the authoritative normalization function for all channel values in Skeldir.
    It implements the channel governance contract defined in db/docs/channel_contract.md.
    
    Algorithm:
    1. Load channel_mapping.yaml (cached after first load)
    2. Build raw key from vendor/utm_source/utm_medium
    3. Lookup in vendor-specific mapping
    4. Validate that mapped value exists in channel_taxonomy
    5. If mapped and valid: return canonical code
    6. If unmapped: log occurrence, emit metric, return 'unknown' fallback
    
    Args:
        utm_source: UTM source parameter from tracking URL (e.g., "google", "facebook")
        utm_medium: UTM medium parameter from tracking URL (e.g., "cpc", "display")
        vendor: Vendor/integration identifier (e.g., "google_ads", "shopify", "stripe")
        tenant_id: Optional tenant ID for logging context
    
    Returns:
        Canonical channel code from channel_taxonomy.code.
        GUARANTEE: Always returns a valid taxonomy code or 'unknown'. Never None or arbitrary strings.
    
    Examples:
        >>> normalize_channel(utm_source="google", utm_medium="cpc", vendor="google_ads")
        'google_search_paid'
        
        >>> normalize_channel(utm_source="facebook", utm_medium="cpc", vendor="facebook_ads")
        'facebook_paid'
        
        >>> normalize_channel(utm_source="bing", utm_medium="cpc", vendor="bing_ads")
        'unknown'  # No mapping exists for bing_ads
        
        >>> normalize_channel(utm_source=None, utm_medium=None, vendor=None)
        'unknown'  # No indicators provided
    """
    # Load mapping and taxonomy (cached)
    try:
        mapping = load_channel_mapping()
        valid_codes = get_valid_taxonomy_codes()
    except Exception as e:
        logger.error(
            "Failed to load channel mapping or taxonomy codes",
            extra={"error": str(e)},
            exc_info=True
        )
        # Fail-safe: return 'unknown' if we can't load configuration
        return 'unknown'
    
    # Handle None inputs by converting to empty string for consistent key building
    utm_source = utm_source or ""
    utm_medium = utm_medium or ""
    vendor = vendor or ""
    
    # If no vendor specified, try to infer a default mapping based on UTM parameters
    if not vendor:
        # Default to 'direct' if no tracking parameters
        if not utm_source and not utm_medium:
            return 'direct'
        # Otherwise we have UTM params but no vendor context - treat as unmapped
        raw_key = f"{utm_source}/{utm_medium}"
        log_unmapped_channel(raw_key, utm_source, utm_medium, vendor="unknown", tenant_id=tenant_id)
        increment_unmapped_channel_metric(vendor="unknown", raw_key=raw_key)
        return 'unknown'
    
    # Check if vendor exists in mapping
    if vendor not in mapping:
        raw_key = f"{vendor}/{utm_source}/{utm_medium}"
        log_unmapped_channel(raw_key, utm_source, utm_medium, vendor, tenant_id)
        increment_unmapped_channel_metric(vendor, raw_key)
        return 'unknown'
    
    vendor_mapping = mapping[vendor]
    
    # Try to find canonical code using various key patterns
    # Pattern 1: Direct vendor indicator lookup (e.g., "FB_ADS", "SEARCH")
    canonical_code = None
    
    # Check uppercase utm_source first (common pattern in mapping)
    if utm_source:
        canonical_code = vendor_mapping.get(utm_source.upper())
    
    # Check combination keys (e.g., "GOOGLE_SEARCH", "FACEBOOK_ADS")
    if not canonical_code and utm_source and utm_medium:
        combined_key = f"{utm_source.upper()}_{utm_medium.upper()}"
        canonical_code = vendor_mapping.get(combined_key)
    
    # Check utm_medium alone
    if not canonical_code and utm_medium:
        canonical_code = vendor_mapping.get(utm_medium.upper())
    
    # Check lowercase versions (some vendors use lowercase)
    if not canonical_code:
        for key in [utm_source, utm_medium, f"{utm_source}_{utm_medium}"]:
            if key:
                canonical_code = vendor_mapping.get(key)
                if canonical_code:
                    break
    
    # If we found a mapping, validate it exists in taxonomy
    if canonical_code:
        if canonical_code in valid_codes:
            logger.debug(
                "Channel normalized successfully",
                extra={
                    "utm_source": utm_source,
                    "utm_medium": utm_medium,
                    "vendor": vendor,
                    "canonical_code": canonical_code,
                }
            )
            return canonical_code
        else:
            # Mapped value doesn't exist in taxonomy (configuration error)
            logger.warning(
                "Mapped channel code not in taxonomy - falling back to 'unknown'",
                extra={
                    "mapped_code": canonical_code,
                    "utm_source": utm_source,
                    "utm_medium": utm_medium,
                    "vendor": vendor,
                    "tenant_id": tenant_id,
                }
            )
    
    # No mapping found - fall back to 'unknown'
    raw_key = f"{vendor}/{utm_source}/{utm_medium}" if utm_source or utm_medium else vendor
    log_unmapped_channel(raw_key, utm_source, utm_medium, vendor, tenant_id)
    increment_unmapped_channel_metric(vendor, raw_key)
    return 'unknown'


def reload_channel_mapping() -> None:
    """
    Force reload of channel mapping from disk.
    
    Use this in development or after deploying updated channel_mapping.yaml
    to ensure the service picks up new mappings without restart.
    """
    global _CHANNEL_MAPPING
    _CHANNEL_MAPPING = None
    load_channel_mapping()
    logger.info("Channel mapping reloaded from disk")


def reload_taxonomy_codes() -> None:
    """
    Force reload of valid taxonomy codes.
    
    In production, this would re-query the database. For now, it clears the cache
    so the next call to get_valid_taxonomy_codes() will reload the hardcoded set.
    """
    global _VALID_TAXONOMY_CODES
    _VALID_TAXONOMY_CODES = None
    get_valid_taxonomy_codes()
    logger.info("Taxonomy codes reloaded")






