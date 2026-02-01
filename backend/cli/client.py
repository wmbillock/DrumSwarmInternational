"""HTTP client for API mode — talks to the running DCI Swarm backend."""

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"


class APIClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        resp = self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get(self, path: str, **params) -> dict | list:
        return self._request("GET", path, params=params)

    def post(self, path: str, data: dict | None = None) -> dict | list:
        return self._request("POST", path, json=data)

    def ping(self) -> bool:
        """Check if the API is reachable."""
        try:
            self._client.post("/api/heartbeat", timeout=3.0)
            return True
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            return False

    # --- Season ---
    def season_create(self, name: str, year: int | None = None) -> dict:
        return self.post("/api/seasons", {"name": name, "year": year})

    # --- Corps ---
    def corps_list(self, season_id: str | None = None) -> list:
        shows = self.get("/api/shows-overview")
        return shows

    def corps_status(self, corps_id: str) -> dict:
        return self.get(f"/api/corps/{corps_id}")

    # --- Shows ---
    def show_create(self, title: str, description: str | None = None) -> dict:
        return self.post("/api/shows", {"title": title, "description": description})

    def show_activate(self, show_id: str) -> dict:
        return self.post(f"/api/shows/{show_id}/activate")

    def show_list(self) -> list:
        return self.get("/api/shows")

    # --- Mode ---
    def mode_switch(self, corps_id: str, mode: str) -> dict:
        return self.post(f"/api/corps/{corps_id}/mode", {"mode": mode})

    # --- Score ---
    def score_submit(self, corps_id: str, caption: str, value: float) -> dict:
        return self.post("/api/scores", {
            "judge_type": caption,
            "value": value,
            "box": 1,
        })

    # --- Status / Health ---
    def system_health(self) -> dict:
        return self.get("/api/system-health")

    def scoresheet(self, corps_id: str) -> dict:
        return self.get(f"/api/corps/{corps_id}/scoresheet")

    # --- Work log ---
    def work_log(self, corps_id: str, limit: int = 50) -> list:
        return self.get(f"/api/corps/{corps_id}/work-log", limit=limit)

    def global_log(self, limit: int = 50) -> list:
        return self.get("/api/work-log", limit=limit)

    # --- Commands ---
    def execute_command(self, corps_id: str, command: str) -> dict:
        return self.post(f"/api/corps/{corps_id}/command", {"command": command})

    # --- Draft ---
    def draft_run(self, corps_id: str) -> dict:
        """Activate a show's corps to trigger agent drafting."""
        # Find the show for this corps and activate it
        shows = self.show_list()
        for s in shows:
            if s.get("corps_id") == corps_id:
                return self.show_activate(s["id"])
        return {"error": "No show found for this corps"}
