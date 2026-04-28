import ast
import os
import re
from pathlib import Path
import sys

ROOT = Path(os.getcwd())
SRC = ROOT / 'src' / 'loom'

def get_functions(filepath: Path) -> list[str]:
    if not filepath.exists():
        return []
    try:
        content = filepath.read_text(encoding='utf-8')
        tree = ast.parse(content)
        funcs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):
                    if any(node.name.startswith(p) for p in ['research_', 'fetch_', 'search_', 'crawl_', 'find_']):
                        funcs.append(node.name)
        return funcs
    except Exception:
        return []

def main():
    print("=== TOOLS AUDIT ===")
    tools_dir = SRC / 'tools'
    tools_files = [f for f in tools_dir.glob('*.py') if f.name != '__init__.py']
    
    server_code = (SRC / 'server.py').read_text(encoding='utf-8')
    tools_ref_text = (ROOT / 'docs' / 'tools-reference.md').read_text(encoding='utf-8') if (ROOT / 'docs' / 'tools-reference.md').exists() else ""
    help_md_text = (ROOT / 'docs' / 'help.md').read_text(encoding='utf-8') if (ROOT / 'docs' / 'help.md').exists() else ""

    missing_tools = False
    
    for f in sorted(tools_files):
        module_name = f.stem
        funcs = get_functions(f)
        
        imported = f"{module_name}" in server_code
        
        unregistered_funcs = []
        for func in funcs:
            if func not in server_code:
                unregistered_funcs.append(func)
                
        test_file = ROOT / 'tests' / 'test_tools' / f"test_{module_name}.py"
        test_file_root = ROOT / 'tests' / f"test_{module_name}.py"
        has_test = test_file.exists() or test_file_root.exists()
        
        doc_ref = module_name in tools_ref_text or any(func in tools_ref_text for func in funcs)
        doc_help = module_name in help_md_text or any(func in help_md_text for func in funcs)
        
        gaps = []
        if not imported: gaps.append("Not imported in server.py")
        if unregistered_funcs: gaps.append(f"Unregistered public functions: {unregistered_funcs}")
        if not has_test: gaps.append("No test file found")
        if not doc_ref: gaps.append("Not in tools-reference.md")
        if not doc_help: gaps.append("Not in help.md")
        
        if gaps:
            missing_tools = True
            print(f"Tool {module_name}.py:")
            for g in gaps:
                print(f"  - {g}")
                
    if not missing_tools:
        print("All tools fully integrated!")

    print("\n=== PROVIDERS AUDIT ===")
    providers_dir = SRC / 'providers'
    providers_files = [f for f in providers_dir.glob('*.py') if f.name != '__init__.py']
    
    search_code = (SRC / 'tools' / 'search.py').read_text(encoding='utf-8') if (SRC / 'tools' / 'search.py').exists() else ""
    validators_code = (SRC / 'validators.py').read_text(encoding='utf-8') if (SRC / 'validators.py').exists() else ""
    params_code = (SRC / 'params.py').read_text(encoding='utf-8') if (SRC / 'params.py').exists() else ""
    
    missing_providers = False
    
    for f in sorted(providers_files):
        module_name = f.stem
        routed = f"{module_name}" in search_code
        
        provider_id = module_name.replace('_search', '').replace('_data', '').replace('_provider', '').replace('_local', '').replace('_extract', '')
        
        in_validators = provider_id in validators_code or module_name in validators_code
        in_params = provider_id in params_code or module_name in params_code
        
        gaps = []
        if not routed: gaps.append("Not routed in search.py")
        if not in_validators: gaps.append("Not in PROVIDER_CONFIG_ALLOWLIST (validators.py)")
        if not in_params: gaps.append("Not in SearchParams/DeepParams (params.py)")
        
        if gaps:
            missing_providers = True
            print(f"Provider {module_name}.py:")
            for g in gaps:
                print(f"  - {g}")

    if not missing_providers:
        print("All providers fully integrated!")

if __name__ == '__main__':
    main()
