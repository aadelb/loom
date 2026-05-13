"""Data Pipeline Builder for ETL-style research workflows."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.data_pipeline")


def _pipeline_dir() -> Path:
    """Get or create ~/.loom/pipelines directory."""
    d = Path.home() / ".loom" / "pipelines"
    d.mkdir(parents=True, exist_ok=True)
    return d


@handle_tool_errors("research_pipeline_create")
async def research_pipeline_create(name: str, stages: list[dict[str, Any]]) -> dict[str, Any]:
    """Create and store an ETL pipeline definition."""
    try:
        if not name or not name.replace("_", "").isalnum():
            raise ValueError("Pipeline name must be alphanumeric + underscore")
        if not stages or len(stages) > 50:
            raise ValueError("Pipeline must have 1-50 stages")

        valid_types = {"extract", "transform", "load"}
        for stage in stages:
            if not all(k in stage for k in ["name", "type", "tool", "params"]):
                raise ValueError("Stage missing: name, type, tool, params")
            if stage["type"] not in valid_types or not isinstance(stage.get("params"), dict):
                raise ValueError(f"Invalid stage: type={stage.get('type')}")

        pipeline = {
            "name": name,
            "version": "1.0",
            "created": datetime.now(UTC).isoformat(),
            "stages": stages,
        }

        path = _pipeline_dir() / f"{name}.json"
        path.write_text(json.dumps(pipeline, indent=2))
        return {"pipeline_name": name, "stages_count": len(stages), "saved": True, "path": str(path)}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_pipeline_create"}


@handle_tool_errors("research_pipeline_validate")
async def research_pipeline_validate(name: str) -> dict[str, Any]:
    """Validate pipeline definition."""
    try:
        path = _pipeline_dir() / f"{name}.json"
        if not path.exists():
            return {"valid": False, "issues": [f"Not found: {name}"], "warnings": [], "estimated_duration_minutes": 0}

        pipeline = json.loads(path.read_text())
        issues, warnings = [], []
        stage_types = [s.get("type") for s in pipeline.get("stages", [])]

        e_idx = next((i for i, t in enumerate(stage_types) if t == "extract"), -1)
        t_idx = next((i for i, t in enumerate(stage_types) if t == "transform"), -1)
        l_idx = next((i for i, t in enumerate(stage_types) if t == "load"), -1)

        if e_idx == -1:
            issues.append("No extract stage found")
        if l_idx == -1:
            warnings.append("No load stage found")
        if e_idx >= 0 and t_idx >= 0 and e_idx > t_idx:
            issues.append("Extract must come before transform")
        if t_idx >= 0 and l_idx >= 0 and t_idx > l_idx:
            issues.append("Transform must come before load")

        estimated = sum(2 if t == "extract" else 1 if t in ("transform", "load") else 0 for t in stage_types)
        return {"valid": not issues, "issues": issues, "warnings": warnings, "estimated_duration_minutes": estimated}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_pipeline_validate"}


@handle_tool_errors("research_pipeline_list")
async def research_pipeline_list() -> dict[str, Any]:
    """List all defined pipelines."""
    try:
        pipelines = []
        for path in sorted(_pipeline_dir().glob("*.json")):
            try:
                data = json.loads(path.read_text())
                pipelines.append({
                    "name": data.get("name"),
                    "stages_count": len(data.get("stages", [])),
                    "created": data.get("created"),
                    "last_run": None,
                })
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Parse failed %s: %s", path.name, e)
        return {"pipelines": pipelines, "total": len(pipelines)}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_pipeline_list"}
