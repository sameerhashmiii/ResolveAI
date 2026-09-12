# Measured Evaluation Results

## Baseline

These are the checked release-baseline results for the deterministic local workflow. They demonstrate repeatability on a synthetic fixture, not expected accuracy on real support data.

| Field | Value |
|---|---|
| Dataset | `resolveai-phase9-eval-v1` |
| SHA-256 | `51c2973578cb4ccc72bd9f5c1e9ae7b40d61eaace87b0e6edbf88c1bf4f4f45f` |
| Sample size | 150 |
| Synthetic | Yes |

| Metric | Result |
|---|---:|
| Exact classification accuracy | 0.55333333 |
| Exact priority accuracy | 0.20666667 |
| Under-prioritization rate | 0.79333333 |
| Retrieval recall@5 | 0.49333333 |
| Retrieval precision@5 | 0.296 |
| Retrieval mean reciprocal rank | 0.58855556 |
| Response rubric overall pass rate | 1.0 |

The low priority accuracy and high under-prioritization rate are material limitations, not acceptable production performance. The response score means generated samples passed the versioned lexical/safety rubric; it does not mean responses were correct, useful, independently reviewed, or safe for delivery.

## Prominent Limitations

**The data generator and deterministic provider share the same synthetic support domain. They are not independent, and expected outcomes are not externally or independently adjudicated.** This can create favorable correlations while category mapping differences can create systematic errors.

- Knowledge relevance labels are deterministic generator outputs, not human relevance judgments.
- The same 150-case synthetic fixture is used as a reproducibility baseline, not a statistically representative test population.
- Exact-match category and priority metrics omit operational cost calibration and uncertainty intervals.
- The response rubric checks required terms, uncertainty language, formatting, escalation language, and prohibited completed-action claims. It does not measure factual correctness or user outcomes.
- Hosted provider behavior is not represented by this baseline and can vary by provider, model, date, and configuration.
- No real organizational, multilingual, adversarial, accessibility, latency, or fairness benchmark is included.

## Reproduction

With migrated PostgreSQL and the knowledge corpus ingested:

```bash
cd backend
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai \
  uv run --frozen python ../evaluation/run_eval.py
```

The runner verifies the checksum, prints a deterministic aggregate JSON report, and persists aggregate results only. See [evaluation methodology](evaluation.md) for metric definitions and data-exposure boundaries.
