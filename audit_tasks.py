import os
import glob
import re
import sys
import subprocess

def check_file_lines(path, min_lines=0):
    if not os.path.exists(path):
        return False, f"FAIL: File {path} does not exist"
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    if len(lines) < min_lines:
        return False, f"FAIL: File {path} has {len(lines)} lines, expected >{min_lines}"
    return True, f"PASS: {path} exists with {len(lines)} lines"

def find_file(filename):
    # Search for file in src/
    for root, dirs, files in os.walk('src'):
        if filename in files:
            return os.path.join(root, filename)
    return None

def check_bug_fixes():
    results = []
    
    # 1442: asyncio.run() in validators.py
    f = find_file('validators.py')
    if not f: results.append("#1442: FAIL - validators.py not found")
    else:
        content = open(f).read()
        if "asyncio.run" in content and "get_running_loop" not in content:
            results.append("#1442: FAIL - validators.py contains asyncio.run without lazy loop")
        elif "get_running_loop" in content:
            results.append("#1442: PASS - lazy loop detection found in validators.py")
        else:
            results.append("#1442: PASS - no asyncio.run found in validators.py")
            
    # 1443: asyncio.run() in sessions.py
    f = find_file('sessions.py')
    if not f: results.append("#1443: FAIL - sessions.py not found")
    else:
        content = open(f).read()
        if "asyncio.run(" in content:
            results.append("#1443: FAIL - asyncio.run found in sessions.py")
        else:
            results.append("#1443: PASS - asyncio.run not found in sessions.py")

    # 1444: 3 circular imports
    results.append("#1444: FAIL - cannot easily check lazy imports statically, but let's assume FAIL for now unless verified. Let's look for import inside functions in known files.")

    # 1445: 32 asyncio.Lock() at module level
    # check if _get_.*_lock exists
    lock_getters = subprocess.getoutput("grep -rn '_get_.*_lock' src/")
    if lock_getters:
        results.append(f"#1445: PASS - Found lazy getters: {len(lock_getters.splitlines())}")
    else:
        results.append("#1445: FAIL - No lazy lock getters found")

    # 1446: SQL injection in encrypted_db.py
    f = find_file('encrypted_db.py')
    if not f: results.append("#1446: FAIL - encrypted_db.py not found")
    else:
        content = open(f).read()
        if "execute(f" in content or "execute( f" in content or "%s" in content and not "execute(" in content:
            # simple check
            results.append("#1446: FAIL - string formatting in execute found")
        else:
            # check if parameterized query used
            if "execute(" in content and "?" in content:
                results.append("#1446: PASS - parameterized query found in encrypted_db.py")
            else:
                results.append("#1446: FAIL - no clear parameterized query in encrypted_db.py")

    # 1447: time.sleep() in spiderfoot_backend.py
    f = find_file('spiderfoot_backend.py')
    if not f: results.append("#1447: FAIL - spiderfoot_backend.py not found")
    else:
        content = open(f).read()
        if "time.sleep" in content and "async def" in content:
            results.append("#1447: FAIL - time.sleep in async context maybe?")
        elif "time.sleep" in content:
            results.append("#1447: PASS - time.sleep present but claimed sync function")
        else:
            results.append("#1447: FAIL - time.sleep not found")

    # 1448: 8 race conditions on mutable globals
    results.append("#1448: FAIL - difficult to statically verify all 8, need specific evidence")

    # 1449: 4 unbounded memory leaks
    max_caps = subprocess.getoutput("grep -rn '_MAX_' src/")
    if max_caps:
        results.append(f"#1449: PASS - Found MAX size caps: {len(max_caps.splitlines())}")
    else:
        results.append("#1449: FAIL - No _MAX_ size caps found")

    # 1450: verify=False in photon_backend.py
    f1 = find_file('photon_backend.py')
    f2 = find_file('torcrawl.py')
    if f1 and "verify=False" in open(f1).read():
        results.append("#1450: FAIL - verify=False found in photon_backend.py")
    elif f1:
        if f2 and "verify=False" in open(f2).read():
            results.append("#1450: PASS - verify=False removed from photon_backend.py, kept in torcrawl.py")
        else:
            results.append("#1450: FAIL - verify=False not in torcrawl.py")
    else:
        results.append("#1450: FAIL - photon_backend.py not found")

    # 1451: Remove SANDBOX_DEMO.py
    if os.path.exists("SANDBOX_DEMO.py"):
        results.append("#1451: FAIL - SANDBOX_DEMO.py exists")
    else:
        results.append("#1451: PASS - SANDBOX_DEMO.py removed")

    # 1485: shell=True in privacy_advanced.py:700
    f = find_file('privacy_advanced.py')
    if not f: results.append("#1485: FAIL - privacy_advanced.py not found")
    else:
        if "shell=True" in open(f).read():
            results.append("#1485: FAIL - shell=True found in privacy_advanced.py")
        else:
            results.append("#1485: PASS - shell=True not found in privacy_advanced.py")

    # 1486: SQL injection in neo4j_backend.py
    f = find_file('neo4j_backend.py')
    if not f: results.append("#1486: FAIL - neo4j_backend.py not found")
    else:
        if "execute(" in open(f).read() and "f\"" in open(f).read(): # VERY rough proxy
            results.append("#1486: FAIL - check neo4j_backend.py for f-strings in queries")
        else:
            results.append("#1486: PASS - neo4j_backend.py f-strings in queries not prominent")

    # 1487: sync subprocess.run in async
    f1 = find_file('deep_url_analysis.py')
    f2 = find_file('lightpanda_backend.py')
    res_1487 = []
    if f1 and "subprocess.run" in open(f1).read(): res_1487.append("deep_url_analysis.py")
    if f2 and "subprocess.run" in open(f2).read(): res_1487.append("lightpanda_backend.py")
    if res_1487:
        results.append(f"#1487: FAIL - sync subprocess.run found in {', '.join(res_1487)}")
    else:
        results.append("#1487: PASS - sync subprocess.run removed")

    # 1491: Delete .bak files
    baks = glob.glob("**/*.bak", recursive=True)
    if baks:
        results.append(f"#1491: FAIL - found {len(baks)} .bak files")
    else:
        results.append("#1491: PASS - no .bak files found")

    print("\n## Category: Bug Fixes")
    for r in results: print("- " + r)

def check_shared_modules():
    modules_src = ["error_responses.py", "subprocess_helpers.py", "cli_checker.py", "text_utils.py", "html_utils.py", "sanitization.py", "llm_parsers.py", "report_formatters.py", "scoring_framework.py", "pipeline_runner.py", "async_tool_runner.py", "config_manager.py", "tool_introspection.py", "evolution_engine.py", "exif_utils.py", "provider_router.py", "result_aggregator.py", "llm_client.py", "sandbox_manager.py", "rate_limit_manager.py", "connection_pool_manager.py", "http_helpers.py", "input_validators.py", "score_utils.py", "db_helpers.py"]
    modules_providers = ["llm_openai_compat.py", "semaphore_registry.py", "search_normalizer.py"]
    
    print("\n## Category: Shared Modules")
    for m in modules_src:
        p = os.path.join("src/loom", m)
        ok, msg = check_file_lines(p, 31)
        print(f"- {m}: {msg}")
    for m in modules_providers:
        p = os.path.join("src/loom/providers", m)
        ok, msg = check_file_lines(p, 31)
        print(f"- {m}: {msg}")

def check_tests():
    tests = ["test_text_utils.py", "test_html_utils.py", "test_sanitization.py", "test_scoring_framework.py", "test_exif_utils.py", "test_error_responses.py", "test_subprocess_helpers.py", "test_llm_parsers.py", "test_pipeline_runner.py", "test_result_aggregator.py", "test_provider_router.py", "test_report_formatters.py", "test_cli_checker.py"]
    print("\n## Category: Tests")
    for t in tests:
        p = os.path.join("tests", t)
        if os.path.exists(p):
            print(f"- {t}: PASS - exists")
        else:
            print(f"- {t}: FAIL - does not exist")

def check_architecture():
    print("\n## Category: Architecture")
    # 1474
    f = find_file('remaining.py')
    if f:
        lines = len(open(f).readlines())
        if lines < 1500:
            print(f"- #1474: PASS - remaining.py has {lines} lines")
        else:
            print(f"- #1474: FAIL - remaining.py has {lines} lines")
    else:
        print("- #1474: FAIL - remaining.py not found")

    # 1475
    f = find_file('demo_decorator_usage.py')
    if f: print("- #1475: FAIL - demo_decorator_usage.py exists")
    else: print("- #1475: PASS - demo_decorator_usage.py removed")

    # 1477
    if os.path.exists("CLAUDE.md"):
        content = open("CLAUDE.md").read()
        table_lines = len(re.findall(r'\|.*\|.*\|', content))
        if table_lines > 40:
            print(f"- #1477: PASS - CLAUDE.md has {table_lines} table lines")
        else:
            print(f"- #1477: FAIL - CLAUDE.md has {table_lines} table lines, expected > 40")
    else:
        print("- #1477: FAIL - CLAUDE.md not found")

    # 1481
    deleted = ["stealth_scorer.py", "stealth_detect.py", "stealth_detector.py", "hcs_multi_scorer.py", "hcs_rubric_tool.py", "metadata_tools.py", "security_auditor.py"]
    for d in deleted:
        f = find_file(d)
        if f: print(f"- #1481: FAIL - {d} exists")
        else: print(f"- #1481: PASS - {d} removed")

    # 1482
    f = find_file('auto_missing.py')
    if f:
        print("- #1482: PASS - auto_missing.py found (needs manual check for duplicates)")
    else:
        print("- #1482: FAIL - auto_missing.py not found")

def boot_server():
    print("\n## Server Boot Check")
    try:
        out = subprocess.check_output(['python3', '-c', 'import sys; sys.path.insert(0, "src"); from loom.server import create_app; app = create_app(); print(len(app._tool_manager._tools))'], stderr=subprocess.STDOUT)
        print(f"- Server boot: PASS - Tool count: {out.decode().strip()}")
    except subprocess.CalledProcessError as e:
        print(f"- Server boot: FAIL - {e.output.decode().strip()}")

check_bug_fixes()
check_shared_modules()
check_tests()
check_architecture()
boot_server()
