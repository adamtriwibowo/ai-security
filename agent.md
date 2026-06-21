# AI Security Agent — Progress & Konteks

File ini mencatat semua progress, bug, dan perbaikan selama pengembangan.
Dibaca oleh Claude di session berikutnya untuk melanjutkan dari titik terakhir.

---

## Ringkasan Proyek

**Tujuan:** Agen keamanan berbasis AI yang menggabungkan Wazuh SIEM dengan LLM lokal (Ollama) untuk analisis ancaman otomatis dalam Bahasa Indonesia.

**Stack:**
- Wazuh 4.9.0 (Manager + Indexer/OpenSearch + Dashboard) via Docker Compose
- Ollama `llama3.2:3b` (2.0 GB, Q4_K_M)
- Python 3.14.3 — httpx, pydantic-settings, typer, rich
- OS: Windows 11 Home, GPU: AMD Radeon RX 6800M

**Repository:** https://github.com/adamtriwibowo/ai-security.git

---

## Struktur Project

```
ai-security/
├── jalankan.bat                    ← Double-click launcher Windows
├── run.ps1                         ← Menu interaktif PowerShell
├── perintah.md                     ← Referensi perintah manual
├── agent.md                        ← File ini
├── README.md
├── .gitignore
├── wazuh-docker/
│   ├── docker-compose.yml          ← Custom port 55300 (tidak dipakai langsung)
│   └── stable-config/              ← GITIGNORED — clone wazuh/wazuh-docker v4.9.0
│       └── single-node/            ← DIREKTORI AKTIF untuk docker compose
│           ├── docker-compose.yml  ← Port 55300:55000
│           └── config/             ← SSL certs & config (generated)
└── agent/
    ├── main.py                     ← CLI: analyze, chat, status
    ├── requirements.txt
    ├── .env                        ← GITIGNORED — konfigurasi aktual
    ├── .env.example                ← Template (committed)
    └── src/
        ├── __init__.py
        ├── config.py               ← pydantic-settings, path .env absolut
        ├── wazuh_client.py         ← Wazuh Manager API + OpenSearch Indexer
        └── llm_agent.py            ← Ollama streaming client + chat history

```

---

## Cara Menjalankan (Urutan Setiap Sesi)

```powershell
# 1. Start Wazuh (setelah restart PC)
wsl -d docker-desktop sysctl -w vm.max_map_count=262144
cd "D:\Adam Website\ai-security\wazuh-docker\stable-config\single-node"
docker compose up -d

# 2. Pastikan Ollama berjalan (system tray)

# 3. Jalankan agent
cd "D:\Adam Website\ai-security"
.\run.ps1        # Menu interaktif
# ATAU double-click jalankan.bat
```

**Port penting:**
| Service | Port |
|---|---|
| Wazuh Dashboard | 443 (https://localhost:443) |
| Wazuh Manager API | 55300 |
| Wazuh Indexer (OpenSearch) | 9200 |
| Ollama | 11434 |

**Kredensial:**
- Dashboard: `admin` / `SecretPassword`
- API: `wazuh-wui` / `MyS3cr37P450r.*-`

---

## Log Progress

### [Sesi 1 — sebelum 2026-06-21]

**Selesai:**
- Setup Docker Desktop + WSL2 di Windows 11
- Deploy Wazuh 4.9.0 single-node via Docker
- Install Ollama + pull `llama3.2:3b`
- Buat Python agent: `config.py`, `wazuh_client.py`, `llm_agent.py`, `main.py`
- Perintah CLI: `analyze`, `chat`, `status`
- Test `python main.py analyze --level 1` → berhasil analisis 50 alert
- Commit & push ke GitHub (commit `5400e5a`)

**Bug yang ditemukan & diperbaiki:**
- Wazuh 5.0.0-beta3 packages 403 → clone ulang dengan `--branch v4.9.0`
- Port 55000 dicadangkan Windows → ganti ke `55300:55000`
- Credentials API salah (`MyS3cur3P4ssw0rd!`) → pakai `MyS3cr37P450r.*-`
- Endpoint `/security/events` tidak ada di Wazuh 4.x → query ke OpenSearch port 9200
- PowerShell heredoc tidak support `$(cat <<'EOF'...)` → pakai `@'...'@`

---

### [Sesi 2 — 2026-06-21]

#### 2026-06-21 ~16:00 — Script Launcher

**Dibuat:**
- `run.ps1` — menu interaktif PowerShell dengan status bar Ollama/Wazuh
- `jalankan.bat` — launcher double-click untuk Windows Explorer
- `perintah.md` — referensi semua perintah manual

**Commit:** `ca45318` — feat: tambah script jalankan program

---

#### 2026-06-21 ~16:30 — Fix run.ps1 Syntax Error

**Bug:** PowerShell 5.1 tidak bisa parse `[OK]` sebagai string (dianggap array index) dan `&` di string tidak diizinkan.

**Fix:**
- Ganti inline `if` assignment ke blok `if/else` terpisah
- Ganti `&` di string dengan kata "dan"

**Commit:** `efa739a` — fix: perbaiki syntax error run.ps1 di PowerShell 5.1

---

#### 2026-06-21 ~17:00 — Fix Wazuh Start Path

**Bug:** `run.ps1` mengarah ke `wazuh-docker/` yang `docker-compose.yml`-nya tidak punya config files. Wazuh harus dijalankan dari `wazuh-docker/stable-config/single-node/`.

**Fix:**
- `run.ps1`: `$WAZUHDIR` diubah ke `wazuh-docker\stable-config\single-node`
- `wazuh-docker/docker-compose.yml`: port diubah dari `55000:55000` ke `55300:55000`

**Commit:** `30ab299` — fix: run.ps1 arahkan ke stable-config/single-node

---

#### 2026-06-21 ~17:20 — Bug Output @@@@@ (Vulkan GPU)

**Bug:** Model LLM menghasilkan karakter `@@@@@@@@@` berulang setiap kali dipanggil.

**Investigasi:**
1. Model `llama3.2:3b` dicurigai korup → hapus + download ulang → masih `@@@`
2. Ollama di-restart → masih `@@@`
3. `qwen2.5:3b` dicoba → sama saja `@@@`
4. Cek `server.log` → model diload ke **Vulkan0 (AMD Radeon RX 6800M)**
5. **Root cause:** Ollama di-upgrade ke **v0.30.10** pada 2026-06-21 15:53 — versi ini punya bug Vulkan backend pada AMD GPU yang menghasilkan token garbage

**Fix:**
- Tambah `"num_gpu": 0` di options Ollama API request → paksa CPU inference
- `num_ctx` turun ke 4096, `repeat_penalty` 1.1

**File:** `agent/src/llm_agent.py` — options payload

**Commit:** `263ff53` → `066adc4`

> **Catatan penting:** Jangan set `OLLAMA_NUM_GPU=0` via env var — tidak efektif karena llama-server subprocess tidak mewarisinya. Harus via `"options": {"num_gpu": 0}` di setiap API request.

---

#### 2026-06-21 ~17:30 — Fix config.py Path .env

**Bug:** `config.py` menggunakan `env_file = ".env"` (path relatif). Ketika agent dijalankan dari direktori lain, pydantic-settings tidak menemukan `.env` dan fallback ke default (`llama3.1:8b`).

**Fix:**
```python
from pathlib import Path
_ENV_FILE = Path(__file__).parent.parent / ".env"

class Config:
    env_file = str(_ENV_FILE)
```

**Commit:** `066adc4` — fix: paksa CPU mode + fix path .env absolut

---

#### 2026-06-21 ~17:50 — Perbaikan Chat Mode

**Bug:** Chat mode selalu menjawab dengan ringkasan generik yang sama karena:
1. Context yang dikirim ke LLM hanya `"380 alert, 1 agent aktif"` — tidak ada detail
2. Tidak ada history percakapan — setiap pertanyaan dianggap independen

**Fix di `llm_agent.py`:**
- Method `ask()` sekarang menerima `messages: list[dict]` (full conversation history)
- Tambah method `format_wazuh_context()` yang memformat detail 15 alert (level, deskripsi, agent, waktu)
- `_stream_chat()` menerima full messages list, bukan single user message

**Fix di `main.py`:**
- History percakapan disimpan sebagai list `[{"role": "user/assistant", "content": "..."}]`
- Context Wazuh di-seed ke awal history (detail 20 alert terbaru)
- Keyword detection: jika pertanyaan mengandung kata seperti "alert", "ancaman", "terbaru" → refresh data Wazuh otomatis
- Perintah `refresh` → update data Wazuh manual
- History dibatasi 20 pesan terakhir (10 turn) agar tidak overflow context window

**Commit:** `a2fc046` — feat: perbaiki chat mode - history percakapan + context Wazuh detail

---

## Status Fitur

| Fitur | Status | Commit |
|---|---|---|
| Wazuh Docker deployment | ✅ Selesai | `5400e5a` |
| Ollama integration | ✅ Selesai | `5400e5a` |
| CLI analyze | ✅ Selesai | `5400e5a` |
| CLI status | ✅ Selesai | `5400e5a` |
| CLI chat (basic) | ✅ Selesai | `5400e5a` |
| Script launcher (run.ps1) | ✅ Selesai | `ca45318` |
| Chat history percakapan | ✅ Selesai | `a2fc046` |
| Context Wazuh detail di chat | ✅ Selesai | `a2fc046` |
| Auto-refresh data Wazuh di chat | ✅ Selesai | `a2fc046` |
| VirusTotal integration | 🔲 Belum | — |
| WhatsApp bot (Baileys) | 🔲 Belum | — |
| Auto-start Wazuh (Task Scheduler) | 🔲 Belum | — |
| FastAPI HTTP server | 🔲 Belum | — |

---

## Rencana Berikutnya

### VirusTotal Integration
- Tambah `agent/src/vt_client.py`
- Endpoint: `https://www.virustotal.com/api/v3/`
- Kebutuhan: API key gratis (4 req/menit) dari virustotal.com
- Fungsi: enrichment IP/hash/domain dari alert Wazuh
- Integrasi ke `analyze` dan `chat`

### WhatsApp Bot (Baileys)
- Butuh Node.js terinstall
- Tambah folder `whatsapp-bot/` dengan Baileys
- Tambah FastAPI server ke Python agent (`agent/api.py`)
- Flow: WhatsApp message → Baileys → POST /chat → LLM → WhatsApp reply

### Auto-start Wazuh
- Buat Windows Task Scheduler task
- Trigger: saat login Windows
- Action: jalankan PowerShell script start Wazuh
- Catatan: `vm.max_map_count` harus diset dulu sebelum `docker compose up`

---

## Known Issues & Catatan Teknis

### Ollama Vulkan Bug (v0.30.10)
- **Versi bermasalah:** Ollama 0.30.10 pada AMD Radeon RX 6800M
- **Gejala:** Output LLM berupa `@@@@@` berulang
- **Workaround aktif:** `"num_gpu": 0` di setiap API request
- **Status downgrade:** Winget hanya punya 0.30.9, proses install sempat stuck
- **Jika Ollama diupdate:** Cek ulang apakah `num_gpu: 0` masih diperlukan

### vm.max_map_count
- Wajib diset ulang setiap kali Docker Desktop restart
- Command: `wsl -d docker-desktop sysctl -w vm.max_map_count=262144`
- Tanpa ini, Wazuh Indexer (OpenSearch) gagal start

### Port Windows Conflict
- Port 55000 dicadangkan oleh Hyper-V/WSL2 (range 54904–55003)
- Solusi permanen: Wazuh API di-map ke port 55300

### Wazuh API vs Indexer
- Alert disimpan di **OpenSearch (port 9200)**, bukan di Manager API
- Manager API (port 55300): agents, SCA, vulnerability, rules
- Indexer (port 9200): alert queries via `wazuh-alerts-4.x-*` index

### config.py Path
- Gunakan path absolut via `Path(__file__)`, bukan relative `".env"`
- Agent bisa dijalankan dari direktori mana pun

### Chat Mode
- Mode `chat` butuh terminal interaktif (stdin)
- Tidak bisa dijalankan dari Claude Code terminal langsung
- Gunakan menu `[7]` di `run.ps1` yang membuka terminal baru otomatis
