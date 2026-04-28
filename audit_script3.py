import os
import ast
import sys
import importlib
import re

FILES_TO_CHECK = [
    "src/loom/tools/dead_content.py",
    "src/loom/tools/invisible_web.py",
    "src/loom/tools/js_intel.py",
    "src/loom/tools/multi_search.py",
    "src/loom/tools/passive_recon.py",
    "src/loom/tools/metadata_forensics.py",
    "src/loom/tools/dark_forum.py",
    "src/loom/tools/infra_correlator.py",
    "src/loom/tools/crypto_trace.py",
    "src/loom/tools/stego_detect.py",
    "src/loom/tools/threat_profile.py",
    "src/loom/tools/social_graph.py",
    "src/loom/tools/leak_scan.py",
    "src/loom/tools/onion_discover.py",
    "src/loom/tools/vuln_intel.py",
    "src/loom/tools/change_monitor.py",
    "src/loom/tools/identity_resolve.py",
    "src/loom/tools/competitive_intel.py",
    "src/loom/tools/knowledge_graph.py",
    "src/loom/tools/fact_checker.py",
    "src/loom/tools/trend_predictor.py",
    "src/loom/tools/report_generator.py",
    "src/loom/tools/realtime_monitor.py",
    "src/loom/tools/ai_safety.py",
    "src/loom/tools/ai_safety_extended.py",
    "src/loom/tools/academic_integrity.py",
    "src/loom/tools/career_trajectory.py",
    "src/loom/tools/job_signals.py",
    "src/loom/tools/signal_detection.py",
    "src/loom/tools/supply_chain_intel.py",
    "src/loom/tools/darkweb_early_warning.py",
    "src/loom/tools/culture_dna.py",
    "src/loom/tools/synth_echo.py",
    "src/loom/tools/psycholinguistic.py",
    "src/loom/tools/bias_lens.py",
    "src/loom/tools/osint_extended.py",
    "src/loom/tools/salary_synthesizer.py",
    "src/loom/tools/deception_job_scanner.py",
    "src/loom/tools/hcs10_academic.py",
    "src/loom/tools/threat_intel.py",
    "src/loom/tools/infra_analysis.py",
    "src/loom/tools/gap_tools_infra.py",
    "src/loom/tools/gap_tools_academic.py",
    "src/loom/tools/gap_tools_ai.py",
    "src/loom/tools/gap_tools_advanced.py",
    "src/loom/tools/infowar_tools.py",
    "src/loom/tools/access_tools.py",
    "src/loom/tools/unique_tools.py",
    "src/loom/tools/p3_tools.py"
]

SERVER_FILE = "src/loom/server.py"

try:
    with open(SERVER_FILE, "r") as f:
        server_code = f.read()
except FileNotFoundError:
    server_code = ""

total_pass = 0
total_fail = 0
critical_issues = []

sys.path.insert(0, os.path.abspath("src"))

for filepath in FILES_TO_CHECK:
    if not os.path.exists(filepath):
        print(f"FILE: {filepath}")
        print("FUNCTIONS: []")
        print("IMPLEMENTATION: PLACEHOLDER")
        print("API_KEYS_NEEDED: NONE")
        print("SPECIAL_DEPS: NONE")
        print("REGISTERED: NO")
        print("IMPORTABLE: NO")
        print("VERDICT: FAIL [File does not exist]")
        print("-" * 40)
        total_fail += 1
        critical_issues.append(f"{filepath} does not exist")
        continue

    with open(filepath, "r") as f:
        code = f.read()
    
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        print(f"FILE: {filepath}")
        print("VERDICT: FAIL [Syntax Error]")
        print("-" * 40)
        total_fail += 1
        critical_issues.append(f"{filepath} Syntax Error: {e}")
        continue

    functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    tool_funcs = [f for f in functions if not f.name.startswith("_") and (f.name.startswith("research_") or "tool" in code or f.name in server_code)]
    
    # If no tool functions found by prefix, just use all non-private top-level functions
    if not tool_funcs:
        tool_funcs = [f for f in functions if not f.name.startswith("_")]

    func_names = [f.name for f in tool_funcs]
    
    implementation = "FULL"
    issues = []
    api_keys = set()
    special_deps = set()
    
    # Check imports
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split('.')[0]
                if name not in sys.stdlib_module_names and name not in ['loom']:
                    special_deps.add(name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                name = node.module.split('.')[0]
                if name not in sys.stdlib_module_names and name not in ['loom']:
                    special_deps.add(name)
                    
    # API Keys & Tor
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ['get', 'getenv']:
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'environ':
                    pass # handled below
                if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == 'environ':
                    if node.args and isinstance(node.args[0], ast.Constant):
                        api_keys.add(node.args[0].value)
            if isinstance(node.func, ast.Name) and node.func.id == 'getenv':
                if node.args and isinstance(node.args[0], ast.Constant):
                    api_keys.add(node.args[0].value)

    if 'API_KEY' in code:
        keys = re.findall(r'[\'"]([A-Z0-9_]*API_KEY[A-Z0-9_]*)[\'"]', code)
        api_keys.update(keys)

    if '.onion' in code or 'socks5' in code.lower() or 'tor' in code.lower():
        special_deps.add('tor/socks5')

    for func in tool_funcs:
        # Check docstring
        if not ast.get_docstring(func):
            issues.append(f"{func.name} missing docstring")
        
        # Check type hints
        if not func.returns:
            issues.append(f"{func.name} missing return type hint")
        for arg in func.args.args:
            if arg.arg != 'self' and not arg.annotation:
                issues.append(f"{func.name} missing type hint for {arg.arg}")
                
        # Check error handling
        has_try = any(isinstance(n, ast.Try) for n in ast.walk(func))
        if not has_try:
            issues.append(f"{func.name} missing try/except block")
            
        # Check real endpoints (just heuristic - looks for http/https in code)
        func_code = ast.unparse(func)
        if 'http://' not in func_code and 'https://' not in func_code and 'requests.' not in func_code and 'httpx.' not in func_code and 'aiohttp.' not in func_code:
            # Maybe it does local processing, or maybe placeholder
            if 'pass' in func_code or 'return {}' in func_code or 'TODO' in func_code:
                implementation = "PLACEHOLDER" if implementation == "FULL" else implementation
                
        if 'pass' in [ast.unparse(n) for n in func.body]:
            implementation = "PLACEHOLDER"
        elif 'TODO' in func_code or 'dummy' in func_code.lower():
            implementation = "PARTIAL"

    # Check registration
    registered_funcs = [fn for fn in func_names if fn in server_code]
    is_registered = "YES" if len(registered_funcs) == len(func_names) and len(func_names) > 0 else "NO"
    if is_registered == "NO" and len(func_names) > 0:
        issues.append("Not all functions registered in server.py")

    # Check importable
    module_name = filepath.replace('src/', '').replace('.py', '').replace('/', '.')
    is_importable = "YES"
    try:
        mod = importlib.import_module(module_name)
        for fn in func_names:
            if not hasattr(mod, fn):
                is_importable = "NO"
                issues.append(f"Function {fn} not found in imported module")
    except Exception as e:
        is_importable = "NO"
        issues.append(f"Import failed: {str(e)}")

    if issues or implementation in ["PLACEHOLDER", "PARTIAL"] or is_registered == "NO" or is_importable == "NO":
        verdict = f"FAIL [{', '.join(issues)}]"
        if not issues:
            verdict = f"FAIL [{implementation}]"
        total_fail += 1
    else:
        verdict = "PASS"
        total_pass += 1
        
    print(f"FILE: {filepath}")
    print(f"FUNCTIONS: {', '.join(func_names) if func_names else 'NONE'}")
    print(f"IMPLEMENTATION: {implementation}")
    print(f"API_KEYS_NEEDED: {', '.join(api_keys) if api_keys else 'NONE'}")
    print(f"SPECIAL_DEPS: {', '.join(special_deps) if special_deps else 'NONE'}")
    print(f"REGISTERED: {is_registered}")
    print(f"IMPORTABLE: {is_importable}")
    print(f"VERDICT: {verdict}")
    print("-" * 40)

print("\nSUMMARY:")
print(f"Total PASS: {total_pass}")
print(f"Total FAIL: {total_fail}")
if critical_issues:
    print("\nCRITICAL ISSUES:")
    for issue in critical_issues:
        print(f"- {issue}")
