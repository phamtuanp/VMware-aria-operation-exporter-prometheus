# VMware Aria Operations Prometheus Exporter

Một Prometheus exporter để thu thập metrics từ VMware Aria Operations và xuất chúng ở định dạng Prometheus.

## Tính năng

- Thu thập metrics từ VMware Aria Operations API
- Hỗ trợ nhiều loại resource (VirtualMachine, HostSystem, Datastore, etc.)
- Xuất metrics ở định dạng Prometheus
- Cấu hình linh hoạt qua file YAML
- Hỗ trợ Docker và Docker Compose
- Tích hợp sẵn với Prometheus và Grafana
- Retry logic và error handling
- Health checks và monitoring

## Quick Start

### Sử dụng Setup Script (Khuyến nghị)

Chúng tôi cung cấp script tự động cho cả Windows và Linux/Ubuntu:

#### Windows (PowerShell)

```powershell
# Trường hợp 1: Chưa có Prometheus/Grafana (cài đặt full stack)
.\setup.ps1 -Mode with-stack

# Trường hợp 2: Đã có Prometheus/Grafana
.\setup.ps1 -Mode existing-stack

# Trường hợp 3: Chỉ chạy exporter
.\setup.ps1 -Mode standalone

# Trường hợp 4: Thay đổi ports
.\setup.ps1 -Mode with-stack -ExporterPort 8001 -PrometheusPort 9091 -GrafanaPort 3001

# Xem help
.\setup.ps1 -Help
```

#### Linux/Ubuntu (Bash)

```bash
# Cấp quyền thực thi cho script
chmod +x setup.sh

# Trường hợp 1: Chưa có Prometheus/Grafana (cài đặt full stack)
./setup.sh -m with-stack

# Trường hợp 2: Đã có Prometheus/Grafana
./setup.sh -m existing-stack

# Trường hợp 3: Chỉ chạy exporter
./setup.sh -m standalone

# Trường hợp 4: Thay đổi ports
./setup.sh -m with-stack -e 8001 -p 9091 -g 3001

# Cài đặt dependencies hệ thống (nếu cần)
./setup.sh --install-deps

# Xem help
./setup.sh -h
```

## Cài đặt và Cấu hình Chi tiết

### Yêu cầu

#### Chung
- Python 3.8+
- VMware Aria Operations 8.x+
- Docker và Docker Compose (cho deployment với container)

#### Theo nền tảng

**Windows:**
- PowerShell 5.1+ (thường có sẵn)
- Windows 10/11 hoặc Windows Server 2016+

**Linux/Ubuntu:**
- Bash shell (có sẵn)
- Ubuntu 18.04+ hoặc các distro Linux tương đương
- curl, wget, git (có thể cài tự động bằng script)

#### Dependencies tùy chọn
- Git (để clone repository)
- Make (để sử dụng Makefile)
- Virtual environment tools (python3-venv, virtualenv)

### Trường hợp 1: Đã có Prometheus và Grafana

Nếu bạn đã có Prometheus và Grafana đang chạy:

1. **Cài đặt exporter**:
```bash
git clone <repository-url>
cd vmware-aria-operation-exp
pip install -r requirements.txt
```

2. **Cấu hình exporter**:
```bash
cp .env .env.local
# Chỉnh sửa file .env.local với thông tin VMware Aria Operations
```

3. **Chỉnh sửa config.yaml** (nếu cần thay đổi port):
```yaml
exporter:
  port: 8000  # Thay đổi port nếu bị conflict
  interval: 60
  log_level: "INFO"
```

4. **Chạy exporter**:
```bash
python vmware_aria_exporter_advanced.py --config config.yaml
```

5. **Thêm job vào Prometheus config** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'vmware-aria-operations'
    static_configs:
      - targets: ['localhost:8000']  # Thay đổi port nếu cần
    scrape_interval: 60s
    scrape_timeout: 30s
    metrics_path: /metrics
```

6. **Reload Prometheus config**:
```bash
curl -X POST http://localhost:9090/-/reload
```

7. **Import Grafana dashboard**:
   - Vào Grafana UI
   - Import file `grafana/dashboards/vmware-aria-overview.json`

### Trường hợp 2: Chưa có Prometheus và Grafana

Nếu bạn chưa có Prometheus và Grafana:

1. **Cài đặt với Docker Compose** (khuyến nghị):
```bash
git clone <repository-url>
cd vmware-aria-operation-exp
```

2. **Cấu hình**:
```bash
cp .env .env.local
# Chỉnh sửa file .env.local với thông tin của bạn
```

3. **Chạy toàn bộ stack**:
```bash
docker-compose up -d
```

Điều này sẽ khởi động:
- VMware Aria Exporter (port 8000)
- Prometheus (port 9090)
- Grafana (port 3000)

4. **Truy cập các dịch vụ**:
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090
   - Exporter metrics: http://localhost:8000/metrics

### Trường hợp 3: Cần thay đổi Port

Nếu các port mặc định bị conflict:

#### 3.1. Thay đổi port Exporter

**Cách 1: Thông qua config.yaml**
```yaml
exporter:
  port: 8001  # Port mới
  interval: 60
  log_level: "INFO"
```

**Cách 2: Thông qua biến môi trường**
```bash
export EXPORTER_PORT=8001
python vmware_aria_exporter_advanced.py --config config.yaml
```

**Cách 3: Với Docker Compose**
```yaml
# Trong docker-compose.yml
services:
  vmware-aria-exporter:
    ports:
      - "8001:8000"  # Host:Container
```

#### 3.2. Thay đổi port Prometheus

**Với Docker Compose:**
```yaml
# Trong docker-compose.yml
services:
  prometheus:
    ports:
      - "9091:9090"  # Port mới: 9091
```

**Cập nhật Grafana datasource:**
```yaml
# Trong grafana/provisioning/datasources/prometheus.yml
datasources:
  - name: Prometheus
    url: http://prometheus:9090  # Port container không đổi
```

#### 3.3. Thay đổi port Grafana

**Với Docker Compose:**
```yaml
# Trong docker-compose.yml
services:
  grafana:
    ports:
      - "3001:3000"  # Port mới: 3001
```

#### 3.4. Thay đổi tất cả ports

**File docker-compose.override.yml:**
```yaml
version: '3.8'
services:
  vmware-aria-exporter:
    ports:
      - "8001:8000"
  prometheus:
    ports:
      - "9091:9090"
  grafana:
    ports:
      - "3001:3000"
```

**Chạy với override:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

### Cài đặt từ source (Manual)

#### Windows

1. Clone repository:
```powershell
git clone <repository-url>
cd vmware-aria-operation-exp
```

2. Cài đặt dependencies:
```powershell
pip install -r requirements.txt
```

3. Cấu hình:
```powershell
cp .env .env.local
# Chỉnh sửa file .env.local với thông tin của bạn
```

4. Chỉnh sửa file `config.yaml` theo môi trường của bạn

5. Chạy exporter:
```powershell
python vmware_aria_exporter_advanced.py --config config.yaml
```

#### Linux/Ubuntu

1. Cài đặt dependencies hệ thống (nếu cần):
```bash
sudo apt update
sudo apt install -y python3 python3-pip git curl wget
```

2. Clone repository:
```bash
git clone <repository-url>
cd vmware-aria-operation-exp
```

3. Cài đặt Python dependencies:
```bash
pip3 install -r requirements.txt
# Hoặc sử dụng Makefile
make -f Makefile.linux install
```

4. Cấu hình:
```bash
cp .env .env.local
# Chỉnh sửa file .env.local với thông tin của bạn
vim .env.local  # hoặc nano, gedit
```

5. Chỉnh sửa file `config.yaml` theo môi trường của bạn

6. Chạy exporter:
```bash
python3 vmware_aria_exporter_advanced.py --config config.yaml
# Hoặc sử dụng Makefile
make -f Makefile.linux run
```

#### Sử dụng Virtual Environment (Khuyến nghị)

**Windows:**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux/Ubuntu:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Cấu hình

### File config.yaml

```yaml
vmware_aria:
  host: "your-aria-host.example.com"
  username: "your-username"
  password: "your-password"
  verify_ssl: false

exporter:
  port: 8000
  interval: 60
  log_level: "INFO"

metrics:
  resource_types:
    - "VirtualMachine"
    - "HostSystem"
    - "Datastore"
  max_stats_per_resource: 50
  stats_time_range_minutes: 60
  timeout_seconds: 30
```

### Biến môi trường

| Biến | Mô tả | Mặc định |
|------|-------|----------|
| `VMWARE_ARIA_HOST` | Hostname của VMware Aria Operations | - |
| `VMWARE_ARIA_USERNAME` | Username để đăng nhập | - |
| `VMWARE_ARIA_PASSWORD` | Password để đăng nhập | - |
| `VMWARE_ARIA_VERIFY_SSL` | Xác thực SSL certificate | `false` |
| `EXPORTER_PORT` | Port của exporter | `8000` |
| `EXPORTER_LOG_LEVEL` | Log level | `INFO` |

## API Endpoints

- `/metrics` - Prometheus metrics endpoint
- `/health` - Health check endpoint
- `/` - Exporter information

## Metrics

Exporter thu thập các loại metrics sau:

### System Metrics
- `vmware_aria_up` - Trạng thái kết nối đến VMware Aria Operations
- `vmware_aria_scrape_duration_seconds` - Thời gian scrape metrics
- `vmware_aria_scrape_errors_total` - Số lỗi khi scrape

### Resource Metrics
- `vmware_aria_resources_total` - Tổng số resources theo loại
- `vmware_aria_resource_health` - Trạng thái health của resource
- `vmware_aria_resource_stats` - Performance stats của resource

### Alert Metrics
- `vmware_aria_alerts_total` - Tổng số alerts theo mức độ
- `vmware_aria_alert_info` - Thông tin chi tiết về alerts

## Monitoring và Alerting

### Prometheus Queries

```promql
# Kiểm tra exporter có hoạt động không
vmware_aria_up

# Số lượng VMs
vmware_aria_resources_total{resource_type="VirtualMachine"}

# CPU usage của VMs
vmware_aria_resource_stats{stat_name="cpu|usage_average"}

# Memory usage của VMs
vmware_aria_resource_stats{stat_name="mem|usage_average"}
```

### Grafana Dashboards

Sample dashboards có thể được tìm thấy trong thư mục `grafana/dashboards/`.

## Troubleshooting

### Lỗi thường gặp

1. **Connection refused**
   - Kiểm tra hostname và port của VMware Aria Operations
   - Kiểm tra network connectivity

2. **Authentication failed**
   - Kiểm tra username và password
   - Kiểm tra quyền của user trong VMware Aria Operations

3. **SSL certificate errors**
   - Đặt `verify_ssl: false` trong config nếu sử dụng self-signed certificate

4. **Timeout errors**
   - Tăng `timeout_seconds` trong config
   - Giảm `max_stats_per_resource` để giảm tải

### Logs

Exporter ghi logs chi tiết về hoạt động. Để tăng log level:

```yaml
exporter:
  log_level: "DEBUG"
```

### Health Checks

Kiểm tra health của exporter:

```bash
curl http://localhost:8000/health
```

## Development

### Chạy tests

```bash
python -m pytest tests/
```

### Code formatting

```bash
black .
flake8 .
```

## Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## License

MIT License - xem file LICENSE để biết thêm chi tiết.

## Support

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub repository.