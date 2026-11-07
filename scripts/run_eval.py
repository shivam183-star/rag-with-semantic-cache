"""Benchmark evaluation runner for RAG Semantic Cache.
Usage: python -m scripts.run_eval --url http://127.0.0.1:8000 --threshold 0.90
"""
import argparse
import json
import time
from pathlib import Path
import httpx
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Run evaluation sweep against RAG Semantic Cache API")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of API backend")
    parser.add_argument("--questions", default="eval/questions.json", help="Path to evaluation questions dataset")
    parser.add_argument("--threshold", type=float, default=0.90, help="Similarity threshold for evaluation")
    parser.add_argument("--clear-first", action="store_true", help="Clear cache before starting cold run")
    parser.add_argument("--output-csv", default="eval/evaluation_results.csv", help="Output results CSV path")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.url, timeout=60.0)

    # 1. Health check
    try:
        health = client.get("/health").json()
        print(f"[*] API Healthy. Docs chunks: {health.get('docs_chunks')}, Cache entries: {health.get('cache_entries')}")
    except Exception as e:
        print(f"[!] Could not connect to API at {args.url}: {e}")
        return

    # Clear cache if requested
    if args.clear_first:
        print("[*] Clearing cache for clean baseline...")
        client.post("/cache/clear")

    with open(args.questions, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results = []
    run_tag = f"eval_{int(time.time())}"

    # Phase 1: Cold Run (Base questions)
    print(f"\n--- Phase 1: Cold Run ({len(dataset['base_questions'])} base questions) ---")
    for item in dataset["base_questions"]:
        payload = {
            "question": item["question"],
            "threshold": args.threshold,
            "run_tag": run_tag,
            "dry_run": false if hasattr(bool, 'false') else False,
        }
        t0 = time.perf_counter()
        r = client.post("/ask", json=payload).json()
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results.append({
            "phase": "cold_base",
            "question": item["question"],
            "cache_hit": r["cache_hit"],
            "similarity": r["similarity"],
            "latency_ms": r["latency_ms"],
            "total_tokens": r["input_tokens"] + r["output_tokens"],
            "answer_preview": r["answer"][:70].replace("\n", " "),
        })
        status = "HIT" if r["cache_hit"] else "MISS"
        print(f"[{status}] {item['question'][:45]:<45} | {r['latency_ms']}ms | tokens: {r['input_tokens']+r['output_tokens']}")

    # Phase 2: Warm Run (Semantic Paraphrases)
    print(f"\n--- Phase 2: Warm Run ({len(dataset['paraphrases'])} paraphrased questions) ---")
    for item in dataset["paraphrases"]:
        payload = {
            "question": item["question"],
            "threshold": args.threshold,
            "run_tag": run_tag,
            "dry_run": False,
        }
        t0 = time.perf_counter()
        r = client.post("/ask", json=payload).json()
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results.append({
            "phase": "warm_paraphrase",
            "question": item["question"],
            "cache_hit": r["cache_hit"],
            "similarity": r["similarity"],
            "latency_ms": r["latency_ms"],
            "total_tokens": r["input_tokens"] + r["output_tokens"],
            "answer_preview": r["answer"][:70].replace("\n", " "),
        })
        status = "HIT" if r["cache_hit"] else "MISS"
        sim_str = f"sim: {r['similarity']:.3f}" if r['similarity'] else "--"
        print(f"[{status}] {item['question'][:45]:<45} | {sim_str} | {r['latency_ms']}ms | tokens: {r['input_tokens']+r['output_tokens']}")

    # Phase 3: Adversarial Near-Misses
    print(f"\n--- Phase 3: Adversarial Near-Misses ({len(dataset.get('near_miss_questions', []))} questions) ---")
    for item in dataset.get("near_miss_questions", []):
        payload = {
            "question": item["question"],
            "threshold": args.threshold,
            "run_tag": run_tag,
            "dry_run": False,
        }
        r = client.post("/ask", json=payload).json()
        results.append({
            "phase": "adversarial_near_miss",
            "question": item["question"],
            "cache_hit": r["cache_hit"],
            "similarity": r["similarity"],
            "latency_ms": r["latency_ms"],
            "total_tokens": r["input_tokens"] + r["output_tokens"],
            "answer_preview": r["answer"][:70].replace("\n", " "),
        })
        status = "HIT" if r["cache_hit"] else "MISS"
        print(f"[{status}] {item['question'][:45]:<45} | {r['latency_ms']}ms")

    # Export to DataFrame & CSV
    df = pd.DataFrame(results)
    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output_csv, index=False)
    print(f"\n[+] Detailed results saved to {args.output_csv}")

    # Metrics Summary
    warm_df = df[df["phase"] == "warm_paraphrase"]
    hits = df[df["cache_hit"] == True]
    misses = df[df["cache_hit"] == False]

    avg_hit_lat = hits["latency_ms"].mean() if len(hits) else 0
    avg_miss_lat = misses["latency_ms"].mean() if len(misses) else 0
    lat_reduction = ((avg_miss_lat - avg_hit_lat) / avg_miss_lat * 100) if avg_miss_lat else 0
    p95_hit = hits["latency_ms"].quantile(0.95) if len(hits) else 0
    p95_miss = misses["latency_ms"].quantile(0.95) if len(misses) else 0

    avg_miss_tokens = misses["total_tokens"].mean() if len(misses) else 0
    tokens_saved = int(len(hits) * avg_miss_tokens)

    near_miss_hits = df[(df["phase"] == "adversarial_near_miss") & (df["cache_hit"] == True)]
    false_hit_rate = (len(near_miss_hits) / len(df[df["phase"] == "adversarial_near_miss"]) * 100) if len(df[df["phase"] == "adversarial_near_miss"]) else 0

    print("\n" + "="*50)
    print("       EVALUATION BENCHMARK SUMMARY")
    print("="*50)
    print(f"Total Evaluated Queries:       {len(df)}")
    print(f"Paraphrase Hit Rate:           {(len(warm_df[warm_df['cache_hit'] == True]) / len(warm_df) * 100):.1f}%")
    print(f"Adversarial False Hit Rate:    {false_hit_rate:.1f}%")
    print(f"Average Latency (Miss):        {avg_miss_lat:.1f} ms")
    print(f"Average Latency (Hit):         {avg_hit_lat:.1f} ms")
    print(f"Latency Reduction:             {lat_reduction:.1f}%")
    print(f"p95 Latency (Miss vs Hit):     {p95_miss:.1f} ms -> {p95_hit:.1f} ms")
    print(f"Estimated Tokens Saved:        {tokens_saved:,} tokens")
    print("="*50)


if __name__ == "__main__":
    main()
