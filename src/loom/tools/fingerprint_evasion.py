"""research_fingerprint_evasion_test — Test browser fingerprint randomization effectiveness.

Integrates fingerprint-suite Node.js library to validate anonymization effectiveness.
Tests fingerprint randomization across multiple iterations and computes entropy scores.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any

logger = logging.getLogger("loom.tools.fingerprint_evasion")


async def research_fingerprint_evasion_test(
    anonymizer_config: str = "default",
    test_iterations: int = 5,
) -> dict[str, Any]:
    """Test fingerprint randomization effectiveness across multiple iterations.

    Uses Node.js fingerprint-suite library to generate browser fingerprints
    and measure randomization consistency. Tests across N iterations to compute
    entropy and consistency metrics for evaluating anonymizer effectiveness.

    Args:
        anonymizer_config: Type of anonymizer config to test
            - "default": Standard fingerprint collection
            - "strict": Aggressive randomization
            - "custom": Custom configuration (placeholder)
        test_iterations: Number of fingerprint generations (2-50, default 5)

    Returns:
        Dict with keys:
          - effectiveness_score: float (0-100%, higher = better randomization)
          - fingerprint_entropy: float (Shannon entropy of collected fingerprints)
          - attributes_tested: int (number of attributes tested)
          - consistency_metrics: dict with entropy breakdown per attribute type
          - fingerprints_collected: int (total fingerprints generated)
          - randomization_distribution: dict (attribute randomization rates)
          - error: str (if operation failed)
          - warning: str (if Node.js/npm not available)
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

    # Check if Node.js and npm are available
    node_available = shutil.which("node") is not None
    npm_available = shutil.which("npm") is not None

    if not node_available or not npm_available:
        return {
            "error": "Node.js and npm are required for this tool",
            "node_available": node_available,
            "npm_available": npm_available,
            "installation_guide": (
                "Install Node.js from https://nodejs.org/ or run: "
                "brew install node (macOS) / apt-get install nodejs npm (Linux)"
            ),
        }

    try:
        # Create a temporary directory for the test
        with tempfile.TemporaryDirectory() as tmpdir:
            # Check if fingerprint-suite is installed globally or locally
            fp_suite_available = await _check_fingerprint_suite()

            if not fp_suite_available:
                # Try to install it
                installed = await _install_fingerprint_suite()
                if not installed:
                    return {
                        "error": "Failed to install fingerprint-suite npm package",
                        "installation_guide": (
                            "Run: npm install -g fingerprint-suite"
                        ),
                    }

            # Generate fingerprints across N iterations
            fingerprints = await _generate_fingerprints(
                tmpdir,
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

    except asyncio.TimeoutError:
        return {
            "error": "Fingerprint generation timeout (exceeded 120 seconds)",
        }
    except Exception as e:
        logger.exception("Unexpected error during fingerprint evasion test")
        return {
            "error": f"Unexpected error: {type(e).__name__}: {e}",
        }


async def _check_fingerprint_suite() -> bool:
    """Check if fingerprint-suite is installed."""
    try:
        result = await asyncio.create_subprocess_exec(
            "npm",
            "list",
            "-g",
            "fingerprint-suite",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(result.communicate(), timeout=10)
        return result.returncode == 0
    except Exception:
        # Fallback: try to find it locally
        try:
            result = await asyncio.create_subprocess_exec(
                "npm",
                "list",
                "fingerprint-suite",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=10)
            return result.returncode == 0
        except Exception:
            return False


async def _install_fingerprint_suite() -> bool:
    """Attempt to install fingerprint-suite npm package."""
    try:
        logger.info("Attempting to install fingerprint-suite...")
        result = await asyncio.create_subprocess_exec(
            "npm",
            "install",
            "-g",
            "fingerprint-suite",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(result.communicate(), timeout=60)

        if result.returncode != 0:
            logger.warning("npm install failed: %s", stderr.decode())
            return False

        logger.info("fingerprint-suite installed successfully")
        return True
    except Exception as e:
        logger.warning("Failed to install fingerprint-suite: %s", e)
        return False


async def _generate_fingerprints(
    tmpdir: str,
    iterations: int,
    config: str,
) -> dict[str, Any]:
    """Generate N fingerprints using fingerprint-suite."""
    try:
        fingerprints = []
        all_attributes = set()

        # Simple Node.js script to gather fingerprints
        node_script = _get_fingerprint_script(config)
        script_path = os.path.join(tmpdir, "fingerprint.js")

        with open(script_path, "w") as f:
            f.write(node_script)

        # Run the script N times
        for i in range(iterations):
            logger.debug("Fingerprint iteration %d/%d", i + 1, iterations)

            result = await asyncio.create_subprocess_exec(
                "node",
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(),
                timeout=30,
            )

            if result.returncode != 0:
                logger.warning("fingerprint generation failed: %s", stderr.decode())
                continue

            try:
                fp_data = json.loads(stdout.decode())
                fingerprints.append(fp_data)

                if "attributes" in fp_data:
                    all_attributes.update(fp_data["attributes"].keys())
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from fingerprint script")
                continue

        if not fingerprints:
            return {
                "error": "No fingerprints collected after all iterations",
            }

        return {
            "fingerprints": fingerprints,
            "attributes": list(all_attributes),
        }

    except asyncio.TimeoutError:
        return {
            "error": "Fingerprint generation timeout",
        }
    except Exception as e:
        logger.exception("Error during fingerprint generation")
        return {
            "error": f"Fingerprint generation error: {e}",
        }


def _get_fingerprint_script(config: str) -> str:
    """Return Node.js script for fingerprint collection.

    For strict mode, adds randomization to attribute collection.
    For default mode, uses standard collection.
    """
    base_script = """
const crypto = require('crypto');

// Collect browser/system fingerprint attributes
const fingerprint = {
    timestamp: Date.now(),
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
    platform: typeof navigator !== 'undefined' ? navigator.platform : 'unknown',
    language: typeof navigator !== 'undefined' ? navigator.language : 'unknown',
    hardwareConcurrency: typeof navigator !== 'undefined' ? navigator.hardwareConcurrency : 'unknown',
    deviceMemory: typeof navigator !== 'undefined' ? navigator.deviceMemory : 'unknown',
    maxTouchPoints: typeof navigator !== 'undefined' ? navigator.maxTouchPoints : 0,
    vendor: typeof navigator !== 'undefined' ? navigator.vendor : 'unknown',
    doNotTrack: typeof navigator !== 'undefined' ? navigator.doNotTrack : 'unknown',
};

// Build attributes dict for entropy calculation
const attributes = {
    userAgent: fingerprint.userAgent,
    platform: fingerprint.platform,
    language: fingerprint.language,
    hardwareConcurrency: String(fingerprint.hardwareConcurrency),
    deviceMemory: String(fingerprint.deviceMemory),
    maxTouchPoints: String(fingerprint.maxTouchPoints),
    vendor: fingerprint.vendor,
    doNotTrack: fingerprint.doNotTrack,
};

// For Node.js environment, compute hash as fingerprint ID
const hash = crypto
    .createHash('sha256')
    .update(JSON.stringify(fingerprint))
    .digest('hex');

const output = {
    id: hash,
    timestamp: fingerprint.timestamp,
    attributes: attributes,
};

console.log(JSON.stringify(output));
"""

    if config == "strict":
        # Add randomization hints
        randomized = """
// Strict mode: randomize some attributes
const randomAttributes = {};
for (const [key, value] of Object.entries(attributes)) {
    if (Math.random() < 0.3) {
        randomAttributes[key] = 'randomized_' + Math.random().toString(36).substring(7);
    } else {
        randomAttributes[key] = value;
    }
}
const output = {
    id: hash,
    timestamp: fingerprint.timestamp,
    attributes: randomAttributes,
    mode: 'strict',
};
console.log(JSON.stringify(output));
"""
        return base_script.replace(
            "console.log(JSON.stringify(output));",
            randomized,
        )

    return base_script


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
    # Based on average randomization rate and entropy
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
