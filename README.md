# AI Security Agent

Agen keamanan berbasis AI yang menggabungkan **Wazuh SIEM** dengan **Large Language Model lokal (Ollama)** untuk analisis ancaman otomatis dalam Bahasa Indonesia.

---

## Arsitektur

```
┌─────────────────────────────────────────────┐
│           AI Security Agent (CLI)           │
│                                             │
│  ┌─────────────┐    ┌──────────────────┐   │
│  │  LLM Layer  │    │   Wazuh Client   │   │
│  │  (Ollama /  │◄──►│  API + Indexer   │   │
│  │  llama3.2)  │    │                  │   │
│  └─────────────┘    └──────────────────┘   │
└────────────────────────┬────────────────────┘
                         │
┌────────────────────────▼────────────────────┐
│              Wazuh Stack (Docker)            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Wazuh   │  │  Wazuh   │  │  Wazuh   │  │
│  │ Manager  │  │ Indexer  │  │Dashboard │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
```

## Fitur

- **Analisis Alert Otomatis** — Mengambil alert dari Wazuh dan menganalisis dengan LLM
- **Chat Interaktif** — Tanya jawab langsung dengan AI Security Analyst
- **100% Lokal** — LLM berjalan di mesin sendiri, tidak ada data keluar ke cloud
- **Bahasa Indonesia** — Semua output analisis dalam Bahasa Indonesia
- **Prioritisasi Ancaman** — Identifikasi serangan brute force, lateral movement, exfiltration

## Tech Stack

| Komponen | Teknologi |
|---|---|
| SIEM | Wazuh 4.9.0 |
| Container | Docker Compose |
| LLM | Ollama (llama3.2:3b / llama3.1:8b) |
| Agent | Python 3.10+ |
| HTTP Client | httpx (async) |
| CLI | Typer + Rich |

---

## Prasyarat

| Kebutuhan | Keterangan |
|---|---|
| OS | Windows 10/11 |
| Docker Desktop | Dengan WSL2 backend aktif |
| Ollama | Download di [ollama.com](https://ollama.com/download) |
| Python | 3.10 atau lebih baru |
| RAM | Minimal 8 GB |

---

## Instalasi

### Langkah 1 — Clone Repository

```powershell
git clone https://github.com/adamtriwibowo/ai-security.git
cd ai-security
```

### Langkah 2 — Deploy Wazuh (Docker)

```powershell
cd wazuh-docker

# Clone konfigurasi Wazuh 4.9.0
git clone https://github.com/wazuh/wazuh-docker.git stable-config --depth=1 --branch v4.9.0

# Set batas memori untuk OpenSearch (wajib di Windows)
wsl -d docker-desktop sysctl -w vm.max_map_count=262144

# Generate sertifikat SSL
cd stable-config/single-node
docker compose -f generate-indexer-certs.yml run --rm generator

# Jalankan Wazuh stack
docker compose up -d
```

> Tunggu **3–5 menit** hingga semua container berstatus `healthy`.
> Dashboard tersedia di: `https://localhost:443` (user: `admin`, password: `SecretPassword`)

### Langkah 3 — Install Ollama & Pull Model

```powershell
# Untuk RAM 8 GB
ollama pull llama3.2:3b

# Untuk RAM 16 GB+ (hasil lebih akurat)
ollama pull llama3.1:8b
```

### Langkah 4 — Setup Python Agent

```powershell
cd agent
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Langkah 5 — Konfigurasi `.env`

```powershell
copy .env.example .env
```

Edit file `.env`:

```env
WAZUH_API_URL=https://localhost:55300
WAZUH_API_USER=wazuh-wui
WAZUH_API_PASSWORD=MyS3cr37P450r.*-
WAZUH_VERIFY_SSL=false

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

ALERT_SEVERITY_THRESHOLD=7
MAX_ALERTS_PER_ANALYSIS=50
```

> **Catatan:** Port Wazuh API menggunakan `55300` karena port `55000` dicadangkan oleh Windows/Hyper-V.

---

## Cara Menjalankan

### Opsi A — Menu Interaktif (Disarankan)

Double-click file **`jalankan.bat`** di Windows Explorer.

Atau dari PowerShell:

```powershell
.\run.ps1
```

Tampilan menu:

```
  ╔══════════════════════════════════════════╗
  ║        AI SECURITY AGENT - MENU          ║
  ║      Wazuh SIEM + Ollama (LLM Lokal)     ║
  ╚══════════════════════════════════════════╝

  Status: Python venv [OK] | Ollama [OK] | Wazuh [OK]

  ─── WAZUH DOCKER ───────────────────────────
  [1]  Start Wazuh Stack
  [2]  Stop Wazuh Stack
  [3]  Status & Log Container

  ─── AI SECURITY AGENT ──────────────────────
  [4]  Cek Status Koneksi (Ollama + Wazuh)
  [5]  Analisis Alert Kritis  (level 7+, 50 alert)
  [6]  Analisis Semua Alert   (level 1+, 100 alert)
  [7]  Mode Chat Interaktif   (buka terminal baru)

  ─── SETUP ──────────────────────────────────
  [8]  Install / Update Dependencies Python
  [0]  Keluar
```

---

### Opsi B — Perintah Manual (PowerShell)

Aktifkan environment Python terlebih dahulu:

```powershell
cd agent
.\venv\Scripts\Activate.ps1
```

#### Cek Status Koneksi

```powershell
python main.py status
```

```
┌──────────────────────────────────────┐
│ Service       │ Status │ Info        │
│───────────────┼────────┼─────────────│
│ Ollama        │ OK     │ llama3.2:3b │
│ Wazuh Manager │ OK     │ v4.9.0      │
└──────────────────────────────────────┘
```

#### Analisis Alert

```powershell
# Alert kritis saja (level 7+, default)
python main.py analyze

# Semua alert mulai level 1
python main.py analyze --level 1

# Pilih jumlah alert
python main.py analyze --level 7 --limit 100
```

Contoh output:

```
Ringkasan: Sistem mendeteksi beberapa pelanggaran konfigurasi keamanan
berdasarkan CIS Benchmark.

Temuan Kritis:
- Level 5 — SCA score di bawah 80%
- Level 3 — sudo tidak terinstall

Rekomendasi:
1. Segera install sudo dan konfigurasikan privilege escalation
2. Ikuti CIS Benchmark untuk hardening sistem
```

#### Mode Chat Interaktif

> Harus dijalankan dari terminal langsung (bukan dari IDE/pipe).

```powershell
python main.py chat
```

```
AI Security Analyst
Ketik pertanyaan keamanan. 'exit' untuk keluar.

Kamu> Apa ancaman terbesar yang terdeteksi?
Kamu> Bagaimana cara meningkatkan SCA score?
Kamu> Jelaskan alert brute force yang ada
```

---

## Struktur Project

```
ai-security/
├── jalankan.bat              ← Double-click untuk buka menu
├── run.ps1                   ← Menu interaktif PowerShell
├── perintah.md               ← Referensi semua perintah
├── README.md
├── .gitignore
├── wazuh-docker/
│   └── docker-compose.yml    ← Custom port mapping (55300)
└── agent/
    ├── main.py               ← CLI entry point
    ├── requirements.txt
    ├── .env.example          ← Template konfigurasi
    └── src/
        ├── config.py         ← Settings dari .env
        ├── wazuh_client.py   ← Wazuh Manager API + Indexer client
        └── llm_agent.py      ← Ollama streaming client
```

## Port yang Digunakan

| Service | Port |
|---|---|
| Wazuh Dashboard | 443 |
| Wazuh Manager API | 55300 |
| Wazuh Indexer (OpenSearch) | 9200 |
| Ollama | 11434 |

---

## Troubleshooting

### Port 55000 tidak tersedia di Windows

Windows/Hyper-V mencadangkan range port tertentu termasuk 55000. Solusi: gunakan port `55300` seperti sudah dikonfigurasi di `wazuh-docker/docker-compose.yml`.

### Wazuh API 401 Unauthorized

Pastikan password di `.env` sama dengan yang ada di `docker-compose.yml`:
```env
WAZUH_API_PASSWORD=MyS3cr37P450r.*-
```

### Container tidak mau start / OpenSearch error

```powershell
# Wajib dijalankan setiap restart Docker Desktop
wsl -d docker-desktop sysctl -w vm.max_map_count=262144
```

### Ollama lambat atau timeout

- Pastikan tidak ada proses berat lain yang berjalan
- Coba model lebih kecil: `OLLAMA_MODEL=llama3.2:1b`
- Tambah timeout di `.env`: `OLLAMA_TIMEOUT=300`

### Mode chat tidak bisa diketik (di IDE/pipe)

Mode `chat` membutuhkan terminal interaktif langsung. Gunakan menu `[7]` di `run.ps1` yang otomatis membuka terminal baru, atau buka PowerShell secara manual dan jalankan `python main.py chat`.

---

## Lisensi

MIT License
