"""Add type coercion guards to tools that crash with list/dict params."""
import re
import os

PROJ = "/opt/loom-v3/src"

FIXES = [
    ("loom/tools/llm/augmented_generate.py", "research_augmented_generate", ["query", "context"]),
    ("loom/tools/infrastructure/gamification.py", "research_challenge_list", ["status"]),
    ("loom/tools/llm/model_compare.py", "research_compare_responses", ["responses"]),
    ("loom/tools/backends/unstructured_backend.py", "research_document_extract", ["url"]),
    ("loom/tools/infrastructure/full_pipeline.py", "research_full_pipeline", ["query"]),
    ("loom/tools/adversarial/hcs_escalation.py", "research_hcs_escalate", ["prompt", "response"]),
    ("loom/tools/adversarial/jailbreak_evolution.py", "research_jailbreak_evolution_get", ["strategy"]),
    ("loom/tools/adversarial/jailbreak_evolution.py", "research_jailbreak_evolution_adapt", ["strategy", "response"]),
    ("loom/tools/research/research_journal.py", "research_journal_search", ["query", "category"]),
    ("loom/tools/infrastructure/marketplace.py", "research_marketplace_list", ["category"]),
    ("loom/tools/llm/model_compare.py", "research_model_consensus", ["query"]),
    ("loom/tools/llm/resilience_predictor.py", "research_predict_resilience", ["strategy"]),
    ("loom/tools/llm/predictive_ranker.py", "research_predict_success", ["prompt", "strategy"]),
    ("loom/target_orchestrator.py", "research_target_orchestrate", ["query"]),
    ("loom/tools/research/transferability.py", "research_transfer_test", ["prompt", "strategy"]),
]


def make_guard(param: str) -> str:
    return (
        f'    if isinstance({param}, list): {param} = " ".join(str(x) for x in {param})\n'
        f"    if isinstance({param}, dict): {param} = str({param})\n"
    )


fixed = 0
for rel_path, func_name, params in FIXES:
    fpath = os.path.join(PROJ, rel_path)
    if not os.path.exists(fpath):
        print(f"SKIP {rel_path}: file not found")
        continue

    with open(fpath) as f:
        content = f.read()

    func_pat = rf"(async\s+)?def\s+{func_name}\([^)]*\)[^:]*:"
    func_match = re.search(func_pat, content)
    if not func_match:
        print(f"SKIP {func_name}: function not found in {rel_path}")
        continue

    func_pos = func_match.end()
    after_def = content[func_pos:]

    check_region = after_def[:500]
    if f"isinstance({params[0]}, list)" in check_region:
        print(f"SKIP {func_name}: guards already present")
        continue

    doc_match = re.search(r'\s*"""[\s\S]*?"""', after_def)
    if doc_match:
        insert_pos = func_pos + doc_match.end()
    else:
        newline_pos = after_def.find("\n")
        insert_pos = func_pos + newline_pos + 1

    guards = "\n"
    for p in params:
        guards += make_guard(p)

    new_content = content[:insert_pos] + guards + content[insert_pos:]

    with open(fpath, "w") as f:
        f.write(new_content)

    fixed += 1
    print(f"FIXED {func_name} in {rel_path} ({len(params)} params)")

print(f"\nTotal: {fixed} functions fixed")
