import pytest

from tessera.silos.registry import SiloRegistry, SiloType, UnknownSiloTypeError


def make_silo_type(name="wiki", tools=("wiki_search",), **kwargs):
    return SiloType(
        name=name,
        server_module=f"tessera.mcp.{name}_server",
        tool_names=tuple(tools),
        prompt_blurb=f"a {name} silo",
        consulted=lambda tool, args, result, manifest: set(),
        **kwargs,
    )


def test_register_and_get_roundtrip():
    reg = SiloRegistry()
    st = make_silo_type()
    reg.register(st)
    assert reg.get("wiki") is st
    assert reg.names() == ("wiki",)


def test_get_unknown_raises_with_registered_names():
    reg = SiloRegistry()
    reg.register(make_silo_type())
    with pytest.raises(UnknownSiloTypeError, match="no silo type 'lake'.*wiki"):
        reg.get("lake")


def test_get_optional_returns_none_for_unknown():
    reg = SiloRegistry()
    assert reg.get_optional("lake") is None


def test_duplicate_name_rejected():
    reg = SiloRegistry()
    reg.register(make_silo_type())
    with pytest.raises(ValueError, match="already registered"):
        reg.register(make_silo_type(tools=("other_tool",)))


def test_duplicate_tool_name_rejected():
    reg = SiloRegistry()
    reg.register(make_silo_type())
    with pytest.raises(ValueError, match="already provided"):
        reg.register(make_silo_type(name="wiki2", tools=("wiki_search",)))


def test_tool_owner_lookup():
    reg = SiloRegistry()
    st = make_silo_type(tools=("wiki_search", "wiki_get"))
    reg.register(st)
    assert reg.tool_owner("wiki_get") is st
    assert reg.tool_owner("nope") is None


def test_build_without_write_rejected():
    with pytest.raises(ValueError, match="both build and write"):
        make_silo_type(build=lambda claims: ({}, {}))


def _fake_ep(load_result):
    class FakeEP:
        name = "fake"
        def load(self):
            return load_result
    return FakeEP()


def test_entry_point_silo_type_registers(monkeypatch):
    st = make_silo_type(name="lake", tools=("search_datasets",))
    monkeypatch.setattr(
        "tessera.silos.registry.entry_points",
        lambda group: [_fake_ep(st)] if group == "tessera.silo_types" else [],
    )
    reg = SiloRegistry()
    assert "lake" in reg.names()


def test_entry_point_callable_returning_list_registers(monkeypatch):
    st = make_silo_type(name="lake", tools=("search_datasets",))
    monkeypatch.setattr(
        "tessera.silos.registry.entry_points",
        lambda group: [_fake_ep(lambda: [st])],
    )
    reg = SiloRegistry()
    assert reg.get("lake") is st


def test_entry_point_does_not_override_existing_name(monkeypatch):
    mine = make_silo_type(name="lake", tools=("my_tool",))
    theirs = make_silo_type(name="lake", tools=("search_datasets",))
    monkeypatch.setattr(
        "tessera.silos.registry.entry_points", lambda group: [_fake_ep(theirs)]
    )
    reg = SiloRegistry()
    reg._types["lake"] = mine  # simulate earlier registration before first lookup
    assert reg.get("lake") is mine
