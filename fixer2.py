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
        # Add timeout=30.0 to httpx.AsyncClient() or httpx.Client() if not present
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
        # open().read() is tricky, we'll try a naive approach
        content = re.sub(r'open\(([^)]+)\)\.read\(\)', r'await asyncio.to_thread(lambda: open(\1).read())', content)

        # 3. bare except
        content = re.sub(r'\bexcept\s*:', 'except Exception as e:', content)

        # 4. Add return type hint -> dict[str, Any] to research_* functions missing it
        def fix_research_return(match):
            m = match.group(0)
            if '->' not in m:
                return m.replace('):', ') -> dict[str, Any]:')
            return m
        content = re.sub(r'def\s+research_[a-zA-Z0-9_]+\([^)]*\):', fix_research_return, content)

        # 6. replace raise inside functions.
        # We will parse functions and look for `raise` inside them.
        lines = content.split('\n')
        in_func = False
        func_name = ""
        in_except = False
        new_lines = []
        for line in lines:
            func_match = re.search(r'def\s+([a-zA-Z0-9_]+)\(', line)
            if func_match:
                func_name = func_match.group(1)
                in_func = True
            
            if re.search(r'^\s*except ', line):
                in_except = True
            
            # Reset in_except on dedent - simplified, we'll just replace raise anywhere inside function
            raise_match = re.search(r'^(\s*)raise\b', line)
            if raise_match and func_name:
                indent = raise_match.group(1)
                # Ensure 'e' is available if possible, or just str(e)
                new_lines.append(f"{indent}return {{'error': str(e) if 'e' in locals() else 'error', 'error_code': 'internal', 'source': '{func_name}'}}")
                continue
                
            new_lines.append(line)
        content = '\n'.join(new_lines)

        # 5. URL validation. 
        # Add `from loom.validators import validate_url; validate_url(url)` for functions with URL string parameter
        # In this simplistic approach, we'll just look for `def ... url...:` and inject it.
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            func_match = re.search(r'def\s+[a-zA-Z0-9_]+\(.*?\burl\b.*?\):', line)
            if func_match:
                indent_match = re.search(r'^(\s*)def', line)
                base_indent = indent_match.group(1) if indent_match else ""
                func_indent = base_indent + "    "
                if "validate_url" not in content: # just check file broadly
                    new_lines.append(f"{func_indent}from loom.validators import validate_url; validate_url(url)")
                else:
                    new_lines.append(f"{func_indent}validate_url(url)")

        content = '\n'.join(new_lines)
        
        # fix the dict[str, Any] Any import if needed
        if 'dict[str, Any]' in content and 'Any' not in content:
            content = "from typing import Any\n" + content

        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Modified {filepath}")
    except Exception as e:
        print(f"Failed {filepath}: {e}")
