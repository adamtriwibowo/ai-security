# Perintah AI Security Agent

## Cara Tercepat — Double Click
Klik dua kali file **`jalankan.bat`** → muncul menu interaktif.

---

## Dari PowerShell / Terminal

### Buka Menu Utama
```powershell
.\run.ps1
```

### Wazuh Docker
```powershell
# Start
cd wazuh-docker; docker compose up -d

# Stop
cd wazuh-docker; docker compose down

# Lihat status container
cd wazuh-docker; docker compose ps

# Lihat log real-time
cd wazuh-docker; docker compose logs -f
```

### AI Security Agent (dari folder `agent\`)
```powershell
cd agent
.\venv\Scripts\Activate.ps1          # aktifkan Python env

python main.py status                 # cek koneksi Ollama & Wazuh
python main.py analyze                # analisis alert level 7+ (50 alert)
python main.py analyze --level 1      # analisis semua alert
python main.py analyze --level 7 --limit 100   # analisis 100 alert
python main.py chat                   # mode tanya jawab interaktif
```

### Setup Pertama Kali
```powershell
cd agent
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env sesuai password Wazuh
```

---

## Akses Wazuh Dashboard
- URL: https://localhost:443
- User: `admin`
- Password: `SecretPassword`

## Catatan Port
| Service          | Port  |
|------------------|-------|
| Wazuh Dashboard  | 443   |
| Wazuh Manager API| 55300 |
| Wazuh Indexer    | 9200  |
| Ollama           | 11434 |
