from tessera.evals.dataset import ProbeMeta, blueprint_to_dataset
from tessera.examples.toy_org import build_toy_blueprint


def test_dataset_has_one_sample_per_probe():
    ds = blueprint_to_dataset(build_toy_blueprint())
    assert len(ds.samples) == 4


def test_unresolvable_sample_expects_refusal():
    ds = blueprint_to_dataset(build_toy_blueprint())
    sample = next(s for s in ds.samples if s.id == "q_globex_contract")
    meta = sample.metadata_as(ProbeMeta)
    assert meta.conflict_type == "unresolvable"
    assert meta.expected_behavior == "refuse"
    assert sample.target == ""  # refusal -> no answer


def test_sample_carries_typed_probe_metadata():
    ds = blueprint_to_dataset(build_toy_blueprint())
    sample = next(s for s in ds.samples if s.id == "q_acme_renewal")
    meta = sample.metadata_as(ProbeMeta)
    assert meta.expected_behavior == "answer"
    assert meta.expected_answer == "2026-03-01"
    assert set(meta.expected_sources) == {"acme.renewal.crm", "acme.renewal.note"}


def test_void_sample_has_empty_target_and_refuse_behavior():
    ds = blueprint_to_dataset(build_toy_blueprint())
    sample = next(s for s in ds.samples if s.id == "q_beta_billing")
    meta = sample.metadata_as(ProbeMeta)
    assert meta.expected_behavior == "refuse"
    assert sample.target == ""  # inspect Sample.target defaults to "" (not None)


def test_probe_meta_must_be_frozen():
    assert ProbeMeta.model_config.get("frozen") is True
