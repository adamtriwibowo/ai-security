import json
import httpx
from typing import AsyncIterator
from .config import settings


SYSTEM_PROMPT = """Kamu adalah AI Security Analyst yang membantu tim keamanan menganalisis data dari Wazuh SIEM.

Panduan menjawab:
- Jawab SESUAI pertanyaan yang diajukan, jangan selalu membahas semua alert
- Jika ditanya tentang ancaman spesifik, fokus ke ancaman itu
- Jika ditanya konsep keamanan umum (brute force, malware, dll), jelaskan konsepnya
- Jika ditanya tentang data Wazuh, gunakan data konteks yang diberikan
- Jika ditanya rekomendasi, berikan langkah konkret
- Gunakan Bahasa Indonesia yang jelas dan profesional
- Jawab ringkas dan tepat sasaran, jangan bertele-tele"""


class LLMAgent:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )

    async def check_ollama(self) -> bool:
        try:
            resp = await self._client.get("/api/tags")
            models = [m["name"] for m in resp.json().get("models", [])]
            return any(settings.ollama_model in m for m in models)
        except Exception:
            return False

    async def analyze_alerts(
        self,
        alerts: list[dict],
        context: dict | None = None,
    ) -> AsyncIterator[str]:
        summary_ctx = ""
        if context:
            summary_ctx = f"Statistik sistem: {json.dumps(context, ensure_ascii=False)}\n\n"

        alert_text = self._format_alerts(alerts)
        messages = [
            {
                "role": "user",
                "content": (
                    f"{summary_ctx}"
                    f"Analisis alert keamanan berikut dari Wazuh SIEM dan berikan:\n"
                    f"- Ringkasan situasi\n"
                    f"- Temuan kritis\n"
                    f"- Analisis ancaman\n"
                    f"- Rekomendasi prioritas\n"
                    f"- Apa yang perlu dipantau\n\n"
                    f"{alert_text}"
                ),
            }
        ]
        async for chunk in self._stream_chat(messages):
            yield chunk

    async def ask(self, messages: list[dict]) -> AsyncIterator[str]:
        """Chat dengan history percakapan penuh."""
        async for chunk in self._stream_chat(messages):
            yield chunk

    async def _stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        payload = {
            "model": settings.ollama_model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "stream": True,
            "options": {
                "num_gpu": 0,
                "num_ctx": 4096,
                "temperature": 0.3,
                "repeat_penalty": 1.1,
                "num_predict": 1024,
            },
        }

        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

    def _format_alerts(self, alerts: list[dict]) -> str:
        if not alerts:
            return "Tidak ada alert yang ditemukan."

        lines = [f"Total alert: {len(alerts)}\n"]
        for i, alert in enumerate(alerts[:10], 1):
            rule = alert.get("rule", {})
            agent = alert.get("agent", {})
            lines.append(
                f"{i}. [{alert.get('timestamp', 'N/A')}] "
                f"Level {rule.get('level', '?')} - {rule.get('description', 'N/A')}\n"
                f"   Agent: {agent.get('name', 'N/A')} ({agent.get('ip', 'N/A')})\n"
                f"   Groups: {', '.join(rule.get('groups', []))}\n"
                f"   Rule ID: {rule.get('id', 'N/A')}"
            )
        return "\n".join(lines)

    def format_wazuh_context(self, stats: dict, alerts: list[dict]) -> str:
        """Buat ringkasan Wazuh yang detail untuk konteks chat."""
        lines = [
            "=== DATA WAZUH SAAT INI ===",
            f"Total alert: {stats.get('total_alerts', 0)}",
            f"Agent aktif: {stats.get('active_agents', 0)}",
            f"Agent disconnect: {stats.get('disconnected_agents', 0)}",
        ]

        if alerts:
            lines.append(f"\nAlert terbaru ({len(alerts)} alert):")
            for i, alert in enumerate(alerts[:15], 1):
                rule = alert.get("rule", {})
                agent = alert.get("agent", {})
                ts = alert.get("timestamp", "")[:19].replace("T", " ")
                lines.append(
                    f"{i}. [Level {rule.get('level', '?')}] {rule.get('description', 'N/A')}"
                    f" | Agent: {agent.get('name', 'N/A')} | {ts}"
                )
        else:
            lines.append("\nTidak ada alert terbaru.")

        return "\n".join(lines)

    async def close(self) -> None:
        await self._client.aclose()
