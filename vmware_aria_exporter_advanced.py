#!/usr/bin/env python3
"""
VMware Aria Operations Prometheus Exporter - Advanced Version

Exporter nâng cao với hỗ trợ cấu hình YAML, retry logic, và nhiều tính năng khác.
"""

import time
import requests
import json
import logging
import yaml
import re
from prometheus_client import start_http_server, Gauge, Counter, Info, Histogram
from prometheus_client.core import CollectorRegistry, REGISTRY
import urllib3
from typing import Dict, List, Any, Optional
import argparse
import os
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VMwareAriaExporterAdvanced:
    """
    VMware Aria Operations Prometheus Exporter - Advanced Version
    """
    
    def __init__(self, config_file: str = None, **kwargs):
        # Load configuration
        self.config = self.load_config(config_file, **kwargs)
        
        # Extract configuration values
        aria_config = self.config['vmware_aria']
        self.host = aria_config['host']
        self.username = aria_config['username']
        self.password = aria_config.get('password') or os.getenv('VMWARE_ARIA_PASSWORD')
        self.verify_ssl = aria_config.get('verify_ssl', False)
        
        exporter_config = self.config['exporter']
        self.port = exporter_config.get('port', 8000)
        self.interval = exporter_config.get('interval', 300)
        self.log_level = exporter_config.get('log_level', 'INFO')
        
        # Set log level
        logging.getLogger().setLevel(getattr(logging, self.log_level))
        
        if not self.password:
            raise ValueError("Password must be provided in config or VMWARE_ARIA_PASSWORD environment variable")
        
        self.base_url = f"https://{self.host}/suite-api"
        self.token = None
        
        # Setup session with retry strategy
        self.session = self.create_session()
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.setup_metrics()
        
        # Authentication
        self.authenticate()
    
    def load_config(self, config_file: str = None, **kwargs) -> Dict:
        """Load configuration from YAML file or use defaults"""
        default_config = {
            'vmware_aria': {
                'host': kwargs.get('host', '192.168.31.31'),
                'username': kwargs.get('username', 'admin'),
                'password': kwargs.get('password', ''),
                'verify_ssl': kwargs.get('verify_ssl', False)
            },
            'exporter': {
                'port': kwargs.get('port', 8000),
                'interval': kwargs.get('interval', 300),
                'log_level': kwargs.get('log_level', 'INFO')
            },
            'metrics': {
                'detailed_resource_types': ['VirtualMachine', 'HostSystem', 'ClusterComputeResource'],
                'max_stats_per_resource': 10,
                'stats_time_range_hours': 1,
                'timeouts': {
                    'resources': 60,
                    'alerts': 30,
                    'stats': 45,
                    'supermetrics': 30
                }
            },
            'labels': {
                'static': {},
                'resource_patterns': {}
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    # Merge with defaults
                    self.deep_merge(default_config, file_config)
                    logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")
                logger.info("Using default configuration")
        
        return default_config
    
    def deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self.deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        session.verify = self.verify_ssl
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def setup_metrics(self):
        """Setup Prometheus metrics"""
        static_labels = self.config['labels'].get('static', {})
        
        # System info
        self.aria_info = Info(
            'vmware_aria_operations_info',
            'VMware Aria Operations system information',
            registry=self.registry
        )
        
        # Resource metrics
        self.resource_count = Gauge(
            'vmware_aria_resources_total',
            'Total number of resources by type',
            ['resource_type', 'adapter_kind'] + list(static_labels.keys()),
            registry=self.registry
        )
        
        # Alert metrics
        self.alert_count = Gauge(
            'vmware_aria_alerts_total',
            'Total number of alerts by criticality',
            ['criticality', 'status'] + list(static_labels.keys()),
            registry=self.registry
        )
        
        # Performance metrics
        self.performance_metric = Gauge(
            'vmware_aria_performance_metric',
            'Performance metrics from resources',
            ['resource_id', 'resource_name', 'resource_type', 'metric_name', 'unit'] + list(static_labels.keys()),
            registry=self.registry
        )
        
        # Collection metrics
        self.collection_duration = Histogram(
            'vmware_aria_collection_duration_seconds',
            'Time spent collecting metrics',
            ['endpoint'],
            registry=self.registry
        )
        
        self.collection_errors = Counter(
            'vmware_aria_collection_errors_total',
            'Total number of collection errors',
            ['endpoint', 'error_type'],
            registry=self.registry
        )
        
        # API response metrics
        self.api_requests_total = Counter(
            'vmware_aria_api_requests_total',
            'Total number of API requests',
            ['endpoint', 'method', 'status_code'],
            registry=self.registry
        )
        
        self.api_request_duration = Histogram(
            'vmware_aria_api_request_duration_seconds',
            'API request duration',
            ['endpoint', 'method'],
            registry=self.registry
        )
    
    def authenticate(self):
        """Authenticate with VMware Aria Operations"""
        auth_url = f"{self.base_url}/api/auth/token/acquire"
        auth_data = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            start_time = time.time()
            response = self.session.post(auth_url, json=auth_data, timeout=30)
            duration = time.time() - start_time
            
            self.api_requests_total.labels(
                endpoint='auth',
                method='POST',
                status_code=response.status_code
            ).inc()
            
            self.api_request_duration.labels(
                endpoint='auth',
                method='POST'
            ).observe(duration)
            
            response.raise_for_status()
            
            auth_response = response.json()
            self.token = auth_response.get('token')
            
            if self.token:
                self.session.headers.update({
                    'Authorization': f'vRealizeOpsToken {self.token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                })
                logger.info("Successfully authenticated with VMware Aria Operations")
            else:
                raise Exception("No token received from authentication")
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.collection_errors.labels(endpoint='auth', error_type=type(e).__name__).inc()
            raise
    
    def make_api_request(self, endpoint: str, method: str = 'GET', **kwargs) -> Optional[Dict]:
        """Make API request with metrics tracking"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = self.session.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = self.session.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            duration = time.time() - start_time
            
            self.api_requests_total.labels(
                endpoint=endpoint,
                method=method.upper(),
                status_code=response.status_code
            ).inc()
            
            self.api_request_duration.labels(
                endpoint=endpoint,
                method=method.upper()
            ).observe(duration)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            self.collection_errors.labels(
                endpoint=endpoint.split('/')[2] if len(endpoint.split('/')) > 2 else 'unknown',
                error_type=type(e).__name__
            ).inc()
            return None
    
    def get_resources(self) -> List[Dict]:
        """Get all resources from VMware Aria Operations"""
        with self.collection_duration.labels(endpoint='resources').time():
            resources = []
            timeout = self.config['metrics']['timeouts']['resources']
            
            try:
                params = {
                    'pageSize': 1000,
                    'page': 0
                }
                
                while True:
                    data = self.make_api_request('/api/resources', params=params, timeout=timeout)
                    if not data:
                        break
                    
                    page_resources = data.get('resourceList', [])
                    resources.extend(page_resources)
                    
                    # Check if there are more pages
                    page_info = data.get('pageInfo', {})
                    total_count = page_info.get('totalCount', 0)
                    current_page = page_info.get('page', 0)
                    page_size = page_info.get('pageSize', 1000)
                    
                    if (current_page + 1) * page_size >= total_count:
                        break
                        
                    params['page'] += 1
                
                logger.info(f"Retrieved {len(resources)} resources")
                
            except Exception as e:
                logger.error(f"Error getting resources: {e}")
            
            return resources
    
    def get_alerts(self) -> List[Dict]:
        """Get alerts from VMware Aria Operations"""
        with self.collection_duration.labels(endpoint='alerts').time():
            alerts = []
            timeout = self.config['metrics']['timeouts']['alerts']
            
            try:
                params = {
                    'pageSize': 1000,
                    'page': 0
                }
                
                data = self.make_api_request('/api/alerts', params=params, timeout=timeout)
                if data:
                    alerts = data.get('alerts', [])
                    logger.info(f"Retrieved {len(alerts)} alerts")
                
            except Exception as e:
                logger.error(f"Error getting alerts: {e}")
            
            return alerts
    
    def get_resource_stats(self, resource_id: str) -> List[Dict]:
        """Get statistics for a specific resource"""
        try:
            timeout = self.config['metrics']['timeouts']['stats']
            hours = self.config['metrics']['stats_time_range_hours']
            
            # Get stats for the specified time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            params = {
                'begin': int(start_time.timestamp() * 1000),
                'end': int(end_time.timestamp() * 1000),
                'rollUpType': 'AVG',
                'intervalType': 'MINUTES',
                'intervalQuantifier': 5
            }
            
            data = self.make_api_request(f'/api/resources/{resource_id}/stats', params=params, timeout=timeout)
            if data:
                return data.get('values', [])
            
        except Exception as e:
            logger.debug(f"Error getting stats for resource {resource_id}: {e}")
        
        return []
    
    def extract_labels_from_resource(self, resource: Dict) -> Dict[str, str]:
        """Extract additional labels from resource using patterns"""
        labels = {}
        patterns = self.config['labels'].get('resource_patterns', {})
        
        resource_name = resource.get('resourceKey', {}).get('name', '')
        
        for label_name, pattern in patterns.items():
            try:
                match = re.search(pattern, resource_name)
                if match:
                    labels[label_name] = match.group(1)
            except Exception as e:
                logger.debug(f"Error applying pattern {pattern} to {resource_name}: {e}")
        
        return labels
    
    def update_metrics(self):
        """Update all Prometheus metrics"""
        logger.info("Starting metrics collection...")
        
        static_labels = self.config['labels'].get('static', {})
        
        # Update system info
        info_labels = {
            'host': self.host,
            'version': 'unknown',
            'exporter_version': '1.0.0'
        }
        info_labels.update(static_labels)
        self.aria_info.info(info_labels)
        
        # Get and process resources
        resources = self.get_resources()
        resource_counts = {}
        detailed_types = self.config['metrics']['detailed_resource_types']
        max_stats = self.config['metrics']['max_stats_per_resource']
        
        for resource in resources:
            resource_kind = resource.get('resourceKey', {}).get('resourceKindKey', 'unknown')
            adapter_kind = resource.get('resourceKey', {}).get('adapterKindKey', 'unknown')
            
            # Count resources
            key = (resource_kind, adapter_kind)
            resource_counts[key] = resource_counts.get(key, 0) + 1
            
            # Get performance stats for detailed resource types
            if resource_kind in detailed_types:
                resource_id = resource.get('identifier')
                resource_name = resource.get('resourceKey', {}).get('name', 'unknown')
                
                if resource_id:
                    stats = self.get_resource_stats(resource_id)
                    
                    # Extract additional labels
                    extra_labels = self.extract_labels_from_resource(resource)
                    
                    for stat in stats[:max_stats]:
                        stat_key = stat.get('statKey', {})
                        metric_name = stat_key.get('key', 'unknown')
                        unit = stat_key.get('unit', '')
                        
                        values = stat.get('data', [])
                        if values:
                            # Use the latest value
                            latest_value = values[-1]
                            if isinstance(latest_value, (int, float)):
                                labels = {
                                    'resource_id': resource_id,
                                    'resource_name': resource_name,
                                    'resource_type': resource_kind,
                                    'metric_name': metric_name,
                                    'unit': unit
                                }
                                labels.update(static_labels)
                                labels.update(extra_labels)
                                
                                self.performance_metric.labels(**labels).set(latest_value)
        
        # Update resource count metrics
        for (resource_kind, adapter_kind), count in resource_counts.items():
            labels = {
                'resource_type': resource_kind,
                'adapter_kind': adapter_kind
            }
            labels.update(static_labels)
            self.resource_count.labels(**labels).set(count)
        
        # Get and process alerts
        alerts = self.get_alerts()
        alert_counts = {}
        
        for alert in alerts:
            criticality = alert.get('alertLevel', 'unknown')
            status = alert.get('status', 'unknown')
            
            key = (criticality, status)
            alert_counts[key] = alert_counts.get(key, 0) + 1
        
        # Update alert count metrics
        for (criticality, status), count in alert_counts.items():
            labels = {
                'criticality': criticality,
                'status': status
            }
            labels.update(static_labels)
            self.alert_count.labels(**labels).set(count)
        
        logger.info("Metrics collection completed")
    
    def run(self):
        """Run the exporter"""
        logger.info(f"Starting VMware Aria Operations exporter on port {self.port}")
        logger.info(f"Collection interval: {self.interval} seconds")
        logger.info(f"Target host: {self.host}")
        
        # Start Prometheus HTTP server
        start_http_server(self.port, registry=self.registry)
        
        while True:
            try:
                self.update_metrics()
                time.sleep(self.interval)
            except KeyboardInterrupt:
                logger.info("Exporter stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying

def main():
    parser = argparse.ArgumentParser(description='VMware Aria Operations Prometheus Exporter - Advanced')
    parser.add_argument('--config', help='Path to YAML configuration file')
    parser.add_argument('--host', help='VMware Aria Operations host')
    parser.add_argument('--username', help='Username for authentication')
    parser.add_argument('--password', help='Password for authentication')
    parser.add_argument('--port', type=int, help='Port for Prometheus metrics')
    parser.add_argument('--interval', type=int, help='Collection interval in seconds')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificates')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Log level')
    
    args = parser.parse_args()
    
    # Filter out None values
    kwargs = {k: v for k, v in vars(args).items() if v is not None and k != 'config'}
    
    # Create and run exporter
    exporter = VMwareAriaExporterAdvanced(config_file=args.config, **kwargs)
    exporter.run()

if __name__ == '__main__':
    main()