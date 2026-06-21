import json
import httpx
from typing import AsyncIterator
from .config import settings


SYSTEM_PROMPT = """Kamu adalah AI Security Analyst yang menganalisis alert dan event dari Wazuh SIEM.

Tugas kamu:
1. Analisis alert keamanan dan tentukan tingkat ancaman nyata (bukan hanya level Wazuh)
2. Identifikasi pola serangan (brute force, lateral movement, exfiltration, dll)
3. Berikan rekomendasi tindakan yang spesifik dan actionable
4. Gunakan bahasa Indonesia yang jelas dan profesional
5. Prioritaskan berdasarkan dampak bisnis

Format respons kamu:
- **Ringkasan**: 1-2 kalimat situasi keamanan saat ini
- **Temuan Kritis**: Alert/event yang perlu segera ditindak
- **Analisis Ancaman**: Pola dan konteks serangan yang terdeteksi
- **Rekomendasi**: Langkah mitigasi yang harus dilakukan (urutkan prioritas)
- **Monitoring**: Apa yang perlu dipantau selanjutnya

Jangan panik berlebihan pada false positive. Gunakan konteks untuk menentukan ancaman nyata."""


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
            summary_ctx = f"\nKonteks sistem: {json.dumps(context, ensure_ascii=False)}\n"

        alert_text = self._format_alerts(alerts)
        user_msg = f"""{summary_ctx}
Analisis alert keamanan berikut dari Wazuh SIEM:

{alert_text}

Berikan analisis keamanan komprehensif."""

        async for chunk in self._stream_chat(user_msg):
            yield chunk

    async def ask(self, question: str, context: str = "") -> AsyncIterator[str]:
        user_msg = f"{context}\n\nPertanyaan: {question}" if context else question
        async for chunk in self._stream_chat(user_msg):
            yield chunk

    async def _stream_chat(self, user_message: str) -> AsyncIterator[str]:
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "stream": True,
            "options": {
                "num_ctx": 8192,
                "temperature": 0.1,
                "repeat_penalty": 1.2,
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
                f"   ID: {rule.get('id', 'N/A')}"
            )
        return "\n".join(lines)

    async def close(self) -> None:
        await self._client.aclose()
