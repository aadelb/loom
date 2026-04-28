import ast
import os
import sys
import importlib
from pathlib import Path

src_dir = Path("src").resolve()
sys.path.insert(0, str(src_dir))

def audit():
    issues = []

    # 1. ANY tool functions defined in src/loom/tools/*.py that are NOT registered in server.py
    try:
        from loom.server import create_app
        app = create_app()
        registered = {t.name for t in app._tool_manager._tools.values()}
        
        defined_tools = set()
        tools_dir = Path('src/loom/tools')
        for py_file in tools_dir.glob('*.py'):
            if py_file.name.startswith('_'): continue
            mod_name = f"loom.tools.{py_file.stem}"
            try:
                mod = importlib.import_module(mod_name)
                for name, obj in vars(mod).items():
                    if callable(obj) and getattr(obj, '__module__', '') == mod_name:
                        if name.startswith('research_') or name.startswith('find_') or name.startswith('fetch_'):
                            defined_tools.add(name)
            except Exception as e:
                pass
                
        # FastMCP uses the function name, but it might strip `research_` or convert `_` to `-`.
        # Let's check if the function is registered by seeing if it's explicitly wrapped in server.py
        server_py = Path("src/loom/server.py").read_text()
        import re
        wrapped = set(re.findall(r'_wrap_tool\([^.]+\.([a-zA-Z0-9_]+)', server_py))
        wrapped.update(re.findall(r'_wrap_tool\((research_[a-zA-Z0-9_]+)', server_py))
        wrapped.update(re.findall(r'hasattr\([^,]+,\s*"([^"]+)"\)', server_py))
        
        for t in sorted(defined_tools - wrapped):
            issues.append(f"1. Unregistered tool function: {t}")
    except Exception as e:
        issues.append(f"Error in check 1: {e}")

    # 2. ANY provider functions in src/loom/providers/*.py that are NOT routed in search.py
    try:
        defined_provs = set()
        prov_dir = Path('src/loom/providers')
        for py_file in prov_dir.glob('*.py'):
            if py_file.name.startswith('_'): continue
            mod_name = f"loom.providers.{py_file.stem}"
            try:
                mod = importlib.import_module(mod_name)
                for name, obj in vars(mod).items():
                    if callable(obj) and getattr(obj, '__module__', '') == mod_name:
                        if name.startswith('search_') or name.startswith('crawl_'):
                            defined_provs.add(name)
            except Exception as e:
                pass
                
        search_py = Path("src/loom/tools/search.py").read_text()
        for p in sorted(defined_provs):
            if p not in search_py:
                issues.append(f"2. Provider function not routed in search.py: {p}")
    except Exception as e:
        issues.append(f"Error in check 2: {e}")

    # 3. ANY config keys defined in config.py that are NOT used anywhere
    try:
        config_py = Path("src/loom/config.py").read_text()
        # Find dictionary keys in DEFAULT_CONFIG
        keys = re.findall(r'"([A-Z0-9_]+)"\s*:', config_py)
        
        all_code = ""
        for py in Path("src/loom").rglob("*.py"):
            if py.name != "config.py":
                all_code += py.read_text()
                
        for k in keys:
            if f'"{k}"' not in all_code and f"'{k}'" not in all_code:
                # also check config.get("KEY")
                issues.append(f"3. Unused config key: {k}")
    except Exception as e:
        issues.append(f"Error in check 3: {e}")

    # 4. ANY env vars referenced in code that are NOT in api-keys.md
    try:
        all_code = ""
        for py in Path("src/loom").rglob("*.py"):
            all_code += py.read_text()
            
        env_vars = set(re.findall(r'os\.environ\.get\("([A-Z0-9_]+)"', all_code))
        env_vars.update(re.findall(r'os\.getenv\("([A-Z0-9_]+)"', all_code))
        env_vars.update(re.findall(r'os\.environ\["([A-Z0-9_]+)"\]', all_code))
        
        api_keys_md = Path("docs/api-keys.md").read_text()
        for ev in sorted(env_vars):
            if ev not in api_keys_md:
                issues.append(f"4. Undocumented env var: {ev}")
    except Exception as e:
        issues.append(f"Error in check 4: {e}")

    # 5. ANY test files that import deleted/renamed functions
    try:
        # Parse all test files and check if imported names exist in the module
        for test_file in Path("tests").rglob("test_*.py"):
            try:
                tree = ast.parse(test_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("loom."):
                        try:
                            mod = importlib.import_module(node.module)
                            for alias in node.names:
                                if not hasattr(mod, alias.name):
                                    issues.append(f"5. Test file {test_file.name} imports missing function '{alias.name}' from {node.module}")
                        except ImportError:
                            issues.append(f"5. Test file {test_file.name} imports missing module '{node.module}'")
            except Exception:
                pass
                
        for test_file in Path(".").glob("test_*.py"):
            try:
                tree = ast.parse(test_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("loom."):
                        try:
                            mod = importlib.import_module(node.module)
                            for alias in node.names:
                                if not hasattr(mod, alias.name):
                                    issues.append(f"5. Test file {test_file.name} imports missing function '{alias.name}' from {node.module}")
                        except ImportError:
                            issues.append(f"5. Test file {test_file.name} imports missing module '{node.module}'")
            except Exception:
                pass
    except Exception as e:
        issues.append(f"Error in check 5: {e}")

    # 6. ANY imports in server.py that fail silently
    try:
        optional_modules = [
            "loom.tools.llm", "loom.tools.enrich", "loom.tools.experts", "loom.tools.creative",
            "loom.providers.youtube_transcripts", "loom.tools.vastai", "loom.tools.billing",
            "loom.tools.email_report", "loom.tools.joplin", "loom.tools.tor", "loom.tools.transcribe",
            "loom.tools.document", "loom.tools.metrics", "loom.tools.slack", "loom.tools.gcp",
            "loom.tools.vercel", "loom.tools.cipher_mirror", "loom.tools.forum_cortex",
            "loom.tools.onion_spectra", "loom.tools.ghost_weave", "loom.tools.dead_drop_scanner",
            "loom.tools.persona_profile", "loom.tools.radicalization_detect", "loom.tools.sentiment_deep",
            "loom.tools.network_persona", "loom.tools.text_analyze", "loom.tools.screenshot",
            "loom.tools.geoip_local", "loom.tools.image_intel", "loom.tools.ip_intel",
            "loom.tools.cve_lookup", "loom.tools.urlhaus_lookup"
        ]
        # To check if an import fails silently, we need to check if the file exists, but importlib fails
        for mod_name in optional_modules:
            mod_path = Path(f"src/{mod_name.replace('.', '/')}.py")
            mod_dir = Path(f"src/{mod_name.replace('.', '/')}")
            if mod_path.exists() or mod_dir.exists():
                try:
                    importlib.import_module(mod_name)
                except ImportError as e:
                    issues.append(f"6. Silent import failure for {mod_name}: {e}")
    except Exception as e:
        issues.append(f"Error in check 6: {e}")

    # 7. ANY CLI commands in cli.py that are broken or incomplete
    try:
        cli_py = Path("src/loom/cli.py").read_text()
        tree = ast.parse(cli_py)
        # Look for commands that might be missing their decorated functions or have missing imports
        # For simplicity, we just look for syntax/import errors in cli.py
        try:
            importlib.import_module("loom.cli")
        except Exception as e:
            issues.append(f"7. Broken CLI commands (cli.py fails to import): {e}")
            
        # check if there are `@cli.command()` missing implementation
        pass
    except Exception as e:
        issues.append(f"Error in check 7: {e}")

    # 8. ANY dead code — functions defined but never called
    # (This is hard to do statically perfectly, but let's check tools that are never wrapped)
    # Handled mainly by #1. We can also check helpers in src/loom/*.py

    print("=== AUDIT RESULTS ===")
    for issue in issues:
        print(issue)
        
    if not issues:
        print("No issues found.")

if __name__ == "__main__":
    audit()
