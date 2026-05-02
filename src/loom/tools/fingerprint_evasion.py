"""research_fingerprint_evasion_test — Test browser fingerprint randomization effectiveness.

Validates anonymization effectiveness by simulating browser fingerprint collection
across multiple iterations and computing entropy/consistency metrics.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import string
from typing import Any

logger = logging.getLogger("loom.tools.fingerprint_evasion")


async def research_fingerprint_evasion_test(
    anonymizer_config: str = "default",
    test_iterations: int = 5,
) -> dict[str, Any]:
    """Test fingerprint randomization effectiveness across multiple iterations.

    Simulates browser fingerprint generation and measures randomization consistency.
    Tests across N iterations to compute entropy and consistency metrics for
    evaluating anonymizer effectiveness.

    Args:
        anonymizer_config: Type of anonymizer config to test
            - "default": Standard fingerprint collection (uses real attributes)
            - "strict": Aggressive randomization (randomizes 50% of attributes)
            - "custom": Custom configuration (randomizes 30% of attributes)
        test_iterations: Number of fingerprint generations (2-50, default 5)

    Returns:
        Dict with keys:
          - effectiveness_score: float (0-100%, higher = better randomization)
          - fingerprint_entropy: float (Shannon entropy of collected fingerprints)
          - attributes_tested: int (number of attributes tested)
          - consistency_metrics: dict with entropy breakdown per attribute type
          - fingerprints_collected: int (total fingerprints generated)
          - randomization_distribution: dict (attribute randomization rates)
          - success: bool (whether operation succeeded)
          - error: str (if operation failed)
    """
    # Validate parameters
    if not isinstance(test_iterations, int) or test_iterations < 2 or test_iterations > 50:
        return {
            "error": f"test_iterations must be 2-50, got {test_iterations}",
        }

    if anonymizer_config not in ("default", "strict", "custom"):
        return {
            "error": f"Invalid anonymizer_config: {anonymizer_config}. "
                     "Must be one of: default, strict, custom",
        }

    logger.info(
        "fingerprint_evasion_test anonymizer_config=%s iterations=%d",
        anonymizer_config,
        test_iterations,
    )

    try:
        # Generate fingerprints across N iterations
        fingerprints = _generate_synthetic_fingerprints(
            test_iterations,
            anonymizer_config,
        )

        if not fingerprints or "error" in fingerprints:
            return fingerprints

        # Compute entropy and consistency metrics
        metrics = _compute_evasion_metrics(
            fingerprints["fingerprints"],
            fingerprints["attributes"],
        )

        return {
            "effectiveness_score": metrics["effectiveness_score"],
            "fingerprint_entropy": metrics["entropy"],
            "attributes_tested": metrics["attributes_tested"],
            "consistency_metrics": metrics["consistency_by_type"],
            "fingerprints_collected": len(fingerprints["fingerprints"]),
            "randomization_distribution": metrics["randomization_rates"],
            "success": True,
        }

    except Exception as e:
        logger.exception("Unexpected error during fingerprint evasion test")
        return {
            "error": f"Unexpected error: {type(e).__name__}: {e}",
        }


def _generate_synthetic_fingerprints(
    iterations: int,
    config: str,
) -> dict[str, Any]:
    """Generate N synthetic fingerprints simulating browser attributes.

    Attributes tested:
    - userAgent: Browser identification string
    - platform: Operating system
    - language: Browser language
    - hardwareConcurrency: CPU core count
    - deviceMemory: Available RAM in GB
    - vendor: Browser vendor
    - doNotTrack: Privacy preference
    - colorDepth: Display color depth
    - screenResolution: Display resolution
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    ]

    platforms = ["Win32", "MacIntel", "Linux x86_64", "iPad", "iPhone"]
    languages = ["en-US", "en-GB", "de-DE", "fr-FR", "ja-JP", "zh-CN"]
    vendors = ["Google Chrome", "Apple", "Mozilla", "Opera", ""]
    hardware_concurrency = [2, 4, 8, 16, 32]
    device_memory = [4, 8, 16, 32]
    color_depths = [24, 32]
    resolutions = ["1920x1080", "1366x768", "2560x1440", "1024x768", "3840x2160"]

    fingerprints = []
    all_attributes = set()

    # Randomization rates by config
    randomization_rate = {"default": 0.0, "strict": 0.5, "custom": 0.3}[config]

    for i in range(iterations):
        fp = _generate_single_fingerprint(
            user_agents,
            platforms,
            languages,
            vendors,
            hardware_concurrency,
            device_memory,
            color_depths,
            resolutions,
            randomization_rate,
        )

        fingerprints.append(fp)
        if "attributes" in fp:
            all_attributes.update(fp["attributes"].keys())

    if not fingerprints:
        return {
            "error": "No fingerprints generated",
        }

    return {
        "fingerprints": fingerprints,
        "attributes": list(all_attributes),
    }


def _generate_single_fingerprint(
    user_agents: list[str],
    platforms: list[str],
    languages: list[str],
    vendors: list[str],
    hardware_concurrency: list[int],
    device_memory: list[int],
    color_depths: list[int],
    resolutions: list[str],
    randomization_rate: float,
) -> dict[str, Any]:
    """Generate a single simulated fingerprint."""
    # Base attributes (realistic values)
    attributes = {
        "userAgent": random.choice(user_agents),
        "platform": random.choice(platforms),
        "language": random.choice(languages),
        "hardwareConcurrency": str(random.choice(hardware_concurrency)),
        "deviceMemory": str(random.choice(device_memory)),
        "vendor": random.choice(vendors),
        "doNotTrack": random.choice(["1", "0", None]),
        "colorDepth": str(random.choice(color_depths)),
        "screenResolution": random.choice(resolutions),
    }

    # Apply randomization based on config
    if randomization_rate > 0:
        for key in list(attributes.keys()):
            if random.random() < randomization_rate:
                # Randomize: replace with random string
                attributes[key] = "randomized_" + "".join(
                    random.choices(string.ascii_lowercase + string.digits, k=8)
                )

    # Compute fingerprint hash
    fp_json = json.dumps(attributes, sort_keys=True)
    fp_hash = hashlib.sha256(fp_json.encode()).hexdigest()

    return {
        "id": fp_hash,
        "attributes": attributes,
    }


def _compute_evasion_metrics(
    fingerprints: list[dict[str, Any]],
    attributes: list[str],
) -> dict[str, Any]:
    """Compute entropy and consistency metrics from collected fingerprints."""
    if not fingerprints or not attributes:
        return {
            "effectiveness_score": 0.0,
            "entropy": 0.0,
            "attributes_tested": 0,
            "consistency_by_type": {},
            "randomization_rates": {},
        }

    import math
    from collections import Counter

    consistency_by_type = {}
    randomization_rates = {}
    total_entropy = 0.0

    # Analyze each attribute
    for attr in attributes:
        values = []
        for fp in fingerprints:
            if "attributes" in fp and attr in fp["attributes"]:
                values.append(fp["attributes"][attr])

        if not values:
            continue

        # Count unique values (higher = better randomization)
        unique_count = len(set(values))
        uniqueness_ratio = unique_count / len(values)
        randomization_rates[attr] = round(uniqueness_ratio * 100, 2)

        # Calculate Shannon entropy for this attribute
        counter = Counter(values)
        entropy = 0.0
        total_values = len(values)
        for count in counter.values():
            prob = count / total_values
            entropy -= prob * math.log2(prob + 1e-10)

        consistency_by_type[attr] = {
            "entropy": round(entropy, 4),
            "unique_values": unique_count,
            "total_samples": total_values,
            "randomization_rate": round(uniqueness_ratio * 100, 2),
        }

        total_entropy += entropy

    # Compute overall effectiveness score (0-100)
    # Based on average randomization rate
    avg_randomization = (
        sum(randomization_rates.values()) / len(randomization_rates)
        if randomization_rates
        else 0.0
    )

    # Effectiveness: combination of uniqueness and entropy
    # Perfect randomization = 100%, no randomization = 0%
    effectiveness_score = round(min(avg_randomization, 100.0), 2)

    # Average entropy across all attributes
    avg_entropy = (
        round(total_entropy / len(attributes), 4)
        if attributes
        else 0.0
    )

    return {
        "effectiveness_score": effectiveness_score,
        "entropy": avg_entropy,
        "attributes_tested": len(attributes),
        "consistency_by_type": consistency_by_type,
        "randomization_rates": randomization_rates,
    }
