import pytest

from tessera.report.models import (
    AxesSummary, CategoryReliability, ProbeEpoch, ProbeReliability, ReportError, RunHeader,
)


def test_probe_epoch_is_frozen_and_holds_fields():
    pe = ProbeEpoch(probe_id="p", epoch=1, conflict_type="none", expected_behavior="answer",
                    passed=True, accuracy_ok=True, provenance_ok=True, refusal_ok=True,
                    consulted=("crm",), expected_sources=("crm",), question="q",
                    answer="a", expected_answer="x")
    assert pe.probe_id == "p" and pe.consulted == ("crm",)
    with pytest.raises(Exception):
        pe.passed = False  # frozen dataclass


def test_report_error_is_exception():
    assert issubclass(ReportError, Exception)
