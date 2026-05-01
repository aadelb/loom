#!/usr/bin/env python3
"""REQ-004: Execute "top paying jobs UAE" with accurate data.

Test script that calls research tools from Loom source:
1. research_multi_search for general UAE job trends
2. research_salary_synthesize for Software Engineer in Dubai
3. research_salary_synthesize for Data Scientist in Abu Dhabi
4. research_market_velocity for software engineering demand in Dubai

Outputs results to /opt/research-toolbox/tmp/req004_result.json
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_req004() -> dict:
    """Execute REQ-004 test suite."""

    # Import tools from loom
    try:
        from loom.tools.multi_search import research_multi_search
        from loom.tools.salary_synthesizer import research_salary_synthesize
        from loom.tools.career_trajectory import research_market_velocity
    except ImportError as e:
        logger.error(f"Failed to import loom tools: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

    result = {
        "req_id": "REQ-004",
        "title": "Top Paying Jobs UAE with Accurate Data",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "running",
        "tests": {}
    }

    try:
        # Test 1: Multi-search for UAE job market trends
        logger.info("TEST 1: research_multi_search('top paying jobs UAE 2026 salary data')")
        test1_result = research_multi_search(
            query="top paying jobs UAE 2026 salary data",
            max_results=20
        )
        result["tests"]["multi_search"] = {
            "status": "success",
            "query": "top paying jobs UAE 2026 salary data",
            "raw_count": test1_result.get("total_raw_results", 0),
            "deduplicated_count": test1_result.get("total_deduplicated", 0),
            "sources": test1_result.get("engines_queried", []),
            "sources_breakdown": test1_result.get("sources_breakdown", {}),
            "results_sample": test1_result.get("results", [])[:5],
            "full_results_count": len(test1_result.get("results", []))
        }
        logger.info(f"✓ TEST 1: Found {len(test1_result.get('results', []))} deduplicated results")

    except Exception as e:
        logger.error(f"✗ TEST 1 FAILED: {e}")
        result["tests"]["multi_search"] = {"status": "failed", "error": str(e)}

    try:
        # Test 2: Salary synthesis for Software Engineer in Dubai
        logger.info("TEST 2: research_salary_synthesize('software engineer', 'Dubai, UAE')")
        test2_result = research_salary_synthesize(
            job_title="software engineer",
            location="Dubai, UAE",
            skills=["AWS", "Kubernetes", "Machine Learning"]
        )
        result["tests"]["salary_software_engineer_dubai"] = {
            "status": "success",
            "job_title": test2_result.get("job_title"),
            "location": test2_result.get("location"),
            "estimated_range": test2_result.get("estimated_range"),
            "base_range": test2_result.get("base_range"),
            "sources_checked": test2_result.get("sources_checked", []),
            "data_points": test2_result.get("data_points", 0),
            "confidence": test2_result.get("confidence", 0),
            "skill_premium_applied": test2_result.get("skill_premium_applied", 0),
            "location_adjusted": test2_result.get("location_adjusted", False)
        }
        salary_range = test2_result.get("estimated_range", {})
        logger.info(f"✓ TEST 2: Salary range USD {salary_range.get('min', 'N/A')} - {salary_range.get('max', 'N/A')}")

    except Exception as e:
        logger.error(f"✗ TEST 2 FAILED: {e}")
        result["tests"]["salary_software_engineer_dubai"] = {"status": "failed", "error": str(e)}

    try:
        # Test 3: Salary synthesis for Data Scientist in Abu Dhabi
        logger.info("TEST 3: research_salary_synthesize('data scientist', 'Abu Dhabi, UAE')")
        test3_result = research_salary_synthesize(
            job_title="data scientist",
            location="Abu Dhabi, UAE",
            skills=["Machine Learning", "AI", "Python"]
        )
        result["tests"]["salary_data_scientist_abudhabi"] = {
            "status": "success",
            "job_title": test3_result.get("job_title"),
            "location": test3_result.get("location"),
            "estimated_range": test3_result.get("estimated_range"),
            "base_range": test3_result.get("base_range"),
            "sources_checked": test3_result.get("sources_checked", []),
            "data_points": test3_result.get("data_points", 0),
            "confidence": test3_result.get("confidence", 0),
            "skill_premium_applied": test3_result.get("skill_premium_applied", 0),
            "location_adjusted": test3_result.get("location_adjusted", False)
        }
        salary_range = test3_result.get("estimated_range", {})
        logger.info(f"✓ TEST 3: Salary range USD {salary_range.get('min', 'N/A')} - {salary_range.get('max', 'N/A')}")

    except Exception as e:
        logger.error(f"✗ TEST 3 FAILED: {e}")
        result["tests"]["salary_data_scientist_abudhabi"] = {"status": "failed", "error": str(e)}

    try:
        # Test 4: Market velocity for software engineering in Dubai
        logger.info("TEST 4: research_market_velocity('software engineering', 'Dubai, UAE')")
        test4_result = research_market_velocity(
            skill="software engineering",
            location="Dubai, UAE"
        )
        result["tests"]["market_velocity_software_dubai"] = {
            "status": "success",
            "skill": test4_result.get("skill"),
            "location": test4_result.get("location"),
            "github_momentum": test4_result.get("github_momentum", {}),
            "discussion_velocity": {
                "recent_discussions": test4_result.get("discussion_velocity", {}).get("recent_discussions"),
                "avg_points_per_story": test4_result.get("discussion_velocity", {}).get("avg_points_per_story")
            },
            "academic_momentum": {
                "total_papers": test4_result.get("academic_momentum", {}).get("total_papers"),
                "avg_papers_per_month": test4_result.get("academic_momentum", {}).get("avg_papers_per_month")
            },
            "overall_velocity": test4_result.get("overall_velocity"),
            "demand_trend": test4_result.get("demand_trend"),
            "confidence_score": test4_result.get("confidence_score")
        }
        logger.info(f"✓ TEST 4: Market velocity = {test4_result.get('overall_velocity')}, Demand = {test4_result.get('demand_trend')}")

    except Exception as e:
        logger.error(f"✗ TEST 4 FAILED: {e}")
        result["tests"]["market_velocity_software_dubai"] = {"status": "failed", "error": str(e)}

    return result


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("REQ-004: Top Paying Jobs UAE with Accurate Data")
    logger.info("=" * 80)
    logger.info("")

    # Run tests
    result = run_req004()
    result["status"] = "completed"

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for test in result.get("tests", {}).values() if test.get("status") == "success")
    failed = sum(1 for test in result.get("tests", {}).values() if test.get("status") == "failed")

    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")

    # Validate acceptance criteria
    logger.info("\n" + "=" * 80)
    logger.info("ACCEPTANCE CRITERIA CHECK")
    logger.info("=" * 80)

    criteria = {
        "salary_data_present": False,
        "job_titles_listed": False,
        "uae_specific_with_sources": False,
        "market_trends_included": False
    }

    tests = result.get("tests", {})

    # Check 1: Salary data present
    if "salary_software_engineer_dubai" in tests and tests["salary_software_engineer_dubai"].get("status") == "success":
        salary_range = tests["salary_software_engineer_dubai"].get("estimated_range", {})
        if salary_range.get("min") and salary_range.get("max"):
            criteria["salary_data_present"] = True
            logger.info("✓ Salary data present (Software Engineer: ${} - ${})".format(
                salary_range.get("min"), salary_range.get("max")
            ))

    if "salary_data_scientist_abudhabi" in tests and tests["salary_data_scientist_abudhabi"].get("status") == "success":
        salary_range = tests["salary_data_scientist_abudhabi"].get("estimated_range", {})
        if salary_range.get("min") and salary_range.get("max"):
            criteria["salary_data_present"] = True
            logger.info("✓ Salary data present (Data Scientist: ${} - ${})".format(
                salary_range.get("min"), salary_range.get("max")
            ))

    # Check 2: Job titles listed
    if "multi_search" in tests and tests["multi_search"].get("status") == "success":
        results = tests["multi_search"].get("results_sample", [])
        if any(r.get("title") for r in results):
            criteria["job_titles_listed"] = True
            logger.info("✓ Job titles listed from multi-search results")
            for r in results:
                if r.get("title"):
                    logger.info(f"    - {r.get('title')[:60]}")

    # Check 3: UAE-specific with sources
    if "salary_software_engineer_dubai" in tests and tests["salary_software_engineer_dubai"].get("status") == "success":
        location = tests["salary_software_engineer_dubai"].get("location")
        sources = tests["salary_software_engineer_dubai"].get("sources_checked", [])
        if ("Dubai" in location or "UAE" in location) and sources:
            criteria["uae_specific_with_sources"] = True
            logger.info(f"✓ UAE-specific data with sources: {sources}")

    # Check 4: Market trends included
    if "market_velocity_software_dubai" in tests and tests["market_velocity_software_dubai"].get("status") == "success":
        trend = tests["market_velocity_software_dubai"].get("demand_trend")
        velocity = tests["market_velocity_software_dubai"].get("overall_velocity")
        if trend and velocity:
            criteria["market_trends_included"] = True
            logger.info(f"✓ Market trends included: {velocity} velocity, {trend} demand")

    logger.info("\n" + "-" * 80)
    passed_criteria = sum(1 for v in criteria.values() if v)
    logger.info(f"Acceptance Criteria Passed: {passed_criteria}/{len(criteria)}")
    for criterion, passed_check in criteria.items():
        status = "✓" if passed_check else "✗"
        logger.info(f"  {status} {criterion}")

    # Save full result
    output_path = Path("/opt/research-toolbox/tmp/req004_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    logger.info("\n" + "=" * 80)
    logger.info(f"Full results saved to: {output_path}")
    logger.info("=" * 80)

    # Print key findings
    logger.info("\nKEY FINDINGS:")
    logger.info("-" * 80)

    if "salary_software_engineer_dubai" in tests and tests["salary_software_engineer_dubai"].get("status") == "success":
        test = tests["salary_software_engineer_dubai"]
        logger.info("\nSoftware Engineer - Dubai, UAE:")
        logger.info(f"  Estimated Range: ${test['estimated_range']['min']:,} - ${test['estimated_range']['max']:,}")
        logger.info(f"  Confidence: {test['confidence']*100:.0f}%")
        logger.info(f"  Data Points: {test['data_points']}")
        logger.info(f"  Sources: {', '.join(test['sources_checked'])}")

    if "salary_data_scientist_abudhabi" in tests and tests["salary_data_scientist_abudhabi"].get("status") == "success":
        test = tests["salary_data_scientist_abudhabi"]
        logger.info("\nData Scientist - Abu Dhabi, UAE:")
        logger.info(f"  Estimated Range: ${test['estimated_range']['min']:,} - ${test['estimated_range']['max']:,}")
        logger.info(f"  Confidence: {test['confidence']*100:.0f}%")
        logger.info(f"  Data Points: {test['data_points']}")
        logger.info(f"  Sources: {', '.join(test['sources_checked'])}")

    if "market_velocity_software_dubai" in tests and tests["market_velocity_software_dubai"].get("status") == "success":
        test = tests["market_velocity_software_dubai"]
        logger.info("\nMarket Velocity - Software Engineering, Dubai:")
        logger.info(f"  Overall Velocity: {test['overall_velocity']}")
        logger.info(f"  Demand Trend: {test['demand_trend']}")
        logger.info(f"  GitHub Stars: {test['github_momentum']['total_stars']:,}")
        logger.info(f"  Academic Papers: {test['academic_momentum']['total_papers']}")

    logger.info("\n" + "=" * 80)

    return 0 if (failed == 0 and passed_criteria >= 3) else 1


if __name__ == "__main__":
    sys.exit(main())
