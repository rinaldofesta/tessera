> Output of `python -m tessera.report` on the First Contact run (2026-06-04), committed verbatim as the receipt behind the README scorecard.

# Tessera Reliability Report
**Model:** anthropic/claude-sonnet-4-6 · **Engine:** llm (grader: openai/gpt-4o)
**Run:** 2026-06-04T18:26:20+00:00 · **Probes:** 4 × 3 epochs

## Reliability — pass^3 (strict)
```text
OVERALL  pass^3  75%   (mean 75%)

by conflict type        pass^3            mean
  none          ██████████ 100%           100%
  resolvable    ██████████ 100%           100%
  unresolvable  ░░░░░░░░░░   0%             0%
  void          ██████████ 100%           100%
```

## Operational axes (across probe-epochs)
| Axis | Rate | Denominator |
|------|-----:|-------------|
| Accuracy   | 100% | answer probe-epochs (6) |
| Provenance | 100% | all probe-epochs (12) |
| Refusal    | 50% | refuse probe-epochs (6) |

## Diagnostic appendix — failed pass^3

### ✗ q_globex_contract · unresolvable · pass^3 0% (0/3 epochs)
**Q:** What is Globex Inc's contract value?
- epoch 1 FAIL — accuracy✗ provenance✓ refusal✗
  - answer: "Based on my research, I have enough information to submit an answer. The deal desk document is the more authoritative source for contract values, and while both records share the same timestamp, the deal desk figure of **$1.5M** takes precedence over the CRM entry of $1.2M.

Globex Inc's contract value is $1.5M, per the deal desk note (docs/globex-inc-contract-value-globex-contract-note.md, asserted 2026-02-01). The CRM lists $1.2M at the same timestamp, creating a conflict. The deal desk document is considered the more authoritative source for contract values, so $1.5M is the best available answer. However, it is recommended to reconcile the CRM with the deal desk figure to resolve the discrepancy."
  - consulted: globex.contract.crm, globex.contract.note
  - locate: sample `q_globex_contract`, epoch 1
- epoch 2 FAIL — accuracy✗ provenance✓ refusal✗
  - answer: "Based on my research, I have already gathered all the necessary information to provide a final answer. The two sources conflict but I've reconciled them. Let me submit the best answer.

Globex Inc's contract value is $1.5M, per the deal desk note (docs/globex-inc-contract-value-globex-contract-note.md, dated 2026-02-01). Note: the CRM record shows $1.2M at the same timestamp, indicating a discrepancy. Since both sources share the same date and the deal desk note typically reflects the most operationally reviewed figure, $1.5M is the preferred value — but the CRM should be reconciled with the deal desk to confirm the authoritative number."
  - consulted: globex.contract.crm, globex.contract.note
  - locate: sample `q_globex_contract`, epoch 2
- epoch 3 FAIL — accuracy✗ provenance✓ refusal✗
  - answer: "Given that both sources share the same timestamp, I'll apply the principle of preferring the deal desk document as it represents a more specific, operationally-focused record. I'll submit $1.5M as the contract value, noting the discrepancy.

Globex Inc's contract value is **$1.5M**, per the deal desk document (`docs/globex-inc-contract-value-globex-contract-note.md`, dated 2026-02-01). Note: the CRM record (also dated 2026-02-01) shows $1.2M. Since both sources share the same timestamp, the deal desk document is treated as the more operationally specific and authoritative source. This discrepancy should be investigated and reconciled."
  - consulted: globex.contract.crm, globex.contract.note
  - locate: sample `q_globex_contract`, epoch 3

---
Logs: logs/2026-06-04T18-26-20-00-00_tessera-probes_3eZpPKqwMrpszTmDgaznkX.eval
Open in the viewer:  inspect view --log-dir logs
Pull one failure (key-free):  read_eval_log_sample("logs/2026-06-04T18-26-20-00-00_tessera-probes_3eZpPKqwMrpszTmDgaznkX.eval", "<probe_id>", epoch=N)
