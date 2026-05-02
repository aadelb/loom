"""research_detect_anomalies — Detect numerical and textual anomalies in research data."""

from __future__ import annotations
import logging, math, random
from typing import Any

logger = logging.getLogger("loom.tools.anomaly_detector")


async def research_detect_anomalies(data: list[float], method: str = "zscore", threshold: float = 2.0) -> dict[str, Any]:
    """Detect numerical anomalies using zscore, iqr, or isolation methods."""
    try:
        if not data or len(data) > 100000:
            return {"error": "data list invalid (empty or >100k items)", "method": method}
        if method not in ("zscore", "iqr", "isolation"):
            return {"error": f"method must be zscore/iqr/isolation", "method": method}
        if not (0 < threshold <= 10):
            return {"error": f"threshold must be 0<x<=10", "method": method}

        values = [float(x) for x in data if x is not None]
        if not values:
            return {"error": "no valid numeric values", "method": method}

        n, mean = len(values), sum(values) / len(values)
        std = math.sqrt(sum((x - mean) ** 2 for x in values) / max(1, n - 1)) if n > 1 else 0
        sv = sorted(values)
        q1, q3 = sv[len(sv) // 4] if len(sv) > 3 else sv[0], sv[3 * len(sv) // 4] if len(sv) > 3 else sv[-1]

        anomalies = []
        if method == "zscore" and std > 0:
            anomalies = [{"index": i, "value": round(v, 4), "score": round(abs((v - mean) / std), 3),
                         "reason": f"zscore {abs((v - mean) / std):.2f} > {threshold}"}
                        for i, v in enumerate(values) if abs((v - mean) / std) > threshold]
        elif method == "iqr":
            iqr = q3 - q1 if q3 > q1 else 1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            anomalies = [{"index": i, "value": round(v, 4), "score": round(min(abs(v - lo), abs(v - hi)) / iqr, 3),
                         "reason": f"outside IQR bounds"}
                        for i, v in enumerate(values) if v < lo or v > hi]
        elif method == "isolation":
            random.seed(42)
            scores = [0.0] * len(values)
            for _ in range(min(10, max(2, len(values) // 2))):
                split = random.choice(values)
                left, right = [i for i, v in enumerate(values) if v <= split], [i for i, v in enumerate(values) if v > split]
                threshold_size = max(1, len(values) // 10)
                for i in (left if len(left) < threshold_size else right if len(right) < threshold_size else []):
                    scores[i] += 1
            max_s = max(scores) if scores else 1
            anomalies = [{"index": i, "value": round(v, 4), "score": round(scores[i] / max_s, 3), "reason": "isolation"}
                        for i, v in enumerate(values) if scores[i] > max_s * 0.5]

        return {
            "method": method, "threshold": threshold, "total_points": len(values),
            "anomalies": sorted(anomalies, key=lambda x: x["score"], reverse=True),
            "anomaly_rate": round(len(anomalies) / len(values), 4),
            "statistics": {"mean": round(mean, 4), "std": round(std, 4), "min": round(min(values), 4),
                          "max": round(max(values), 4), "q1": round(q1, 4), "q3": round(q3, 4)}
        }
    except Exception as e:
        logger.exception("anomaly detection error")
        return {"error": f"{type(e).__name__}: {str(e)[:100]}", "method": method}


async def research_detect_text_anomalies(texts: list[str], baseline: str = "") -> dict[str, Any]:
    """Detect unusual text patterns (length, vocabulary, structure, encoding)."""
    try:
        if not texts or len(texts) > 50000:
            return {"error": "texts list invalid", "total_texts": 0}
        text_list = [str(t) for t in texts if t is not None]
        if not text_list:
            return {"error": "no valid text values", "total_texts": 0}

        get_words = lambda t: [w.lower() for w in t.split() if any(c.isalnum() for c in w)]
        lengths = [len(t) for t in text_list]
        med_len = sorted(lengths)[len(lengths) // 2]
        all_vocab = set(w for t in text_list for w in get_words(t))

        anomalies, types_found = [], {}
        for idx, text in enumerate(text_list):
            anom_types, score = [], 0.0
            words = get_words(text)

            if med_len > 0 and (len(text) / med_len < 0.5 or len(text) / med_len > 2.0):
                anom_types.append("unusual_length")
                score += 0.3
            if all_vocab and len(set(words) & all_vocab) / len(all_vocab) < 0.3:
                anom_types.append("unusual_vocabulary")
                score += 0.3
            punct = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(1, len(text))
            if punct > 0.4 or (len(text) > 50 and punct < 0.05):
                anom_types.append("unusual_structure")
                score += 0.2
            if any(ord(c) < 32 and c not in '\t\n\r' for c in text) or "�" in text:
                anom_types.append("encoding_artifacts")
                score += 0.2

            if anom_types:
                anomalies.append({"index": idx, "text_preview": text[:100], "anomaly_types": anom_types, "score": round(score, 3)})
                for t in anom_types:
                    types_found[t] = types_found.get(t, 0) + 1

        return {
            "total_texts": len(text_list), "anomalies": sorted(anomalies, key=lambda x: x["score"], reverse=True),
            "anomaly_count": len(anomalies), "types_found": types_found,
            "statistics": {"mean_length": round(sum(lengths) / len(lengths), 2), "median_length": int(med_len),
                          "max_length": max(lengths), "vocab_size": len(all_vocab)}
        }
    except Exception as e:
        logger.exception("text anomaly detection error")
        return {"error": f"{type(e).__name__}", "total_texts": len(texts)}
