import httpx
from typing import Any
from .config import settings

# Wazuh 4.x stores alerts in OpenSearch (port 9200), not the Manager API
# Manager API (port 55300) handles agents, SCA, vulnerability, rules
INDEXER_URL = "https://localhost:9200"
INDEXER_CREDS = ("admin", "SecretPassword")  # default Wazuh indexer creds


class WazuhClient:
    def __init__(self):
        self._token: str | None = None
        self._client = httpx.AsyncClient(
            base_url=settings.wazuh_api_url,
            verify=settings.wazuh_verify_ssl,
            timeout=30,
        )
        self._indexer = httpx.AsyncClient(
            base_url=INDEXER_URL,
            verify=False,
            timeout=30,
        )

    async def authenticate(self) -> None:
        resp = await self._client.post(
            "/security/user/authenticate",
            auth=(settings.wazuh_api_user, settings.wazuh_api_password),
        )
        resp.raise_for_status()
        self._token = resp.json()["data"]["token"]
        self._client.headers.update({"Authorization": f"Bearer {self._token}"})

    async def _get(self, path: str, params: dict | None = None) -> Any:
        if not self._token:
            await self.authenticate()
        resp = await self._client.get(path, params=params)
        if resp.status_code == 401:
            await self.authenticate()
            resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _indexer_search(self, index: str, query: dict) -> list[dict]:
        resp = await self._indexer.post(
            f"/{index}/_search",
            json=query,
            auth=("admin", "SecretPassword"),
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        return [h["_source"] for h in hits]

    async def get_alerts(
        self,
        limit: int = 50,
        min_level: int = 7,
        offset: int = 0,
    ) -> list[dict]:
        query = {
            "size": limit,
            "from": offset,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {
                "range": {"rule.level": {"gte": min_level}}
            },
        }
        return await self._indexer_search("wazuh-alerts-4.x-*", query)

    async def get_agents(self, status: str = "all") -> list[dict]:
        params: dict = {"limit": 500, "sort": "-dateAdd"}
        if status != "all":
            params["status"] = status
        data = await self._get("/agents", params=params)
        return data.get("data", {}).get("affected_items", [])

    async def get_agent_vulnerabilities(self, agent_id: str) -> list[dict]:
        data = await self._get(
            f"/vulnerability/{agent_id}",
            params={"limit": 100, "sort": "-severity"},
        )
        return data.get("data", {}).get("affected_items", [])

    async def get_sca_results(self, agent_id: str) -> list[dict]:
        data = await self._get(f"/sca/{agent_id}", params={"limit": 100})
        return data.get("data", {}).get("affected_items", [])

    async def get_manager_info(self) -> dict:
        data = await self._get("/manager/info")
        return data.get("data", {})

    async def get_stats_summary(self) -> dict:
        # Count total alerts from indexer
        count_resp = await self._indexer.post(
            "/wazuh-alerts-4.x-*/_count",
            json={"query": {"match_all": {}}},
            auth=("admin", "SecretPassword"),
        )
        total_alerts = 0
        if count_resp.status_code == 200:
            total_alerts = count_resp.json().get("count", 0)

        agents_active = await self._get("/agents", params={"status": "active", "limit": 1})
        agents_disc = await self._get("/agents", params={"status": "disconnected", "limit": 1})

        return {
            "total_alerts": total_alerts,
            "active_agents": agents_active.get("data", {}).get("total_affected_items", 0),
            "disconnected_agents": agents_disc.get("data", {}).get("total_affected_items", 0),
        }

    async def close(self) -> None:
        await self._client.aclose()
        await self._indexer.aclose()
