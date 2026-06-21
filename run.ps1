# AI Security Agent - Script Utama
# Cara pakai: klik kanan run.ps1 -> "Run with PowerShell"
# Atau dari terminal: .\run.ps1

$ROOT      = $PSScriptRoot
$AGENTDIR  = Join-Path $ROOT "agent"
$PYTHON    = Join-Path $AGENTDIR "venv\Scripts\python.exe"
$PIP       = Join-Path $AGENTDIR "venv\Scripts\pip.exe"
$MAINPY    = Join-Path $AGENTDIR "main.py"
$WAZUHDIR  = Join-Path $ROOT "wazuh-docker\stable-config\single-node"

function Show-Header {
    Clear-Host
    Write-Host ""
    Write-Host "  +==========================================+" -ForegroundColor Cyan
    Write-Host "  |      AI SECURITY AGENT - MENU           |" -ForegroundColor Cyan
    Write-Host "  |    Wazuh SIEM + Ollama (LLM Lokal)      |" -ForegroundColor Cyan
    Write-Host "  +==========================================+" -ForegroundColor Cyan
    Write-Host ""
}

function Show-StatusBar {
    $venvOk   = Test-Path $PYTHON
    $ollamaOk = $false
    $wazuhUp  = $false

    try {
        $null = Invoke-WebRequest -Uri "http://localhost:11434" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        $ollamaOk = $true
    } catch {}

    try {
        $containers = docker ps --filter "name=wazuh" --format "{{.Names}}" 2>$null
        if ($containers) { $wazuhUp = $true }
    } catch {}

    if ($venvOk)   { $vs = "OK" } else { $vs = "--" }
    if ($ollamaOk) { $os = "OK" } else { $os = "--" }
    if ($wazuhUp)  { $ws = "OK" } else { $ws = "--" }

    if ($venvOk)   { $vc = "Green" } else { $vc = "Red" }
    if ($ollamaOk) { $oc = "Green" } else { $oc = "DarkYellow" }
    if ($wazuhUp)  { $wc = "Green" } else { $wc = "DarkYellow" }

    Write-Host "  Status: " -NoNewline
    Write-Host "Python venv [$vs] " -ForegroundColor $vc -NoNewline
    Write-Host "| Ollama [$os] " -ForegroundColor $oc -NoNewline
    Write-Host "| Wazuh [$ws]" -ForegroundColor $wc
    Write-Host ""

    return $venvOk
}

function Pause-Menu {
    Write-Host ""
    Write-Host "  Tekan Enter untuk kembali ke menu..." -ForegroundColor DarkGray
    $null = Read-Host
}

# ── Menu Handlers ───────────────────────────────────────────

function Do-WazuhStart {
    Write-Host "  Mengatur vm.max_map_count..." -ForegroundColor Yellow
    wsl -d docker-desktop sysctl -w vm.max_map_count=262144 2>$null

    Write-Host "  Menjalankan Wazuh Docker stack..." -ForegroundColor Yellow
    Push-Location $WAZUHDIR
    docker compose up -d
    Pop-Location

    Write-Host ""
    Write-Host "  Wazuh stack dimulai. Tunggu 3-5 menit hingga semua container healthy." -ForegroundColor Green
    Write-Host "  Dashboard: https://localhost:443  (admin / SecretPassword)" -ForegroundColor DarkGray
}

function Do-WazuhStop {
    Write-Host "  Menghentikan Wazuh stack..." -ForegroundColor Yellow
    Push-Location $WAZUHDIR
    docker compose down
    Pop-Location
    Write-Host "  Wazuh dihentikan." -ForegroundColor Green
}

function Do-WazuhStatus {
    Write-Host "  Status container Wazuh:" -ForegroundColor Yellow
    Write-Host ""
    Push-Location $WAZUHDIR
    docker compose ps
    Write-Host ""
    Write-Host "  Log 20 baris terakhir:" -ForegroundColor DarkGray
    docker compose logs --tail=20
    Pop-Location
}

function Do-AgentStatus {
    Write-Host "  Memeriksa koneksi ke Ollama dan Wazuh..." -ForegroundColor Yellow
    Write-Host ""
    & $PYTHON $MAINPY status
}

function Do-Analyze {
    param([int]$Level, [int]$Limit)
    Write-Host "  Menganalisis $Limit alert dengan severity level >= $Level..." -ForegroundColor Yellow
    Write-Host ""
    & $PYTHON $MAINPY analyze --level $Level --limit $Limit
}

function Do-Chat {
    Write-Host "  Membuka mode chat di terminal baru..." -ForegroundColor Yellow
    $activate = Join-Path $AGENTDIR "venv\Scripts\Activate.ps1"
    $cmd = "Set-Location '$AGENTDIR'; & '$activate'; python main.py chat"
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $cmd
    Write-Host "  Terminal chat dibuka di jendela baru." -ForegroundColor Green
}

function Do-Setup {
    Write-Host "  Membuat Python virtual environment..." -ForegroundColor Yellow

    if (-not (Test-Path (Join-Path $AGENTDIR "venv"))) {
        python -m venv (Join-Path $AGENTDIR "venv")
    } else {
        Write-Host "  venv sudah ada, lewati pembuatan." -ForegroundColor DarkGray
    }

    Write-Host "  Menginstall dependencies..." -ForegroundColor Yellow
    & $PIP install -r (Join-Path $AGENTDIR "requirements.txt")

    $envFile    = Join-Path $AGENTDIR ".env"
    $envExample = Join-Path $AGENTDIR ".env.example"

    if (-not (Test-Path $envFile)) {
        Copy-Item $envExample $envFile
        Write-Host "  File .env dibuat dari .env.example." -ForegroundColor Green
        Write-Host "  Edit agent\.env sesuai password Wazuh Anda." -ForegroundColor DarkYellow
    } else {
        Write-Host "  .env sudah ada, tidak ditimpa." -ForegroundColor DarkGray
    }

    Write-Host "  Setup selesai!" -ForegroundColor Green
}

# ── Main Loop ───────────────────────────────────────────────

while ($true) {
    Show-Header
    $venvReady = Show-StatusBar

    Write-Host "  --- WAZUH DOCKER -------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  [1]  Start Wazuh Stack"
    Write-Host "  [2]  Stop Wazuh Stack"
    Write-Host "  [3]  Status dan Log Container"
    Write-Host ""
    Write-Host "  --- AI SECURITY AGENT --------------------------------------" -ForegroundColor DarkGray

    if ($venvReady) {
        Write-Host "  [4]  Cek Status Koneksi (Ollama + Wazuh)"
        Write-Host "  [5]  Analisis Alert Kritis  (level 7+, 50 alert)"
        Write-Host "  [6]  Analisis Semua Alert   (level 1+, 100 alert)"
        Write-Host "  [7]  Mode Chat Interaktif   (buka terminal baru)"
    } else {
        Write-Host "  [4-7] Tidak tersedia -- jalankan [8] Setup dulu" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "  --- SETUP --------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  [8]  Install / Update Dependencies Python"
    Write-Host "  [0]  Keluar"
    Write-Host ""

    $choice = Read-Host "  Pilih"

    switch ($choice) {
        "1" { Show-Header; Do-WazuhStart;                    Pause-Menu }
        "2" { Show-Header; Do-WazuhStop;                     Pause-Menu }
        "3" { Show-Header; Do-WazuhStatus;                   Pause-Menu }
        "4" { if ($venvReady) { Show-Header; Do-AgentStatus; Pause-Menu } }
        "5" { if ($venvReady) { Show-Header; Do-Analyze -Level 7 -Limit 50;  Pause-Menu } }
        "6" { if ($venvReady) { Show-Header; Do-Analyze -Level 1 -Limit 100; Pause-Menu } }
        "7" { if ($venvReady) { Do-Chat; Pause-Menu } }
        "8" { Show-Header; Do-Setup;                         Pause-Menu }
        "0" { exit }
        default {
            Write-Host "  Pilihan tidak valid." -ForegroundColor Red
            Start-Sleep -Milliseconds 800
        }
    }
}
