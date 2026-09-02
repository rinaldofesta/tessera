# tests/test_factory_values.py
import random
import re

from tessera.factory import values
from tessera.factory.schema import VALUE_TYPES

_SHAPE = {
    "money": r"^\$\d+(\.\d{2}M|k)$",
    "percent": r"^\d+(\.\d+)?%$",
    "date": r"^\d{4}-\d{2}-\d{2}$",
    "duration": r"^\d+ (hours|minutes)$",
    "person": r"^[A-Z][a-z]+ [A-Z][a-z]+$",
}


def test_every_type_is_deterministic_and_shaped():
    for vt in VALUE_TYPES:
        v1 = values.gen_value(vt, random.Random(7))
        v2 = values.gen_value(vt, random.Random(7))
        assert v1 == v2, vt                       # deterministic per seed
        if vt in _SHAPE:
            assert re.match(_SHAPE[vt], str(v1)), (vt, v1)


def test_count_is_int():
    assert isinstance(values.gen_value("count", random.Random(1)), int)


def test_distinct_pair_differs():
    for vt in VALUE_TYPES:
        a, b = values.gen_distinct_pair(vt, random.Random(3))
        assert str(a) != str(b), vt


def test_exclude_is_respected():
    rng = random.Random(5)
    first = values.gen_value("plan", random.Random(5))
    again = values.gen_value("plan", rng, exclude=(first,))
    assert str(again) != str(first)


def test_distinct_pair_avoids_substring_collisions():
    # inequality is not enough: '2.9%' and '12.9%' are distinct strings but the shorter
    # is a substring of the longer, which empties the downstream substring-based
    # distractor filter (evals/dataset._distractor_values). Neither side may contain the
    # other.
    for vt in VALUE_TYPES:
        for seed in range(200):
            a, b = values.gen_distinct_pair(vt, random.Random(seed))
            sa, sb = str(a).lower(), str(b).lower()
            assert sa not in sb and sb not in sa, (vt, seed, a, b)
