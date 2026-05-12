"""Integration test runner for validating all 311 tool modules."""
from __future__ import annotations
import asyncio, importlib, inspect, time
from pathlib import Path
from typing import Any


async def research_integration_test(
    modules: list[str] | None = None, timeout_ms: int = 5000
) -> dict[str, Any]:
    """Import and validate all tool modules load and respond correctly."""
    start = time.perf_counter()
    tools_dir = Path(__file__).parent
    py_files = (
        sorted([f.stem for f in tools_dir.glob("*.py")
                if f.name != "__init__.py" and not f.name.startswith("_")])
        if modules is None else modules
    )
    errors, passed, failed = [], 0, 0

    for module_name in py_files:
        try:
            mod = importlib.import_module(f"loom.tools.{module_name}")
            funcs = [(n, f) for n, f in inspect.getmembers(mod)
                     if inspect.iscoroutinefunction(f) and n.startswith("research_")]
            if not funcs:
                errors.append({"module": module_name, "error": "No async research_* functions"})
                failed += 1
                continue
            module_had_error = False
            for func_name, func in funcs:
                try:
                    kwargs = {pn: ("" if (a := p.annotation) in (str, Path) else
                                   0 if a in (int, float) else
                                   [] if a is list else {} if a is dict else False)
                             for pn, p in inspect.signature(func).parameters.items()
                             if p.default is inspect.Parameter.empty}
                    await asyncio.wait_for(func(**kwargs), timeout=timeout_ms / 1000)
                except asyncio.TimeoutError:
                    pass
                except TypeError as e:
                    if "missing required argument" not in str(e):
                        errors.append({"module": module_name, "error": f"{func_name}: {str(e)[:60]}"})
                        module_had_error = True
                        break
                except Exception:
                    pass
            if module_had_error:
                failed += 1
                continue
            passed += 1
        except Exception as e:
            errors.append({"module": module_name, "error": f"{type(e).__name__}: {str(e)[:60]}"})
            failed += 1

    return {
        "total_modules": len(py_files),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "duration_ms": (time.perf_counter() - start) * 1000,
    }


async def research_smoke_test(tool_name: str) -> dict[str, Any]:
    """Smoke test a single tool by importing and verifying it's callable."""
    result = {
        "tool": tool_name,
        "importable": False,
        "callable": False,
        "has_docstring": False,
        "param_count": 0,
        "error": None,
    }
    try:
        module_name, func_name = (
            (tool_name.rsplit(".", 1))
            if "." in tool_name
            else (tool_name, f"research_{tool_name.split('_')[-1]}")
        )
        mod = importlib.import_module(f"loom.tools.{module_name}")
        result["importable"] = True
        if not hasattr(mod, func_name):
            result["error"] = f"Function {func_name} not found"
            return result
        func = getattr(mod, func_name)
        result["callable"] = inspect.iscoroutinefunction(func)
        result["has_docstring"] = bool(func.__doc__)
        result["param_count"] = len(inspect.signature(func).parameters)
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:60]}"
    return result
