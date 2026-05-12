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
            
            if "validate_url(url)" not in content:
                inject = f"\n{func_indent}from loom.validators import validate_url\n{func_indent}validate_url(url)"
            else:
                inject = f"\n{func_indent}validate_url(url)"
                
            return m + inject

        # Find `def func_name(...url...):`
        content = re.sub(r'def\s+([a-zA-Z0-9_]+)\([^)]*\burl\b[^)]*\)\s*(?:->\s*[^:]+)?\s*:', inject_validate, content)

        # 6. Raise logic - instead of replacing all raises blindly, replace raises that have an exception msg
        # e.g., `raise ValueError("msg")` -> `return {'error': "msg", 'error_code': 'internal', 'source': 'func_name'}`
        # e.g., bare `raise` in except -> `return {'error': str(e), ...}`
        
        def fix_raise(match):
            indent = match.group(1)
            raise_stmt = match.group(2)
            
            # Find which function we are in by looking backwards
            pos = match.start()
            before = content[:pos]
            func_matches = list(re.finditer(r'def\s+([a-zA-Z0-9_]+)\(', before))
            func_name = func_matches[-1].group(1) if func_matches else "unknown"
            
            if raise_stmt == "raise":
                return f"{indent}return {{'error': str(e), 'error_code': 'internal', 'source': '{func_name}'}}"
            
            # Check if it has string inside: raise ValueError("msg")
            msg_match = re.search(r'raise\s+[a-zA-Z0-9_]+\((["\'])(.*?)(["\'])\)', raise_stmt)
            if msg_match:
                msg = msg_match.group(2)
                return f"{indent}return {{'error': '{msg}', 'error_code': 'internal', 'source': '{func_name}'}}"
                
            # fallback
            return f"{indent}return {{'error': str(e) if 'e' in locals() else 'error', 'error_code': 'internal', 'source': '{func_name}'}}"

        content = re.sub(r'^(\s*)(raise\b.*?)$', fix_raise, content, flags=re.MULTILINE)

        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Modified URL/raise in {filepath}")
    except Exception as e:
        print(f"Failed {filepath}: {e}")
