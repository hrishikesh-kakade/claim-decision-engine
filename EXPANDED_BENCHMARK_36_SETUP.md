# Expanded 36-case decision benchmark

This patch preserves the original 18 claim inputs and adds 18 separately stored cases:

- 6 `ADMISSIBLE`
- 6 `ADMISSIBLE_WITH_LIMITS`
- 6 `PARTIALLY_ADMISSIBLE`

The original cases remain:

- 6 `NOT_ADMISSIBLE`
- 12 `NEEDS_REVIEW`

The expected outcomes for all 36 cases are in `eval/policy_aware_expected_outcomes.json`. The original 18 expected decisions and rationales are retained; the new 18 are appended under `NEW-*` IDs.

## Files in this patch

- `eval/cases/expanded_cases.json`: 18 new claim inputs.
- `eval/policy_aware_expected_outcomes.json`: complete 36-case expected-outcome file.
- `eval/common.py`: includes the expanded case file in `load_cases()`.
- `tests/test_expanded_benchmark.py`: structural checks for count, class distribution, monetary bases and partial-claim timing evidence.

## Apply

Extract the ZIP into the repository root, preserving folder paths and allowing the updated files to overwrite their existing versions. The original `data/public_test_cases.json` and `eval/cases/custom_cases.json` are not modified.

## Validate

```powershell
uv run python -m unittest tests.test_expanded_benchmark -v
uv run python .\eval\run_eval.py
```

For the integrated report, after the other evaluation components are ready:

```powershell
uv run python .\eval\run_all.py
```

The first command checks benchmark structure. The second runs all 36 claims through the decision engine and compares actual outputs with the independently specified expected outcomes. The full integrated run also executes retrieval, citation and latency evaluations.

## Important limitation

These are synthetic, developer-authored cases derived from the supplied policy clauses. Their expected outcomes are rule-based hypotheses that must be confirmed by running the engine and reviewing every mismatch. They are not independent insurance-expert adjudications. In particular, the current production code's pre/post-window and aggregate-payable calculations still require separate review before monetary accuracy claims are made.
