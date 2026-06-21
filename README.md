# AI Security Agent

Agen keamanan berbasis AI yang menggabungkan **Wazuh SIEM** dengan **Large Language Model lokal (Ollama)** untuk analisis ancaman otomatis menggunakan Bahasa Indonesia.

## Arsitektur

```
┌─────────────────────────────────────────────┐
│           AI Security Agent (CLI)           │
│                                             │
│  ┌─────────────┐    ┌──────────────────┐   │
│  │  LLM Layer  │    │   Wazuh API      │   │
│  │  (Ollama /  │◄──►│   + Indexer      │   │
│  │  llama3.2)  │    │   Client         │   │
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

## Prasyarat

- Windows 10/11 dengan Docker Desktop (WSL2)
- Ollama terinstall
- Python 3.10+
- RAM minimal 8GB

## Instalasi

### 1. Clone Repository

```bash
git clone https://github.com/adamtriwibowo/ai-security.git
cd ai-security
```

### 2. Deploy Wazuh

```bash
cd wazuh-docker

# Clone Wazuh 4.9.0 Docker config
git clone https://github.com/wazuh/wazuh-docker.git stable-config --depth=1 --branch v4.9.0

# Set vm.max_map_count (Windows dengan Docker Desktop)
wsl -d docker-desktop sysctl -w vm.max_map_count=262144

# Generate SSL certificates
cd stable-config/single-node
docker compose -f generate-indexer-certs.yml run --rm generator

# Start Wazuh stack
docker compose up -d
```

> Tunggu 3-5 menit hingga semua container healthy.

### 3. Install Ollama & Pull Model

Download Ollama di [ollama.com](https://ollama.com/download) lalu:

```bash
# RAM 8GB
ollama pull llama3.2:3b

# RAM 16GB+ (lebih akurat)
ollama pull llama3.1:8b
```

### 4. Setup Python Agent

```bash
cd agent
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

# Konfigurasi
cp .env.example .env
# Edit .env sesuai kebutuhan
```

### 5. Konfigurasi `.env`

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

> **Catatan:** Port Wazuh API menggunakan `55300` (bukan 55000) karena port tersebut dicadangkan oleh Windows.

## Penggunaan

```bash
cd agent
.\venv\Scripts\Activate.ps1  # Windows
```

### Cek Status Koneksi

```bash
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

### Analisis Alert

```bash
# Analisis alert level 7+ (default)
python main.py analyze

# Analisis semua alert (level 1+)
python main.py analyze --level 1

# Analisis 100 alert terbaru
python main.py analyze --level 7 --limit 100
```

Contoh output:
```
**Ringkasan**: Sistem mendeteksi beberapa pelanggaran konfigurasi keamanan 
berdasarkan CIS Benchmark.

**Temuan Kritis**:
- Level 5 - SCA score di bawah 80%
- Level 3 - sudo tidak terinstall

**Rekomendasi**:
1. Segera install sudo dan konfigurasikan privilege escalation
2. Ikuti CIS Benchmark untuk hardening sistem
```

### Mode Chat Interaktif

```bash
python main.py chat
```

```
AI Security Analyst
Ketik pertanyaan keamanan. 'exit' untuk keluar.

Kamu> Apa ancaman terbesar yang terdeteksi?
Kamu> Bagaimana cara meningkatkan SCA score?
Kamu> Jelaskan alert brute force yang ada
```

## Struktur Project

```
ai-security/
├── README.md
├── .gitignore
├── wazuh-docker/
│   └── docker-compose.yml          # Custom port mapping (55300)
└── agent/
    ├── main.py                     # CLI entry point
    ├── requirements.txt
    ├── .env.example
    └── src/
        ├── config.py               # Settings dari .env
        ├── wazuh_client.py         # Wazuh Manager API + Indexer client
        └── llm_agent.py            # Ollama streaming client
```

## Troubleshooting

### Port 55000 tidak tersedia di Windows
Windows mencadangkan range port tertentu. Gunakan port `55300`:
```yaml
# wazuh-docker/docker-compose.yml
ports:
  - "55300:55000"  # host:container
```

### Wazuh API 401 Unauthorized
Pastikan password di `.env` sesuai dengan `docker-compose.yml`:
```env
WAZUH_API_PASSWORD=MyS3cr37P450r.*-
```

### Ollama lambat / timeout
- Pastikan tidak ada proses berat lain berjalan
- Coba model lebih kecil: `OLLAMA_MODEL=llama3.2:1b`
- Tambah timeout: `OLLAMA_TIMEOUT=300`

## Lisensi

MIT License
