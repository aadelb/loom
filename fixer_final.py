import os
import re

files = [
    'src/loom/tools/academic_integrity.py',
    'src/loom/tools/access_tools.py',
    'src/loom/tools/adversarial_craft.py',
    'src/loom/tools/adversarial_debate_tool.py',
    'src/loom/tools/agent_benchmark.py',
    'src/loom/tools/ai_safety.py',
    'src/loom/tools/ai_safety_extended.py',
    'src/loom/tools/anomaly_detector.py',
    'src/loom/tools/antiforensics.py',
    'src/loom/tools/api_fuzzer.py',
    'src/loom/tools/api_version.py',
    'src/loom/tools/arxiv_pipeline.py',
    'src/loom/tools/ask_all_models.py',
    'src/loom/tools/attack_economy.py',
    'src/loom/tools/attack_scorer.py',
    'src/loom/tools/audit_log.py',
    'src/loom/tools/audit_query.py',
    'src/loom/tools/auto_docs.py',
    'src/loom/tools/auto_experiment.py',
    'src/loom/tools/auto_params.py'
]

for filepath in files:
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        original_content = content

        # 1. timeout=30.0
        def fix_httpx(match):
            m = match.group(0)
            if 'timeout' not in m:
                if m.endswith('()'):
                    return m[:-1] + 'timeout=30.0)'
                else:
                    return m[:-1] + ', timeout=30.0)'
            return m
        content = re.sub(r'httpx\.(?:Async)?Client\([^)]*\)', fix_httpx, content)

        # 2. wrap blocking calls
        content = re.sub(r'\brequests\.get\(', 'await asyncio.to_thread(requests.get, ', content)
        content = re.sub(r'\brequests\.post\(', 'await asyncio.to_thread(requests.post, ', content)
        content = re.sub(r'\btime\.sleep\(', 'await asyncio.to_thread(time.sleep, ', content)
        content = re.sub(r'open\(([^)]+)\)\.read\(\)', r'await asyncio.to_thread(lambda: open(\1).read())', content)

        # 3. bare except
        content = re.sub(r'\bexcept\s*:', 'except Exception as e:', content)

        # 4. Add return type hint
        def fix_research_return(match):
            m = match.group(0)
            if '->' not in m:
                return m.replace('):', ') -> dict[str, Any]:')
            return m
        content = re.sub(r'def\s+research_[a-zA-Z0-9_]+\([^)]*\):', fix_research_return, content)

        # 5. URL validation using regex DOTALL
        def inject_validate(match):
            m = match.group(0)
            func_name = match.group(1)
            # Find the indentation of the def
            lines = content.split('\n')
            indent = ""
            for line in lines:
                if line.lstrip().startswith(f"def {func_name}("):
                    indent = line[:len(line) - len(line.lstrip())]
                    break
            func_indent = indent + "    "
            
            if "from loom.validators import validate_url" not in content:
                inject = f"\n{func_indent}from loom.validators import validate_url\n{func_indent}validate_url(url)"
            else:
                inject = f"\n{func_indent}validate_url(url)"
                
            return m + inject

        # Find `def func_name(...url...):`
        content = re.sub(r'def\s+([a-zA-Z0-9_]+)\([^)]*\burl\b[^)]*\)\s*(?:->\s*[^:]+)?\s*:', inject_validate, content)

        # 6. Replace raise
        def fix_raise(match):
            indent = match.group(1)
            raise_stmt = match.group(2)
            
            pos = match.start()
            before = content[:pos]
            func_matches = list(re.finditer(r'def\s+([a-zA-Z0-9_]+)\(', before))
            func_name = func_matches[-1].group(1) if func_matches else "unknown"
            
            if raise_stmt == "raise":
                return f"{indent}return {{'error': str(e), 'error_code': 'internal', 'source': '{func_name}'}}"
            
            msg_match = re.search(r'raise\s+[a-zA-Z0-9_]+\((["\'])(.*?)\1\)', raise_stmt)
            if msg_match:
                msg = msg_match.group(2)
                return f"{indent}return {{'error': '{msg}', 'error_code': 'internal', 'source': '{func_name}'}}"
                
            return f"{indent}return {{'error': str(e) if 'e' in locals() else 'error', 'error_code': 'internal', 'source': '{func_name}'}}"

        content = re.sub(r'^(\s*)(raise\b.*?)$', fix_raise, content, flags=re.MULTILINE)

        if 'dict[str, Any]' in content and 'Any' not in content:
            content = "from typing import Any\n" + content

        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Modified {filepath}")
    except Exception as e:
        print(f"Failed {filepath}: {e}")
