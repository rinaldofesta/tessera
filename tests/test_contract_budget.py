from tessera.api.app import create_app


def test_api_route_budget_and_deleted_surfaces(tmp_path):
    paths = create_app(home=tmp_path / "home").openapi()["paths"]

    # PR6a removes the four launcher-vocabulary paths and lowers this budget to 16.
    assert len(paths) <= 19
    assert {
        "/api/trends",
        "/api/leaderboard",
        "/api/experiments",
        "/api/evaluations",
        "/api/logs",
        "/api/reports",
        "/api/preflights",
    }.isdisjoint(paths)
