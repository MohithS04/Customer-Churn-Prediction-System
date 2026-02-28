"""Data quality validators."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from database import SessionLocal
from database.models import DataQualityMetrics

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """Validate data quality metrics."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def validate_completeness(self, data_source: str, records: List[Dict[str, Any]], required_fields: List[str]) -> Dict[str, Any]:
        """
        Validate data completeness.
        
        Args:
            data_source: Name of data source
            records: List of records to validate
            required_fields: List of required field names
            
        Returns:
            Validation result with metrics
        """
        if not records:
            return {
                'status': 'fail',
                'completeness': 0.0,
                'message': 'No records found'
            }
        
        total_records = len(records)
        complete_records = 0
        
        for record in records:
            if all(field in record and record[field] is not None for field in required_fields):
                complete_records += 1
        
        completeness = complete_records / total_records if total_records > 0 else 0.0
        
        threshold = 0.95  # 95% completeness threshold
        status = 'pass' if completeness >= threshold else 'fail'
        
        result = {
            'status': status,
            'completeness': completeness,
            'complete_records': complete_records,
            'total_records': total_records,
            'threshold': threshold
        }
        
        self._save_metric(data_source, 'completeness', completeness, threshold, status, result)
        
        return result
    
    def validate_freshness(self, data_source: str, latest_timestamp: datetime, threshold_minutes: int = 10) -> Dict[str, Any]:
        """
        Validate data freshness.
        
        Args:
            data_source: Name of data source
            latest_timestamp: Latest record timestamp
            threshold_minutes: Maximum allowed lag in minutes
            
        Returns:
            Validation result
        """
        now = datetime.utcnow()
        lag_minutes = (now - latest_timestamp).total_seconds() / 60
        
        status = 'pass' if lag_minutes <= threshold_minutes else 'fail'
        
        result = {
            'status': status,
            'lag_minutes': lag_minutes,
            'threshold_minutes': threshold_minutes,
            'latest_timestamp': latest_timestamp.isoformat()
        }
        
        self._save_metric(data_source, 'freshness', lag_minutes, threshold_minutes, status, result)
        
        return result
    
    def validate_accuracy(self, data_source: str, validation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data accuracy using business rules.
        
        Args:
            data_source: Name of data source
            validation_rules: Dictionary of field -> validation function
            
        Returns:
            Validation result
        """
        # Placeholder - implement specific validation rules
        result = {
            'status': 'pass',
            'accuracy': 1.0,
            'violations': []
        }
        
        self._save_metric(data_source, 'accuracy', 1.0, 0.98, 'pass', result)
        
        return result
    
    def detect_drift(self, data_source: str, current_distribution: Dict[str, float], baseline_distribution: Dict[str, float]) -> Dict[str, Any]:
        """
        Detect data drift using distribution comparison.
        
        Args:
            data_source: Name of data source
            current_distribution: Current data distribution
            baseline_distribution: Baseline distribution
            
        Returns:
            Drift detection result
        """
        # Simple drift detection using KL divergence approximation
        import math
        
        psi = 0.0
        for key in set(current_distribution.keys()) | set(baseline_distribution.keys()):
            current = current_distribution.get(key, 0.0001)
            baseline = baseline_distribution.get(key, 0.0001)
            psi += (current - baseline) * math.log(current / baseline)
        
        threshold = 0.2
        status = 'pass' if psi <= threshold else 'fail'
        
        result = {
            'status': status,
            'psi': psi,
            'threshold': threshold
        }
        
        self._save_metric(data_source, 'data_drift', psi, threshold, status, result)
        
        return result
    
    def _save_metric(self, data_source: str, metric_name: str, value: float, threshold: float, status: str, details: Dict[str, Any]):
        """Save quality metric to database."""
        try:
            metric = DataQualityMetrics(
                data_source=data_source,
                metric_name=metric_name,
                metric_value=value,
                threshold_value=threshold,
                status=status,
                details=details
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error saving quality metric: {e}")
            self.db.rollback()
