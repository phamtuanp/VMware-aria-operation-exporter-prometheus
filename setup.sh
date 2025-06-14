#!/bin/bash
# VMware Aria Operations Prometheus Exporter Setup Script
# Bash script for Linux/Ubuntu

set -e

# Default values
MODE="with-stack"
EXPORTER_PORT=8000
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
CONFIG_FILE="config.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${GREEN}VMware Aria Operations Prometheus Exporter Setup${NC}"
    echo ""
    echo -e "${YELLOW}Usage: ./setup.sh [OPTIONS]${NC}"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo -e "  -m, --mode <mode>           Setup mode: standalone, with-stack, existing-stack"
    echo -e "  -e, --exporter-port <port>  Exporter port (default: 8000)"
    echo -e "  -p, --prometheus-port <port> Prometheus port (default: 9090)"
    echo -e "  -g, --grafana-port <port>   Grafana port (default: 3000)"
    echo -e "  -c, --config <file>         Config file path (default: config.yaml)"
    echo -e "  -h, --help                  Show this help message"
    echo ""
    echo -e "${YELLOW}Modes:${NC}"
    echo -e "  standalone      - Run only the exporter"
    echo -e "  with-stack      - Run exporter + Prometheus + Grafana (default)"
    echo -e "  existing-stack  - Configure for existing Prometheus/Grafana"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ./setup.sh -m standalone -e 8001"
    echo -e "  ./setup.sh -m with-stack -p 9091 -g 3001"
    echo -e "  ./setup.sh -m existing-stack"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker for non-standalone modes
    if [[ "$MODE" != "standalone" ]]; then
        if ! command -v docker &> /dev/null; then
            log_error "Docker not found. Please install Docker first."
            echo "Installation guide: https://docs.docker.com/engine/install/ubuntu/"
            exit 1
        fi
        log_success "Docker found"
        
        if ! command -v docker-compose &> /dev/null; then
            log_error "Docker Compose not found. Please install Docker Compose first."
            echo "Installation guide: https://docs.docker.com/compose/install/"
            exit 1
        fi
        log_success "Docker Compose found"
        
        # Check if user is in docker group
        if ! groups $USER | grep &>/dev/null '\bdocker\b'; then
            log_warning "User $USER is not in docker group. You may need to use sudo."
            log_info "To add user to docker group: sudo usermod -aG docker $USER"
        fi
    fi
    
    # Check Python for standalone mode
    if [[ "$MODE" == "standalone" ]] || [[ "$MODE" == "existing-stack" ]]; then
        if ! command -v python3 &> /dev/null; then
            log_error "Python3 not found. Please install Python 3.8+ first."
            echo "Installation: sudo apt update && sudo apt install python3 python3-pip"
            exit 1
        fi
        log_success "Python3 found"
        
        if ! command -v pip3 &> /dev/null; then
            log_error "pip3 not found. Please install pip3 first."
            echo "Installation: sudo apt install python3-pip"
            exit 1
        fi
        log_success "pip3 found"
    fi
    
    log_success "Prerequisites check completed"
    echo ""
}

setup_environment() {
    log_info "Setting up environment..."
    
    # Create .env file if not exists
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env" ]]; then
            cp ".env" ".env.local"
            log_success "Created .env.local from template"
        else
            log_warning ".env template not found. Please create .env file manually."
        fi
    else
        log_success ".env file already exists"
    fi
    
    # Create logs directory
    mkdir -p logs
    log_success "Created logs directory"
    
    log_success "Environment setup completed"
    echo ""
}

setup_standalone() {
    log_info "Setting up standalone exporter..."
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    pip3 install -r requirements.txt
    
    # Update config if port is different
    if [[ $EXPORTER_PORT -ne 8000 ]]; then
        log_info "Updating exporter port to $EXPORTER_PORT..."
        sed -i "s/port: 8000/port: $EXPORTER_PORT/g" "$CONFIG_FILE"
    fi
    
    log_success "Standalone setup completed"
    echo ""
    echo -e "${YELLOW}To start the exporter:${NC}"
    echo -e "  python3 vmware_aria_exporter_advanced.py --config $CONFIG_FILE"
    echo ""
    echo -e "${GREEN}Exporter will be available at: http://localhost:$EXPORTER_PORT/metrics${NC}"
}

setup_with_stack() {
    log_info "Setting up full stack (Exporter + Prometheus + Grafana)..."
    
    # Create override file if ports are different
    if [[ $EXPORTER_PORT -ne 8000 ]] || [[ $PROMETHEUS_PORT -ne 9090 ]] || [[ $GRAFANA_PORT -ne 3000 ]]; then
        log_info "Creating docker-compose.override.yml for custom ports..."
        
        cat > docker-compose.override.yml << EOF
version: '3.8'
services:
  vmware-aria-exporter:
    ports:
      - "$EXPORTER_PORT:8000"
  prometheus:
    ports:
      - "$PROMETHEUS_PORT:9090"
  grafana:
    ports:
      - "$GRAFANA_PORT:3000"
EOF
        log_success "Created docker-compose.override.yml"
    fi
    
    # Start services
    log_info "Starting Docker services..."
    docker-compose up -d
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 10
    
    log_success "Full stack setup completed"
    echo ""
    echo -e "${YELLOW}Services are available at:${NC}"
    echo -e "  Exporter metrics: ${GREEN}http://localhost:$EXPORTER_PORT/metrics${NC}"
    echo -e "  Prometheus:       ${GREEN}http://localhost:$PROMETHEUS_PORT${NC}"
    echo -e "  Grafana:          ${GREEN}http://localhost:$GRAFANA_PORT${NC} (admin/admin)"
    echo ""
    echo -e "${YELLOW}To check service status:${NC}"
    echo -e "  docker-compose ps"
    echo -e "${YELLOW}To view logs:${NC}"
    echo -e "  docker-compose logs -f"
}

setup_existing_stack() {
    log_info "Configuring for existing Prometheus/Grafana stack..."
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    pip3 install -r requirements.txt
    
    # Update config if port is different
    if [[ $EXPORTER_PORT -ne 8000 ]]; then
        log_info "Updating exporter port to $EXPORTER_PORT..."
        sed -i "s/port: 8000/port: $EXPORTER_PORT/g" "$CONFIG_FILE"
    fi
    
    log_success "Exporter configuration completed"
    echo ""
    echo -e "${YELLOW}Add this job to your Prometheus configuration:${NC}"
    cat << EOF
scrape_configs:
  - job_name: 'vmware-aria-operations'
    static_configs:
      - targets: ['localhost:$EXPORTER_PORT']
    scrape_interval: 60s
    scrape_timeout: 30s
    metrics_path: /metrics
EOF
    
    echo ""
    echo -e "${YELLOW}To start the exporter:${NC}"
    echo -e "  python3 vmware_aria_exporter_advanced.py --config $CONFIG_FILE"
    echo ""
    echo -e "${YELLOW}Don't forget to:${NC}"
    echo -e "  1. Reload Prometheus configuration"
    echo -e "  2. Import Grafana dashboard from grafana/dashboards/vmware-aria-overview.json"
}

install_system_dependencies() {
    log_info "Installing system dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install required packages
    sudo apt install -y curl wget git
    
    if [[ "$MODE" == "standalone" ]] || [[ "$MODE" == "existing-stack" ]]; then
        sudo apt install -y python3 python3-pip python3-venv
    fi
    
    if [[ "$MODE" != "standalone" ]]; then
        # Install Docker if not present
        if ! command -v docker &> /dev/null; then
            log_info "Installing Docker..."
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
            log_success "Docker installed. Please log out and log back in for group changes to take effect."
        fi
        
        # Install Docker Compose if not present
        if ! command -v docker-compose &> /dev/null; then
            log_info "Installing Docker Compose..."
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
            log_success "Docker Compose installed"
        fi
    fi
    
    log_success "System dependencies installed"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -e|--exporter-port)
            EXPORTER_PORT="$2"
            shift 2
            ;;
        -p|--prometheus-port)
            PROMETHEUS_PORT="$2"
            shift 2
            ;;
        -g|--grafana-port)
            GRAFANA_PORT="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        --install-deps)
            install_system_dependencies
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate mode
if [[ ! "$MODE" =~ ^(standalone|with-stack|existing-stack)$ ]]; then
    log_error "Invalid mode: $MODE"
    show_help
    exit 1
fi

# Main execution
main() {
    echo -e "${GREEN}VMware Aria Operations Prometheus Exporter Setup${NC}"
    echo -e "${YELLOW}Mode: $MODE${NC}"
    echo -e "${YELLOW}Exporter Port: $EXPORTER_PORT${NC}"
    if [[ "$MODE" != "standalone" ]]; then
        echo -e "${YELLOW}Prometheus Port: $PROMETHEUS_PORT${NC}"
        echo -e "${YELLOW}Grafana Port: $GRAFANA_PORT${NC}"
    fi
    echo ""
    
    check_prerequisites
    setup_environment
    
    case $MODE in
        "standalone")
            setup_standalone
            ;;
        "with-stack")
            setup_with_stack
            ;;
        "existing-stack")
            setup_existing_stack
            ;;
    esac
    
    log_success "Setup completed successfully!"
}

# Run main function
main