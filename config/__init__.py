"""Configuration management module."""

import os
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables
    config['database'] = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5434)),  # Updated to 5434
        'db': os.getenv('POSTGRES_DB', 'churn_prediction'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    }
    
    config['kafka'] = {
        'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'topics': {
            'customer_service': os.getenv('KAFKA_TOPIC_CUSTOMER_SERVICE', 'customer-service-events'),
            'stb_telemetry': os.getenv('KAFKA_TOPIC_STB_TELEMETRY', 'stb-telemetry-events'),
            'analytics': os.getenv('KAFKA_TOPIC_ANALYTICS', 'web-analytics-events'),
            'billing': os.getenv('KAFKA_TOPIC_BILLING', 'billing-events'),
        }
    }
    
    config['redis'] = {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', 6379)),
        'password': os.getenv('REDIS_PASSWORD', ''),
    }
    
    config['mlflow'] = {
        'tracking_uri': os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5001'),  # Updated to 5001
        'experiment_name': os.getenv('MLFLOW_EXPERIMENT_NAME', 'churn_prediction'),
    }
    
    return config


# Global config instance
CONFIG = load_config()
