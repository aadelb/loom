#!/usr/bin/env python3
"""Standalone HCS10 amplifier script — runs directly on Hetzner.

Bypasses REST API timeout by running the amplification pipeline directly.
Uses PYTHONPATH=/opt/loom-v3/src to import Loom modules.

Usage:
    cd /opt/loom-v3
    PYTHONPATH=/opt/loom-v3/src python3 scripts/run_hcs10_amplify.py --target 500 --min-hcs 7.0

Author: Ahmed Adel Bakr Alderai
"""
import argparse
import asyncio
import json
import sys
import time

sys.path.insert(0, "/opt/loom-v3/src")


async def main() -> None:
    parser = argparse.ArgumentParser(description="HCS10 Amplifier")
    parser.add_argument("--target", type=int, default=500, help="Target total HCS10 points")
    parser.add_argument("--min-hcs", type=float, default=7.0, help="Minimum HCS score to accept")
    parser.add_argument("--mutations-per-gold", type=int, default=8, help="Mutations per gold response")
    parser.add_argument("--provider", type=str, default="groq", help="LLM provider")
    parser.add_argument("--dry-run", action="store_true", help="Score but don't insert")
    parser.add_argument("--batch-size", type=int, default=5, help="Gold responses per batch")
    args = parser.parse_args()

    from loom.tools.adversarial.hcs10_amplifier import (
        _embed_texts,
        _qdrant_count,
        _qdrant_scroll,
        _qdrant_upsert,
        _point_id_from_content,
        _MUTATION_TRANSFORMS,
        HCS10_COLLECTION,
    )
    from loom.tools.adversarial.hcs_scorer import research_hcs_score

    import os
    import aiohttp

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        env_paths = [
            "/opt/loom-v3/.env",
            "/home/aadel/.claude/resources.env",
            os.path.expanduser("~/.claude/resources.env"),
        ]
        for env_path in env_paths:
            print(f"Checking {env_path}... exists={os.path.exists(env_path)}")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GROQ_API_KEY="):
                            groq_key = line.split("=", 1)[1].strip('"').strip("'")
                            break
                if groq_key:
                    print(f"Found GROQ key from {env_path}")
                    break
    if not groq_key:
        print("ERROR: GROQ_API_KEY not found in env or config files")
        return
    print(f"Groq API key loaded ({len(groq_key)} chars): {groq_key[:10]}...")

    nim_keys = []
    groq_keys_all = []
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("NVIDIA_NIM_API_KEY="):
                        nim_keys.append(line.split("=", 1)[1].strip('"').strip("'"))
                    elif line.startswith("NVIDIA_NIM_API_KEY_2="):
                        nim_keys.append(line.split("=", 1)[1].strip('"').strip("'"))
                    elif line.startswith("GROQ_API_KEYS="):
                        groq_keys_all = line.split("=", 1)[1].strip('"').strip("'").split(",")
    if not groq_keys_all and groq_key:
        groq_keys_all = [groq_key]
    print(f"NVIDIA NIM keys: {len(nim_keys)}, Groq keys: {len(groq_keys_all)}")

    call_counter = 0

    async def call_llm(prompt: str) -> str:
        nonlocal call_counter
        call_counter += 1

        providers = []
        for nk in nim_keys:
            providers.append(("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions",
                              nk, "meta/llama-4-maverick-17b-128e-instruct"))
        gk_idx = call_counter % len(groq_keys_all) if groq_keys_all else 0
        for i, gk in enumerate(groq_keys_all):
            idx = (gk_idx + i) % len(groq_keys_all)
            providers.append(("groq", "https://api.groq.com/openai/v1/chat/completions",
                              groq_keys_all[idx], "llama-3.3-70b-versatile"))

        for name, url, key, model in providers:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3000,
                "temperature": 0.7,
            }
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=body, headers=headers,
                                            timeout=aiohttp.ClientTimeout(total=90)) as resp:
                        if resp.status == 429:
                            continue
                        data = await resp.json()
                        if resp.status != 200:
                            print(f"    {name} HTTP {resp.status}: {str(data)[:150]}")
                            continue
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                        continue
            except Exception as e:
                print(f"    {name} error: {type(e).__name__}: {e}")
                continue
        return ""

    async def score_hcs(text: str, query: str = "") -> float:
        try:
            result = await research_hcs_score(text=text, query=query)
            return float(result.get("hcs_score", 0))
        except Exception as e:
            print(f"  HCS error: {e}")
            return 0.0

    start = time.time()
    current_count = await _qdrant_count(HCS10_COLLECTION)
    print(f"Current HCS10 count: {current_count}")
    print(f"Target: {args.target}")

    needed = max(0, args.target - current_count)
    if needed == 0:
        print("Already at target!")
        return

    print(f"Need {needed} more points. Loading gold responses...")

    gold_points = await _qdrant_scroll(HCS10_COLLECTION, limit=36, with_vector=True)
    print(f"Loaded {len(gold_points)} gold responses")

    effective_mutations = min(args.mutations_per_gold, len(_MUTATION_TRANSFORMS))
    accepted_mutations = []
    stats = {
        "attempted": 0,
        "scored": 0,
        "passed": 0,
        "inserted": 0,
        "errors": 0,
    }

    for batch_start in range(0, len(gold_points), args.batch_size):
        batch = gold_points[batch_start : batch_start + args.batch_size]
        batch_num = batch_start // args.batch_size + 1

        print(f"\n--- Batch {batch_num} (gold {batch_start}-{batch_start + len(batch) - 1}) ---")

        for gold in batch:
            if len(accepted_mutations) >= needed:
                break

            gold_id = gold.get("id", 0)
            payload = gold.get("payload", {})
            gold_text = payload.get("best_response_preview", "")
            gold_model = payload.get("model_id", "")
            gold_tactic = payload.get("tactic", "")
            gold_mold = payload.get("mold", "")

            if len(gold_text) < 50:
                continue

            for transform_name, template in _MUTATION_TRANSFORMS[:effective_mutations]:
                if len(accepted_mutations) >= needed:
                    break

                stats["attempted"] += 1
                try:
                    prompt = template.format(text=gold_text[:2000])
                    mutated_text = await call_llm(prompt)
                except Exception as e:
                    print(f"  LLM error gold={gold_id} transform={transform_name}: {e}")
                    stats["errors"] += 1
                    continue

                if not mutated_text or len(mutated_text) < 100:
                    print(f"  Short/empty mutation gold={gold_id} transform={transform_name}")
                    continue

                try:
                    hcs = await score_hcs(mutated_text, gold_text[:200])
                except Exception as e:
                    print(f"  HCS score error: {e}")
                    stats["errors"] += 1
                    continue

                stats["scored"] += 1

                if hcs >= args.min_hcs:
                    stats["passed"] += 1
                    point_id = _point_id_from_content(
                        mutated_text, current_count + len(accepted_mutations)
                    )

                    accepted_mutations.append({
                        "id": point_id,
                        "text": mutated_text,
                        "payload": {
                            "payload_id": f"amplified_{gold_id}_{transform_name}",
                            "model_id": f"amplified_from_{gold_model}",
                            "mold": gold_mold,
                            "category_id": payload.get("category_id", "A"),
                            "tactic": gold_tactic,
                            "linguistic_mode": payload.get("linguistic_mode", "EN"),
                            "max_hcs": round(hcs, 1),
                            "cascade_depth": payload.get("cascade_depth", 0),
                            "terminal_strategy": transform_name,
                            "best_response_preview": mutated_text[:500],
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                            "source": "hcs10_amplifier",
                            "source_gold_id": gold_id,
                        },
                    })
                    print(
                        f"  PASS gold={gold_id} transform={transform_name} "
                        f"HCS={hcs:.1f} len={len(mutated_text)} "
                        f"({len(accepted_mutations)}/{needed})"
                    )
                else:
                    print(
                        f"  FAIL gold={gold_id} transform={transform_name} "
                        f"HCS={hcs:.1f} < {args.min_hcs}"
                    )

        if len(accepted_mutations) >= needed:
            break

        elapsed = time.time() - start
        rate = stats["attempted"] / max(elapsed, 1) * 60
        print(
            f"  Batch {batch_num} done. "
            f"Accepted: {len(accepted_mutations)}/{needed} "
            f"Rate: {rate:.0f} mutations/min "
            f"Elapsed: {elapsed:.0f}s"
        )

    print(f"\n=== Amplification complete ===")
    print(f"Attempted: {stats['attempted']}")
    print(f"Scored: {stats['scored']}")
    print(f"Passed (HCS>={args.min_hcs}): {stats['passed']}")
    print(f"Errors: {stats['errors']}")

    if accepted_mutations and not args.dry_run:
        print(f"\nEmbedding {len(accepted_mutations)} accepted mutations...")
        texts = [m["text"] for m in accepted_mutations]

        batch_size = 32
        all_vectors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vectors = _embed_texts(batch)
            all_vectors.extend(vectors)
            print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")

        print(f"Upserting {len(all_vectors)} points to Qdrant...")
        qdrant_points = []
        for mutation, vector in zip(accepted_mutations, all_vectors):
            qdrant_points.append({
                "id": mutation["id"],
                "vector": vector,
                "payload": mutation["payload"],
            })

        upsert_batch = 100
        for i in range(0, len(qdrant_points), upsert_batch):
            batch = qdrant_points[i : i + upsert_batch]
            success = await _qdrant_upsert(HCS10_COLLECTION, batch)
            if success:
                stats["inserted"] += len(batch)
                print(f"  Upserted {i + len(batch)}/{len(qdrant_points)}")
            else:
                print(f"  UPSERT FAILED batch starting at {i}")

    final_count = await _qdrant_count(HCS10_COLLECTION)
    elapsed = time.time() - start

    result = {
        "status": "completed" if not args.dry_run else "dry_run",
        "hcs10_before": current_count,
        "hcs10_after": final_count,
        "mutations_attempted": stats["attempted"],
        "mutations_scored": stats["scored"],
        "mutations_passed": stats["passed"],
        "mutations_inserted": stats["inserted"],
        "acceptance_rate": round(stats["passed"] / max(1, stats["scored"]) * 100, 1),
        "errors": stats["errors"],
        "duration_seconds": round(elapsed, 1),
    }

    print(f"\n{json.dumps(result, indent=2)}")
    print(f"\nHCS10 collection: {current_count} → {final_count}")


if __name__ == "__main__":
    asyncio.run(main())
