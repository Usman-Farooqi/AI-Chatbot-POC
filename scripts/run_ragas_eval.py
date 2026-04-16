"""
scripts/run_ragas_eval.py — Evaluate the RAG chatbot pipeline with RAGAS.

For each question in tests/eval_questions.jsonl:
  1. Runs the SAME retrieval pipeline the app uses (search_documents)
  2. Runs the SAME generation pipeline (build_system_prompt + Claude)
  3. Hands (question, retrieved_contexts, answer, ground_truth) to RAGAS
  4. Scores on faithfulness, answer_relevancy, context_precision, context_recall
  5. Saves summary + per-question results under tests/eval_history/<timestamp>/

Usage:
    python scripts/run_ragas_eval.py
    python scripts/run_ragas_eval.py --limit 5          # quick smoke test
    python scripts/run_ragas_eval.py --judge haiku      # cheaper judge model

Environment:
    ANTHROPIC_API_KEY    required
    RAGAS_JUDGE_MODEL    optional — overrides the LLM used as RAGAS judge
                         (default: claude-sonnet-4-6, same as the chatbot)

Cost: ~$0.30–$3 per full run depending on judge model.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ── Path bootstrap ────────────────────────────────────────────────────────────
# So this script can be run as `python scripts/run_ragas_eval.py` from the
# project root and still import document_loader / chat_engine.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from chat_engine import MODEL, build_system_prompt   # noqa: E402
from document_loader import load_documents, search_documents   # noqa: E402


# ── Config ────────────────────────────────────────────────────────────────────
GOLDEN_FILE  = PROJECT_ROOT / "tests" / "eval_questions.jsonl"
OUTPUT_ROOT  = PROJECT_ROOT / "tests" / "eval_history"

JUDGE_MODEL_ALIASES = {
    "sonnet": "claude-sonnet-4-6",
    "haiku":  "claude-haiku-4-5",
    "opus":   "claude-opus-4-6",
}


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_pipeline(question: str, bundle, client) -> tuple[str, list[str]]:
    """
    Run the actual chatbot pipeline for one question.

    Returns (answer, full_contexts).  `full_contexts` is the complete set of
    context passages Claude actually saw — both the always-injected small docs
    (vehicle_profile, maintenance_records, insurance_card) AND the RAG-retrieved
    chunks from the large docs.  Passing only the RAG chunks to RAGAS would
    cause faithfulness / context_precision / context_recall to drop to 0 on any
    question answered from the small docs, producing misleading scores.
    """
    chunks = search_documents(question)
    system_prompt = build_system_prompt(bundle, retrieved_chunks=chunks or None)

    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": question}],
    )
    answer = resp.content[0].text

    # Build the full context list exactly as Claude saw it.
    contexts: list[str] = [
        f"[vehicle_profile]\n{json.dumps(bundle.vehicle_profile, indent=2)}",
        f"[maintenance_records]\n{bundle.maintenance_records}",
        f"[insurance_card]\n{bundle.insurance_card}",
    ]
    if chunks:
        for c in chunks:
            contexts.append(f"[{c['source']}]\n{c['text']}")

    return answer, contexts


# ── RAGAS evaluation ──────────────────────────────────────────────────────────

def run_ragas(rows: list[dict], judge_model: str):
    """
    Run RAGAS on the collected pipeline traces.
    Imported lazily so the script fails fast on missing deps with a clear message.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.run_config import RunConfig
        from ragas.metrics import (
            Faithfulness,
            ResponseRelevancy,
            LLMContextPrecisionWithReference,
            LLMContextRecall,
        )
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_anthropic import ChatAnthropic
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as e:
        print(f"\n✗ Missing RAGAS dependencies: {e}")
        print("  Install with: pip install ragas datasets langchain-anthropic langchain-huggingface")
        sys.exit(1)

    # max_tokens=4096: some metrics (e.g. Faithfulness on long answers) emit
    # large JSON payloads and get truncated on the default 1024 cap, which
    # surfaces as LLMDidNotFinishException and a NaN score.
    judge_llm = LangchainLLMWrapper(
        ChatAnthropic(model=judge_model, max_tokens=4096, temperature=0)
    )
    judge_emb = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    )

    # Throttle concurrency so we don't blow past Anthropic's per-minute
    # rate limits (Haiku: 50 rpm / 50K input TPM on default tier).
    # max_workers=2 keeps us well under the ceiling at a modest speed cost.
    run_config = RunConfig(max_workers=2, timeout=180)

    # RAGAS expects specific column names:
    #   user_input, retrieved_contexts, response, reference
    dataset = Dataset.from_list([
        {
            "user_input":         r["question"],
            "retrieved_contexts": r["contexts"],
            "response":           r["answer"],
            "reference":          r["ground_truth"],
        }
        for r in rows
    ])

    metrics = [
        Faithfulness(),
        ResponseRelevancy(),
        LLMContextPrecisionWithReference(),
        LLMContextRecall(),
    ]

    print(f"\n→ Running RAGAS evaluation with judge: {judge_model}")
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=judge_llm,
        embeddings=judge_emb,
        run_config=run_config,
    )
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation on the chatbot.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only evaluate the first N questions (smoke test).")
    parser.add_argument("--judge", type=str, default=None,
                        help=f"Judge model. Aliases: {list(JUDGE_MODEL_ALIASES)}, "
                             "or pass a full model string. Defaults to chatbot model.")
    parser.add_argument("--golden", type=str, default=str(GOLDEN_FILE),
                        help="Path to the golden dataset JSONL.")
    args = parser.parse_args()

    # override=True because the parent shell may have ANTHROPIC_API_KEY set
    # to an empty string (common on macOS with Claude Desktop installed)
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("✗ ANTHROPIC_API_KEY not set. Put it in .env or export it.")
        sys.exit(1)

    # Resolve judge model (CLI > env > default)
    judge = args.judge or os.getenv("RAGAS_JUDGE_MODEL") or MODEL
    judge = JUDGE_MODEL_ALIASES.get(judge, judge)

    # ── Load golden dataset ──────────────────────────────────────────────────
    golden_path = Path(args.golden)
    if not golden_path.exists():
        print(f"✗ Golden dataset not found: {golden_path}")
        sys.exit(1)

    with golden_path.open() as f:
        golden = [json.loads(line) for line in f if line.strip()]

    if args.limit:
        golden = golden[:args.limit]

    print("=" * 60)
    print(f"RAGAS Evaluation — {len(golden)} questions")
    print(f"Chatbot model:  {MODEL}")
    print(f"Judge model:    {judge}")
    print("=" * 60)

    # ── Run pipeline on each question ────────────────────────────────────────
    bundle = load_documents()
    client = anthropic.Anthropic(api_key=api_key)

    rows = []
    for i, item in enumerate(golden, 1):
        q = item["question"]
        print(f"\n[{i}/{len(golden)}] {q[:70]}{'...' if len(q) > 70 else ''}")

        t0 = time.time()
        try:
            answer, contexts = run_pipeline(q, bundle, client)
        except Exception as exc:
            print(f"  ✗ Pipeline failed: {exc}")
            continue

        rows.append({
            "question":     q,
            "contexts":     contexts,
            "answer":       answer,
            "ground_truth": item["ground_truth"],
            "expected_src": item.get("expected_source", ""),
        })
        print(f"  ✓ {len(contexts)} chunks retrieved, {len(answer)} chars returned in {time.time()-t0:.1f}s")

    if not rows:
        print("\n✗ No successful pipeline runs — aborting evaluation.")
        sys.exit(1)

    # ── Run RAGAS ────────────────────────────────────────────────────────────
    results = run_ragas(rows, judge_model=judge)

    # ── Save outputs ─────────────────────────────────────────────────────────
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_dir = OUTPUT_ROOT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    # Compute summary scores from the per-question DataFrame.
    # RAGAS 0.2+ returns a result object that's awkward to iterate directly;
    # .to_pandas() is the stable public API.
    df = results.to_pandas()
    metric_cols = [c for c in df.columns
                   if c not in ("user_input", "retrieved_contexts", "response", "reference")]

    # For each metric, report mean + how many questions it actually scored
    # (NaN = judge failed, usually rate-limit / timeout; excluded from mean).
    scores = {}
    for col in metric_cols:
        series = df[col]
        valid = series.dropna()
        scores[col] = {
            "mean":     float(valid.mean()) if len(valid) else None,
            "scored":   int(len(valid)),
            "failed":   int(series.isna().sum()),
            "total":    int(len(series)),
        }

    summary = {
        "timestamp":     datetime.now().isoformat(),
        "chatbot_model": MODEL,
        "judge_model":   judge,
        "n_questions":   len(rows),
        "scores":        scores,
    }
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    # Per-question CSV (detailed scores)
    df.to_csv(out_dir / "per_question.csv", index=False)

    # ── Print summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"{'Metric':<38} {'Score':>6} {'Scored':>8}   Bar")
    print("-" * 70)
    for metric, info in summary["scores"].items():
        mean = info["mean"]
        if mean is None:
            print(f"  {metric:<36} {'n/a':>6}  {info['scored']}/{info['total']}")
        else:
            bar = "█" * int(mean * 20)
            note = "" if info["failed"] == 0 else f" ⚠ {info['failed']} judge failure(s)"
            print(f"  {metric:<36} {mean:6.3f}  {info['scored']}/{info['total']}  {bar}{note}")
    print(f"\n→ Saved to: {out_dir}")
    print("  - summary.json      (overall scores)")
    print("  - per_question.csv  (detailed per-question scores)")


if __name__ == "__main__":
    main()
