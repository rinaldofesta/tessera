# Tessera Reliability Report
**Model:** openai/gpt-4o · **Engine:** llm (grader: anthropic/claude-sonnet-4-6)
**Run:** 2026-06-07T16:58:43+00:00 · **Probes:** 4 × 3 epochs · **inspect_ai:** 0.3.235

## Reliability — pass^3 (strict)
```text
OVERALL  pass^3  75%   (mean 92%)

by conflict type        pass^3            mean
  none          ██████████ 100%           100%
  resolvable    ██████████ 100%           100%
  unresolvable  ░░░░░░░░░░   0%            67%  ⚠ flaky
  void          ██████████ 100%           100%
```

## Operational axes (across probe-epochs)
| Axis | Rate | Denominator |
|------|-----:|-------------|
| Accuracy   | 100% | answer probe-epochs (6) |
| Provenance | 100% | all probe-epochs (12) |
| Refusal    | 83% | refuse probe-epochs (6) |

## Diagnostic appendix — failed pass^3

### ✗ q_globex_contract · unresolvable · pass^3 0% (2/3 epochs)
**Q:** What is Globex Inc's contract value?
- epoch 2 FAIL — accuracy✗ provenance✓ refusal✗
  - answer: "The contract value for Globex Inc is $1.5 million as per the documentation from the deal desk. This value is more recent and thus preferred over the $1.2 million listed in the CRM. Both sources were asserted on the same date, but since the document specifies it came from the deal desk, it is likely more accurate."
  - consulted: globex.contract.crm, globex.contract.note
  - locate: sample `q_globex_contract`, epoch 2

---
Logs: src/tessera/data/examples/gpt-4o/log.eval
Open in the viewer:  inspect view --log-dir src/tessera/data/examples/gpt-4o
Pull one failure (key-free):  read_eval_log_sample("src/tessera/data/examples/gpt-4o/log.eval", "<probe_id>", epoch=N)
