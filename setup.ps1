# VMware Aria Operations Prometheus Exporter Setup Script
# PowerShell script for Windows

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("standalone", "with-stack", "existing-stack")]
    [string]$Mode = "with-stack",
    
    [Parameter(Mandatory=$false)]
    [int]$ExporterPort = 8000,
    
    [Parameter(Mandatory=$false)]
    [int]$PrometheusPort = 9090,
    
    [Parameter(Mandatory=$false)]
    [int]$GrafanaPort = 3000,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigFile = "config.yaml",
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

function Show-Help {
    Write-Host "VMware Aria Operations Prometheus Exporter Setup" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\setup.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -Mode <mode>           Setup mode: standalone, with-stack, existing-stack" -ForegroundColor White
    Write-Host "  -ExporterPort <port>   Exporter port (default: 8000)" -ForegroundColor White
    Write-Host "  -PrometheusPort <port> Prometheus port (default: 9090)" -ForegroundColor White
    Write-Host "  -GrafanaPort <port>    Grafana port (default: 3000)" -ForegroundColor White
    Write-Host "  -ConfigFile <file>     Config file path (default: config.yaml)" -ForegroundColor White
    Write-Host "  -Help                  Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Modes:" -ForegroundColor Yellow
    Write-Host "  standalone      - Run only the exporter" -ForegroundColor White
    Write-Host "  with-stack      - Run exporter + Prometheus + Grafana (default)" -ForegroundColor White
    Write-Host "  existing-stack  - Configure for existing Prometheus/Grafana" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\setup.ps1 -Mode standalone -ExporterPort 8001" -ForegroundColor White
    Write-Host "  .\setup.ps1 -Mode with-stack -PrometheusPort 9091 -GrafanaPort 3001" -ForegroundColor White
    Write-Host "  .\setup.ps1 -Mode existing-stack" -ForegroundColor White
}

function Test-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Yellow
    
    # Check Docker
    if ($Mode -ne "standalone") {
        try {
            docker --version | Out-Null
            Write-Host "✓ Docker found" -ForegroundColor Green
        } catch {
            Write-Host "✗ Docker not found. Please install Docker first." -ForegroundColor Red
            exit 1
        }
        
        try {
            docker-compose --version | Out-Null
            Write-Host "✓ Docker Compose found" -ForegroundColor Green
        } catch {
            Write-Host "✗ Docker Compose not found. Please install Docker Compose first." -ForegroundColor Red
            exit 1
        }
    }
    
    # Check Python for standalone mode
    if ($Mode -eq "standalone") {
        try {
            python --version | Out-Null
            Write-Host "✓ Python found" -ForegroundColor Green
        } catch {
            Write-Host "✗ Python not found. Please install Python 3.8+ first." -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "Prerequisites check completed." -ForegroundColor Green
    Write-Host ""
}

function Setup-Environment {
    Write-Host "Setting up environment..." -ForegroundColor Yellow
    
    # Create .env file if not exists
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env") {
            Copy-Item ".env" ".env.local"
            Write-Host "✓ Created .env.local from template" -ForegroundColor Green
        } else {
            Write-Host "⚠ .env template not found. Please create .env file manually." -ForegroundColor Yellow
        }
    } else {
        Write-Host "✓ .env file already exists" -ForegroundColor Green
    }
    
    Write-Host "Environment setup completed." -ForegroundColor Green
    Write-Host ""
}

function Setup-Standalone {
    Write-Host "Setting up standalone exporter..." -ForegroundColor Yellow
    
    # Install Python dependencies
    Write-Host "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Update config if port is different
    if ($ExporterPort -ne 8000) {
        Write-Host "Updating exporter port to $ExporterPort..."
        $config = Get-Content $ConfigFile -Raw
        $config = $config -replace "port: 8000", "port: $ExporterPort"
        Set-Content $ConfigFile $config
    }
    
    Write-Host "✓ Standalone setup completed" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start the exporter:" -ForegroundColor Yellow
    Write-Host "  python vmware_aria_exporter_advanced.py --config $ConfigFile" -ForegroundColor White
    Write-Host ""
    Write-Host "Exporter will be available at: http://localhost:$ExporterPort/metrics" -ForegroundColor Green
}

function Setup-WithStack {
    Write-Host "Setting up full stack (Exporter + Prometheus + Grafana)..." -ForegroundColor Yellow
    
    # Create override file if ports are different
    if ($ExporterPort -ne 8000 -or $PrometheusPort -ne 9090 -or $GrafanaPort -ne 3000) {
        Write-Host "Creating docker-compose.override.yml for custom ports..."
        
        $override = @"
version: '3.8'
services:
  vmware-aria-exporter:
    ports:
      - "$ExporterPort`:8000"
  prometheus:
    ports:
      - "$PrometheusPort`:9090"
  grafana:
    ports:
      - "$GrafanaPort`:3000"
"@
        Set-Content "docker-compose.override.yml" $override
        Write-Host "✓ Created docker-compose.override.yml" -ForegroundColor Green
    }
    
    # Start services
    Write-Host "Starting Docker services..."
    docker-compose up -d
    
    Write-Host "✓ Full stack setup completed" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services are available at:" -ForegroundColor Yellow
    Write-Host "  Exporter metrics: http://localhost:$ExporterPort/metrics" -ForegroundColor White
    Write-Host "  Prometheus:       http://localhost:$PrometheusPort" -ForegroundColor White
    Write-Host "  Grafana:          http://localhost:$GrafanaPort (admin/admin)" -ForegroundColor White
}

function Setup-ExistingStack {
    Write-Host "Configuring for existing Prometheus/Grafana stack..." -ForegroundColor Yellow
    
    # Install Python dependencies
    Write-Host "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Update config if port is different
    if ($ExporterPort -ne 8000) {
        Write-Host "Updating exporter port to $ExporterPort..."
        $config = Get-Content $ConfigFile -Raw
        $config = $config -replace "port: 8000", "port: $ExporterPort"
        Set-Content $ConfigFile $config
    }
    
    # Show Prometheus configuration
    Write-Host "✓ Exporter configuration completed" -ForegroundColor Green
    Write-Host ""
    Write-Host "Add this job to your Prometheus configuration:" -ForegroundColor Yellow
    Write-Host @"
scrape_configs:
  - job_name: 'vmware-aria-operations'
    static_configs:
      - targets: ['localhost:$ExporterPort']
    scrape_interval: 60s
    scrape_timeout: 30s
    metrics_path: /metrics
"@ -ForegroundColor White
    
    Write-Host ""
    Write-Host "To start the exporter:" -ForegroundColor Yellow
    Write-Host "  python vmware_aria_exporter_advanced.py --config $ConfigFile" -ForegroundColor White
    Write-Host ""
    Write-Host "Don't forget to:" -ForegroundColor Yellow
    Write-Host "  1. Reload Prometheus configuration" -ForegroundColor White
    Write-Host "  2. Import Grafana dashboard from grafana/dashboards/vmware-aria-overview.json" -ForegroundColor White
}

function Main {
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Host "VMware Aria Operations Prometheus Exporter Setup" -ForegroundColor Green
    Write-Host "Mode: $Mode" -ForegroundColor Yellow
    Write-Host "Exporter Port: $ExporterPort" -ForegroundColor Yellow
    if ($Mode -ne "standalone") {
        Write-Host "Prometheus Port: $PrometheusPort" -ForegroundColor Yellow
        Write-Host "Grafana Port: $GrafanaPort" -ForegroundColor Yellow
    }
    Write-Host ""
    
    Test-Prerequisites
    Setup-Environment
    
    switch ($Mode) {
        "standalone" { Setup-Standalone }
        "with-stack" { Setup-WithStack }
        "existing-stack" { Setup-ExistingStack }
    }
    
    Write-Host "Setup completed successfully!" -ForegroundColor Green
}

# Run main function
Main