"""Thin httpx client for the Tessera API. Base URL is configurable via TESSERA_API_URL."""

from __future__ import annotations

import os

import httpx

DEFAULT_URL = os.environ.get("TESSERA_API_URL", "http://127.0.0.1:8000")


class TesseraAPI:
    def __init__(self, base_url: str = DEFAULT_URL, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def list_logs(self) -> list[dict]:
        r = self._client.get("/api/logs")
        r.raise_for_status()
        return r.json()

    def list_orgs(self) -> list[str]:
        r = self._client.get("/api/orgs")
        r.raise_for_status()
        return r.json()

    def list_models(self) -> list[str]:
        r = self._client.get("/api/models")
        r.raise_for_status()
        return r.json()

    def get_report(self, log_id: str) -> dict:
        r = self._client.get(f"/api/logs/{log_id}/report")
        r.raise_for_status()
        return r.json()

    def upload(self, name: str, data: bytes) -> dict:
        r = self._client.post("/api/reports",
                              files={"file": (name, data, "application/octet-stream")})
        if r.status_code == 400:
            raise ValueError(r.json().get("detail", "cannot read log"))
        r.raise_for_status()
        return r.json()

    def start_run(self, payload: dict) -> dict:
        r = self._client.post("/api/runs", json=payload)
        if r.status_code == 400:
            raise ValueError(r.json().get("detail", "bad request"))
        r.raise_for_status()
        return r.json()

    def poll(self, job_id: str) -> dict:
        r = self._client.get(f"/api/runs/{job_id}")
        r.raise_for_status()
        return r.json()
