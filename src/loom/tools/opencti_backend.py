"""OpenCTI threat intelligence backend — GraphQL-based CTI platform queries."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.opencti_backend")

# GraphQL query for indicator lookups
_OPENCTI_INDICATOR_QUERY = """
query GetIndicator($value: String!) {
  indicators(search: $value, first: 1) {
    edges {
      node {
        id
        pattern
        patternType
        validFrom
        validUntil
        createdBy {
          name
        }
        objectMarking {
          definition
        }
        objectLabel {
          value
        }
        externalReferences {
          url
          description
        }
        relationships {
          edges {
            node {
              id
              relationship_type
              to {
                ... on AttackPattern {
                  name
                }
                ... on Malware {
                  name
                }
                ... on ThreatActor {
                  name
                }
                ... on Tool {
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def research_opencti_query(
    indicator: str,
    indicator_type: str = "auto",
    opencti_url: str = "",
) -> dict[str, Any]:
    """Query OpenCTI threat intelligence platform for indicator information.

    OpenCTI is a modern CTI (Cyber Threat Intelligence) platform that provides
    structured threat data via GraphQL API. Queries indicators, returns relationships
    to malware, attack patterns, threat actors, and tools.

    Args:
        indicator: IOC value to query (IP, domain, email, hash, URL, etc.)
        indicator_type: Type hint for the indicator ('auto', 'ip', 'domain', 'email',
                       'hash', 'url', 'file'). 'auto' attempts auto-detection.
        opencti_url: Override OpenCTI endpoint URL. Defaults to OPENCTI_URL env var.
                     Falls back to "http://localhost:8080" if not set.

    Returns:
        Dict with keys:
        - indicator: The queried IOC value
        - indicator_type: Detected or provided type
        - stix_objects: List of STIX objects found
        - relationships: Related threats (malware, attacks, actors, tools)
        - confidence: Confidence score (if available)
        - created_by: Organization/source that added the intel
        - error: Error message if query failed
    """
    # Get OpenCTI URL from parameter, env, or default
    url = opencti_url or os.environ.get("OPENCTI_URL", "http://localhost:8080")
    api_key = os.environ.get("OPENCTI_API_KEY", "")

    result: dict[str, Any] = {
        "indicator": indicator,
        "indicator_type": indicator_type,
        "stix_objects": [],
        "relationships": [],
        "confidence": None,
        "created_by": None,
    }

    # Check if OpenCTI is configured
    if not api_key:
        result["error"] = (
            "OPENCTI_API_KEY not set. Configure OpenCTI API key in environment."
        )
        logger.warning("opencti_not_configured: missing API key")
        return result

    # Build GraphQL request
    graphql_endpoint = f"{url}/graphql"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": _OPENCTI_INDICATOR_QUERY,
        "variables": {"value": indicator},
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                graphql_endpoint,
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        # Check for GraphQL errors
        if "errors" in data:
            errors = data.get("errors", [])
            error_msg = ", ".join(
                [err.get("message", "unknown error") for err in errors]
            )
            result["error"] = f"GraphQL error: {error_msg}"
            logger.warning("opencti_graphql_error indicator=%s: %s", indicator, error_msg)
            return result

        # Parse response
        data_obj = data.get("data") or {}
        indicators = data_obj.get("indicators", {})
        edges = indicators.get("edges", [])

        if not edges:
            result["error"] = f"No indicators found for: {indicator}"
            return result

        # Extract first indicator match
        node = edges[0].get("node", {})

        # Collect STIX objects
        stix_objects = [
            {
                "id": node.get("id"),
                "pattern": node.get("pattern"),
                "pattern_type": node.get("patternType"),
                "valid_from": node.get("validFrom"),
                "valid_until": node.get("validUntil"),
            }
        ]
        result["stix_objects"] = stix_objects

        # Extract created_by (source org)
        created_by = node.get("createdBy", {})
        if created_by:
            result["created_by"] = created_by.get("name")

        # Extract object markings (TLP, etc.) and labels
        markings = [
            m.get("definition") for m in (node.get("objectMarking") or [])
        ]
        labels = [
            label.get("value") for label in (node.get("objectLabel") or [])
        ]

        # Extract relationships (related threats)
        relationships = []
        relationships_obj = node.get("relationships") or {}
        for rel_edge in relationships_obj.get("edges", []):
            rel_node = rel_edge.get("node", {})
            rel_to = rel_node.get("to", {})
            rel_name = rel_to.get("name", "Unknown")

            relationships.append(
                {
                    "type": rel_node.get("relationship_type"),
                    "related_object": rel_name,
                }
            )

        result["relationships"] = relationships
        result["markings"] = markings
        result["labels"] = labels

        logger.info(
            "opencti_query_success indicator=%s relationships=%d",
            indicator,
            len(relationships),
        )

    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text[:200]  # Truncate to prevent data leakage
        result["error"] = (
            f"OpenCTI API error ({exc.response.status_code}): {response_text}"
        )
        logger.error(
            "opencti_http_error indicator=%s status=%d",
            indicator,
            exc.response.status_code,
        )
    except httpx.RequestError as exc:
        result["error"] = f"OpenCTI connection error: {exc!s}"
        logger.error("opencti_connection_error indicator=%s: %s", indicator, exc)
    except (json.JSONDecodeError, KeyError) as exc:
        result["error"] = f"OpenCTI response parse error: {exc!s}"
        logger.error("opencti_parse_error indicator=%s: %s", indicator, exc)
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc!s}"
        logger.error("opencti_unexpected_error indicator=%s: %s", indicator, exc)

    return result
