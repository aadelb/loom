"""research_creepjs_audit — Privacy baseline assessment using creepjs fingerprinting."""

from __future__ import annotations

import logging
from typing import Any

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.creepjs_backend")


def _extract_creepjs_metrics(response_data: dict[str, Any]) -> dict[str, Any]:
	"""Extract privacy metrics from creepjs API response."""
	metrics = {
		"trust_score": response_data.get("trustScore", 0),
		"fingerprint_hash": None,
		"detected_features": {},
		"privacy_grade": "unknown",
		"mismatch_score": 0,
	}

	if "fingerprint" in response_data and isinstance(response_data["fingerprint"], dict):
		metrics["fingerprint_hash"] = response_data["fingerprint"].get("hash")

	if "components" in response_data and isinstance(response_data["components"], dict):
		components = response_data["components"]
		detected = {}
		mismatch_count = 0

		for feature in ["canvas", "webgl", "audio", "fonts", "screen", "timezone"]:
			if feature in components:
				data = components[feature]
				is_lie = bool(data.get("lies", False))
				if is_lie:
					mismatch_count += 1
				detected[feature] = {
					"detected": is_lie,
					"value": data.get("value") if feature != "fonts" else len(data.get("value", [])),
				}

		metrics["detected_features"] = detected
		metrics["mismatch_score"] = mismatch_count

	# Calculate privacy grade
	score = metrics["trust_score"]
	metrics["privacy_grade"] = (
		"A" if score >= 85 else
		"B" if score >= 70 else
		"C" if score >= 55 else
		"D" if score >= 40 else
		"F"
	)

	return metrics


async def _run_creepjs_audit(target_url: str) -> dict[str, Any]:
	"""Run creepjs audit using nodriver browser automation."""
	try:
		import nodriver  # type: ignore
		browser = await nodriver.start()
		page = await browser.get(target_url)
		await page.sleep(3)

		fp_data = await page.evaluate(
			"() => window.fp?.result || null"
		)

		await browser.stop()
		return fp_data or {"error": "Failed to extract creepjs data"}

	except ImportError:
		return {"error": "nodriver not available. Install with: pip install nodriver"}
	except Exception as exc:
		logger.error("creepjs_audit_failed: %s", exc, exc_info=True)
		return {"error": f"Browser automation failed: {str(exc)}"}


def research_creepjs_audit(
	target_url: str = "https://creepjs.web.app",
	headless: bool = True,
) -> dict[str, Any]:
	"""Privacy baseline assessment using creepjs fingerprinting.

	Analyzes browser fingerprinting vectors:
	- Canvas, WebGL, AudioContext, fonts, screen, timezone resistance

	Args:
		target_url: URL to analyze (default creepjs self-test page)
		headless: Whether to run browser in headless mode

	Returns:
		Dict with: success, trust_score, fingerprint_hash, detected_features,
		privacy_grade (A-F), mismatch_score, assessment, recommendations, error
	"""
	result: dict[str, Any] = {
		"success": False,
		"trust_score": 0,
		"fingerprint_hash": None,
		"detected_features": {},
		"privacy_grade": "unknown",
		"mismatch_score": 0,
		"assessment": "",
		"recommendations": [],
		"error": None,
	}

	if target_url:
		try:
			validate_url(target_url)
		except UrlSafetyError as e:
			result["error"] = str(e)
			logger.warning("creepjs_invalid_url: %s", e)
			return result

	try:
		import asyncio
		try:
			loop = asyncio.get_event_loop()
		except RuntimeError:
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)

		fp_response = loop.run_until_complete(_run_creepjs_audit(target_url))

		if "error" in fp_response:
			result["error"] = fp_response["error"]
			return result

		metrics = _extract_creepjs_metrics(fp_response)
		result.update(metrics)
		result["success"] = True

		# Assessment text
		assessments = {
			"A": "Excellent privacy baseline. Strong fingerprinting resistance.",
			"B": "Good privacy baseline. Some vectors detected but acceptable.",
			"C": "Fair privacy baseline. Consider enabling privacy extensions.",
			"D": "Poor privacy baseline. Multiple vulnerabilities detected.",
			"F": "Critical privacy baseline. Strong fingerprinting vulnerability.",
		}
		result["assessment"] = assessments.get(result["privacy_grade"], "Unknown status")

		# Recommendations
		features = result.get("detected_features", {})
		recommendations = []

		if features.get("canvas", {}).get("detected"):
			recommendations.append("Canvas fingerprinting: Use extension to block canvas API")
		if features.get("webgl", {}).get("detected"):
			recommendations.append("WebGL fingerprinting: Disable WebGL or use privacy extension")
		if features.get("audio", {}).get("detected"):
			recommendations.append("AudioContext fingerprinting: Limit audio API access")
		if features.get("fonts", {}).get("detected"):
			recommendations.append("Font enumeration: Use extension blocking font detection")
		if result["mismatch_score"] > 3:
			recommendations.append("Multiple vectors detected: Enable comprehensive hardening")

		result["recommendations"] = recommendations or [
			"No critical vectors detected. Maintain current privacy settings."
		]

		logger.info(
			"creepjs_audit_complete trust_score=%d grade=%s mismatches=%d",
			result["trust_score"],
			result["privacy_grade"],
			result["mismatch_score"],
		)

		return result

	except Exception as exc:
		result["error"] = f"Unexpected error: {str(exc)}"
		logger.error("creepjs_audit_exception: %s", exc, exc_info=True)
		return result
