# AI Security Agent - Setup Guide
## Stack: Wazuh 4.9 + Ollama (Local LLM) + Python

---

## LANGKAH 1: Install Docker Desktop

1. Download Docker Desktop dari: https://www.docker.com/products/docker-desktop/
2. Jalankan installer, **centang "Use WSL 2 instead of Hyper-V"**
3. Restart komputer setelah install
4. Buka Docker Desktop, tunggu hingga status "Running" (ikon hijau di taskbar)

Verifikasi di PowerShell:
```powershell
docker --version
docker compose version
```

---

## LANGKAH 2: Deploy Wazuh via Docker

Wazuh menggunakan script resmi untuk generate SSL certificates:

```powershell
# Masuk ke folder wazuh-docker
cd "D:\Adam Website\ai-security\wazuh-docker"

# Clone config resmi Wazuh Docker
git clone https://github.com/wazuh/wazuh-docker.git .wazuh-config --depth=1
cp -r .wazuh-config/single-node/config ./config

# Generate SSL certificates (jalankan di WSL atau Git Bash)
# Buka WSL terminal lalu jalankan:
# cd /mnt/d/Adam\ Website/ai-security/wazuh-docker
# docker compose -f .wazuh-config/single-node/generate-indexer-certs.yml run --rm generator

# Start Wazuh stack
docker compose up -d
```

**Tunggu 3-5 menit** agar semua service siap. Monitor dengan:
```powershell
docker compose logs -f wazuh.manager
```

Akses Dashboard: https://localhost (username: admin, password: SecurePassword123!)

---

## LANGKAH 3: Install Ollama

1. Download dari: https://ollama.com/download
2. Install dan jalankan
3. Pull model LLM:

```powershell
# Model ringan tapi powerful untuk security analysis
ollama pull llama3.1:8b

# Atau model yang lebih kecil jika RAM terbatas (<8GB)
ollama pull llama3.2:3b

# Verifikasi
ollama list
```

Rekomendasi berdasarkan RAM:
- RAM 8GB  → llama3.2:3b
- RAM 16GB → llama3.1:8b  (RECOMMENDED)
- RAM 32GB → llama3.1:70b

---

## LANGKAH 4: Setup Python Agent

```powershell
cd "D:\Adam Website\ai-security\agent"

# Buat virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy dan edit konfigurasi
copy .env.example .env
# Edit .env sesuai password yang kamu set
```

---

## LANGKAH 5: Jalankan Agent

```powershell
cd "D:\Adam Website\ai-security\agent"
.\venv\Scripts\Activate.ps1

# Cek status koneksi
python main.py status

# Analisis alert terbaru
python main.py analyze

# Analisis dengan filter level tinggi saja
python main.py analyze --level 10

# Mode chat interaktif
python main.py chat
```

---

## Troubleshooting

### Docker tidak bisa start
- Pastikan WSL2 sudah enabled: `wsl --install` di PowerShell (Admin)
- Restart Docker Desktop

### Wazuh dashboard tidak bisa diakses
- Tunggu lebih lama (container butuh waktu init)
- Cek: `docker compose ps` pastikan semua "healthy"

### Ollama model lambat
- Pastikan tidak ada proses berat lain berjalan
- Coba model yang lebih kecil: ubah OLLAMA_MODEL di .env

### SSL Error Wazuh API
- Set WAZUH_VERIFY_SSL=false di .env (untuk development)

---

## Arsitektur

```
main.py (CLI)
├── src/wazuh_client.py    → Koneksi ke Wazuh REST API
├── src/llm_agent.py       → Koneksi ke Ollama + analisis
└── src/config.py          → Konfigurasi dari .env
```
