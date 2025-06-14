# VMware Aria Operations Prometheus Exporter Makefile

.PHONY: help install run test clean docker-build docker-run docker-stop logs

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install Python dependencies"
	@echo "  run         - Run the exporter locally"
	@echo "  test        - Run tests"
	@echo "  clean       - Clean up temporary files"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run with Docker Compose"
	@echo "  docker-stop - Stop Docker Compose services"
	@echo "  logs        - Show Docker Compose logs"
	@echo "  format      - Format code with black"
	@echo "  lint        - Run code linting"

# Install dependencies
install:
	pip install -r requirements.txt

# Run the exporter locally
run:
	python vmware_aria_exporter_advanced.py --config config.yaml

# Run tests
test:
	python -m pytest tests/ -v

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

# Docker targets
docker-build:
	docker build -t vmware-aria-exporter .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

logs:
	docker-compose logs -f

# Code formatting and linting
format:
	black .
	lint:
	flake8 .
	mypy .

# Development setup
dev-setup: install
	pip install black flake8 mypy pytest

# Check configuration
check-config:
	python -c "import yaml; yaml.safe_load(open('config.yaml'))"
	echo "Configuration file is valid"

# Health check
health:
	curl -f http://localhost:8000/health || echo "Exporter is not running"

# Show metrics
metrics:
	curl -s http://localhost:8000/metrics | head -20