#!/usr/bin/env python3
"""
VMware Aria Operations Prometheus Exporter

Exporter này lấy metrics từ VMware Aria Operations và expose chúng cho Prometheus.
Dựa trên API documentation của VMware Aria Operations.
"""

import time
import requests
import json
import logging
from prometheus_client import start_http_server, Gauge, Counter, Info
from prometheus_client.core import CollectorRegistry, REGISTRY
import urllib3
from typing import Dict, List, Any
import argparse
import os
from datetime import datetime, timedelta

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VMwareAriaExporter:
    """
    VMware Aria Operations Prometheus Exporter
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 8000, verify_ssl: bool = False):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{host}/suite-api"
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.token = None
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.setup_metrics()
        
        # Authentication
        self.authenticate()
    
    def setup_metrics(self):
        """Setup Prometheus metrics"""
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
            ['resource_type', 'adapter_kind'],
            registry=self.registry
        )
        
        # Alert metrics
        self.alert_count = Gauge(
            'vmware_aria_alerts_total',
            'Total number of alerts by criticality',
            ['criticality', 'status'],
            registry=self.registry
        )
        
        # Performance metrics
        self.performance_metric = Gauge(
            'vmware_aria_performance_metric',
            'Performance metrics from resources',
            ['resource_id', 'resource_name', 'metric_name', 'unit'],
            registry=self.registry
        )
        
        # Collection metrics
        self.collection_duration = Gauge(
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
    
    def authenticate(self):
        """Authenticate with VMware Aria Operations"""
        auth_url = f"{self.base_url}/api/auth/token/acquire"
        auth_data = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = self.session.post(auth_url, json=auth_data)
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
            raise
    
    def get_resources(self) -> List[Dict]:
        """Get all resources from VMware Aria Operations"""
        start_time = time.time()
        resources = []
        
        try:
            url = f"{self.base_url}/api/resources"
            params = {
                'pageSize': 1000,
                'page': 0
            }
            
            while True:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
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
            self.collection_errors.labels(endpoint='resources', error_type=type(e).__name__).inc()
        
        finally:
            duration = time.time() - start_time
            self.collection_duration.labels(endpoint='resources').set(duration)
        
        return resources
    
    def get_alerts(self) -> List[Dict]:
        """Get alerts from VMware Aria Operations"""
        start_time = time.time()
        alerts = []
        
        try:
            url = f"{self.base_url}/api/alerts"
            params = {
                'pageSize': 1000,
                'page': 0
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            alerts = data.get('alerts', [])
            
            logger.info(f"Retrieved {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            self.collection_errors.labels(endpoint='alerts', error_type=type(e).__name__).inc()
        
        finally:
            duration = time.time() - start_time
            self.collection_duration.labels(endpoint='alerts').set(duration)
        
        return alerts
    
    def get_resource_stats(self, resource_id: str) -> List[Dict]:
        """Get statistics for a specific resource"""
        try:
            url = f"{self.base_url}/api/resources/{resource_id}/stats"
            
            # Get stats for the last hour
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            params = {
                'begin': int(start_time.timestamp() * 1000),
                'end': int(end_time.timestamp() * 1000),
                'rollUpType': 'AVG',
                'intervalType': 'MINUTES',
                'intervalQuantifier': 5
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('values', [])
            
        except Exception as e:
            logger.debug(f"Error getting stats for resource {resource_id}: {e}")
            return []
    
    def get_super_metrics(self) -> List[Dict]:
        """Get super metrics definitions"""
        start_time = time.time()
        super_metrics = []
        
        try:
            url = f"{self.base_url}/api/supermetrics"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            super_metrics = data.get('super-metrics', [])
            
            logger.info(f"Retrieved {len(super_metrics)} super metrics")
            
        except Exception as e:
            logger.error(f"Error getting super metrics: {e}")
            self.collection_errors.labels(endpoint='supermetrics', error_type=type(e).__name__).inc()
        
        finally:
            duration = time.time() - start_time
            self.collection_duration.labels(endpoint='supermetrics').set(duration)
        
        return super_metrics
    
    def update_metrics(self):
        """Update all Prometheus metrics"""
        logger.info("Starting metrics collection...")
        
        # Update system info
        self.aria_info.info({
            'host': self.host,
            'version': 'unknown',  # Could be retrieved from /api/versions
            'exporter_version': '1.0.0'
        })
        
        # Get and process resources
        resources = self.get_resources()
        resource_counts = {}
        
        for resource in resources:
            resource_kind = resource.get('resourceKey', {}).get('resourceKindKey', 'unknown')
            adapter_kind = resource.get('resourceKey', {}).get('adapterKindKey', 'unknown')
            
            key = (resource_kind, adapter_kind)
            resource_counts[key] = resource_counts.get(key, 0) + 1
            
            # Get performance stats for important resources (limit to avoid overload)
            if resource_kind in ['VirtualMachine', 'HostSystem', 'ClusterComputeResource']:
                resource_id = resource.get('identifier')
                resource_name = resource.get('resourceKey', {}).get('name', 'unknown')
                
                if resource_id:
                    stats = self.get_resource_stats(resource_id)
                    for stat in stats[:10]:  # Limit to first 10 stats
                        stat_key = stat.get('statKey', {})
                        metric_name = stat_key.get('key', 'unknown')
                        unit = stat_key.get('unit', '')
                        
                        values = stat.get('data', [])
                        if values:
                            # Use the latest value
                            latest_value = values[-1]
                            if isinstance(latest_value, (int, float)):
                                self.performance_metric.labels(
                                    resource_id=resource_id,
                                    resource_name=resource_name,
                                    metric_name=metric_name,
                                    unit=unit
                                ).set(latest_value)
        
        # Update resource count metrics
        for (resource_kind, adapter_kind), count in resource_counts.items():
            self.resource_count.labels(
                resource_type=resource_kind,
                adapter_kind=adapter_kind
            ).set(count)
        
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
            self.alert_count.labels(
                criticality=criticality,
                status=status
            ).set(count)
        
        logger.info("Metrics collection completed")
    
    def run(self, interval: int = 300):
        """Run the exporter"""
        logger.info(f"Starting VMware Aria Operations exporter on port {self.port}")
        logger.info(f"Collection interval: {interval} seconds")
        
        # Start Prometheus HTTP server
        start_http_server(self.port, registry=self.registry)
        
        while True:
            try:
                self.update_metrics()
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Exporter stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying

def main():
    parser = argparse.ArgumentParser(description='VMware Aria Operations Prometheus Exporter')
    parser.add_argument('--host', required=True, help='VMware Aria Operations host')
    parser.add_argument('--username', required=True, help='Username for authentication')
    parser.add_argument('--password', help='Password for authentication')
    parser.add_argument('--port', type=int, default=8000, help='Port for Prometheus metrics (default: 8000)')
    parser.add_argument('--interval', type=int, default=300, help='Collection interval in seconds (default: 300)')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificates')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Get password from environment if not provided
    password = args.password or os.getenv('VMWARE_ARIA_PASSWORD')
    if not password:
        raise ValueError("Password must be provided via --password or VMWARE_ARIA_PASSWORD environment variable")
    
    # Create and run exporter
    exporter = VMwareAriaExporter(
        host=args.host,
        username=args.username,
        password=password,
        port=args.port,
        verify_ssl=args.verify_ssl
    )
    
    exporter.run(interval=args.interval)

if __name__ == '__main__':
    main()