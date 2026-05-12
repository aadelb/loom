"""research_hcs_report — HCS distribution report generation.

Generates per-model and per-strategy HCS distribution reports from recorded scores.
Detects regressions and exports markdown reports.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from loom.hcs_report import HCSReportGenerator
    _REPORT_AVAILABLE = True
except ImportError:
    _REPORT_AVAILABLE = False

logger = logging.getLogger("loom.tools.hcs_report")


async def research_hcs_report(
    report_type: str = "combined",
    regression_threshold: float = 1.0,
    data_path: str = "~/.loom/hcs_data.jsonl",
) -> dict[str, Any]:
    """Generate HCS distribution reports and detect regressions.

    Generates per-model and per-strategy HCS distribution reports from recorded
    scores. Can return model report, strategy report, combined markdown report,
    or regression analysis.

    Args:
        report_type: Type of report to generate:
            - "model": Per-model HCS distribution with statistics
            - "strategy": Per-strategy HCS distribution with statistics
            - "combined": Full markdown report with all data
            (default: "combined")
        regression_threshold: Minimum score drop to flag as regression (0.1-5.0,
            default: 1.0). Compares recent half vs. older half of data.
        data_path: Path to JSONL file storing HCS measurements
            (default: ~/.loom/hcs_data.jsonl)

    Returns:
        Dict with structure depending on report_type:
        - For "model": {"models": {...}, "total_readings": int}
        - For "strategy": {"strategies": {...}, "total_readings": int}
        - For "combined": {"markdown": str, "total_readings": int}
        Plus optional "regressions": [...] if threshold is specified and violations found

    Example:
        # Get per-model report
        result = await research_hcs_report(report_type="model")
        for model, stats in result["models"].items():
            print(f"{model}: mean={stats['mean']:.2f}, count={stats['count']}")

        # Get combined markdown report
        result = await research_hcs_report(report_type="combined")
        with open("hcs_report.md", "w") as f:
            f.write(result["markdown"])

        # Detect regressions
        result = await research_hcs_report(
            report_type="combined",
            regression_threshold=0.5
        )
        for regression in result.get("regressions", []):
            print(f"Regression: {regression['name']} dropped {regression['drop']:.2f}")
    """
    if not _REPORT_AVAILABLE:
        return {
            "error": "HCS report generator not available",
            "report_type": report_type,
            "total_readings": 0,
        }

    # Validate parameters
    if report_type not in ("model", "strategy", "combined"):
        return {
            "error": f"Invalid report_type: {report_type}. Must be 'model', 'strategy', or 'combined'.",
            "report_type": report_type,
            "total_readings": 0,
        }

    if not isinstance(regression_threshold, (int, float)) or regression_threshold < 0.1 or regression_threshold > 5.0:
        return {
            "error": f"regression_threshold must be between 0.1 and 5.0, got {regression_threshold}",
            "report_type": report_type,
            "total_readings": 0,
        }

    try:
        generator = HCSReportGenerator(data_path=data_path)

        result: dict[str, Any] = {}

        # Generate requested report
        if report_type == "model":
            result = generator.generate_model_report()
        elif report_type == "strategy":
            result = generator.generate_strategy_report()
        elif report_type == "combined":
            markdown = generator.generate_combined_report()
            result = {
                "markdown": markdown,
                "total_readings": len(generator.get_all_readings()),
            }
        else:
            raise ValueError(f"Unknown report_type: {report_type}")

        # Detect regressions
        regressions = generator.detect_regressions(threshold=regression_threshold)
        if regressions:
            result["regressions"] = regressions

        logger.info(
            "hcs_report_generated type=%s regressions=%d",
            report_type,
            len(regressions),
        )

        return result

    except FileNotFoundError as e:
        logger.error("hcs_report_file_not_found path=%s", data_path)
        return {
            "error": f"Data file not found: {data_path}",
            "report_type": report_type,
            "total_readings": 0,
        }
    except IOError as e:
        logger.error("hcs_report_io_error: %s", str(e))
        return {
            "error": f"IO error reading data: {str(e)}",
            "report_type": report_type,
            "total_readings": 0,
        }
    except ValueError as e:
        logger.error("hcs_report_value_error: %s", str(e))
        return {
            "error": f"Invalid data format: {str(e)}",
            "report_type": report_type,
            "total_readings": 0,
        }
    except Exception as e:
        logger.error("hcs_report_unexpected_error: %s", str(e), exc_info=True)
        return {
            "error": f"Unexpected error: {str(e)}",
            "report_type": report_type,
            "total_readings": 0,
        }
