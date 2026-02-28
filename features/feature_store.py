"""Feature store for managing and serving features."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import redis
from sqlalchemy import func, and_
from database import SessionLocal
from database.models import (
    Customer,
    CustomerServiceInteraction,
    STBTelemetry,
    WebAnalyticsEvent,
    BillingEvent
)
from config import CONFIG

logger = logging.getLogger(__name__)


class FeatureStore:
    """Feature store for online and offline feature serving."""
    
    def __init__(self):
        redis_config = CONFIG['redis']
        self.redis_client = redis.Redis(
            host=redis_config['host'],
            port=redis_config['port'],
            password=redis_config.get('password') or None,
            decode_responses=True
        )
        self.db = SessionLocal()
        self.ttl_seconds = CONFIG['feature_store']['online_store']['ttl_seconds']
    
    def get_customer_features(self, customer_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get customer features (online store with Redis cache).
        
        Args:
            customer_id: Customer identifier
            use_cache: Whether to use Redis cache
            
        Returns:
            Dictionary of feature names to values
        """
        # Try cache first
        if use_cache:
            cached = self.redis_client.get(f"features:{customer_id}")
            if cached:
                return json.loads(cached)
        
        # Compute features
        features = self._compute_features(customer_id)
        
        # Cache for TTL
        if use_cache:
            self.redis_client.setex(
                f"features:{customer_id}",
                self.ttl_seconds,
                json.dumps(features)
            )
        
        return features
    
    def update_customer_features(self, customer_id: str):
        """Update features for a customer (called after new events)."""
        features = self._compute_features(customer_id)
        self.redis_client.setex(
            f"features:{customer_id}",
            self.ttl_seconds,
            json.dumps(features)
        )
    
    def _compute_features(self, customer_id: str) -> Dict[str, Any]:
        """Compute all features for a customer."""
        now = datetime.utcnow()
        
        # Get customer record
        customer = self.db.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        
        if not customer:
            logger.warning(f"Customer not found: {customer_id}")
            return {}
        
        features = {}
        
        # Demographics features
        features.update(self._compute_demographic_features(customer))
        
        # Customer service features
        features.update(self._compute_service_features(customer_id, now))
        
        # STB telemetry features
        features.update(self._compute_stb_features(customer_id, now))
        
        # Web analytics features
        features.update(self._compute_web_features(customer_id, now))
        
        # Billing features
        features.update(self._compute_billing_features(customer_id, now))
        
        # Behavioral features
        features.update(self._compute_behavioral_features(customer_id, customer, now))
        
        return features
    
    def _compute_demographic_features(self, customer: Customer) -> Dict[str, Any]:
        """Compute demographic features."""
        return {
            'customer_segment': customer.customer_segment,
            'age_range': customer.age_range or 'unknown',
            'household_size': customer.household_size or 0,
            'estimated_income': customer.estimated_income or 'unknown',
            'tenure_days': (datetime.utcnow().date() - customer.account_created_date).days if customer.account_created_date else 0,
            'monthly_recurring_revenue': float(customer.monthly_recurring_revenue or 0),
            'lifetime_value': float(customer.lifetime_value or 0),
            'auto_renew': 1 if customer.auto_renew else 0,
            'days_until_contract_end': (customer.contract_end_date - datetime.utcnow().date()).days if customer.contract_end_date else 999,
        }
    
    def _compute_service_features(self, customer_id: str, now: datetime) -> Dict[str, Any]:
        """Compute customer service interaction features."""
        # Last 30 days
        thirty_days_ago = now - timedelta(days=30)
        
        interactions = self.db.query(CustomerServiceInteraction).filter(
            and_(
                CustomerServiceInteraction.customer_id == customer_id,
                CustomerServiceInteraction.timestamp >= thirty_days_ago
            )
        ).all()
        
        if not interactions:
            return {
                'service_calls_30d': 0,
                'avg_sentiment_30d': 0.0,
                'unresolved_calls_30d': 0,
                'avg_call_duration_30d': 0.0,
                'days_since_last_call': 999,
            }
        
        sentiments = [i.sentiment_score for i in interactions if i.sentiment_score is not None]
        durations = [i.duration_seconds for i in interactions if i.duration_seconds is not None]
        unresolved = [i for i in interactions if i.resolution_status == 'unresolved']
        last_call = max(i.timestamp for i in interactions)
        
        return {
            'service_calls_30d': len(interactions),
            'avg_sentiment_30d': sum(sentiments) / len(sentiments) if sentiments else 0.0,
            'unresolved_calls_30d': len(unresolved),
            'avg_call_duration_30d': sum(durations) / len(durations) if durations else 0.0,
            'days_since_last_call': (now - last_call).days,
        }
    
    def _compute_stb_features(self, customer_id: str, now: datetime) -> Dict[str, Any]:
        """Compute set-top box telemetry features."""
        thirty_days_ago = now - timedelta(days=30)
        
        events = self.db.query(STBTelemetry).filter(
            and_(
                STBTelemetry.customer_id == customer_id,
                STBTelemetry.timestamp >= thirty_days_ago
            )
        ).all()
        
        if not events:
            return {
                'stb_errors_30d': 0,
                'avg_network_quality_30d': 100.0,
                'total_buffer_events_30d': 0,
                'total_viewing_hours_30d': 0.0,
            }
        
        errors = [e for e in events if e.event_type == 'error']
        network_qualities = [e.network_quality for e in events if e.network_quality is not None]
        buffer_events = sum(e.buffer_events for e in events)
        viewing_seconds = sum(e.viewing_duration_seconds or 0 for e in events)
        
        return {
            'stb_errors_30d': len(errors),
            'avg_network_quality_30d': sum(network_qualities) / len(network_qualities) if network_qualities else 100.0,
            'total_buffer_events_30d': buffer_events,
            'total_viewing_hours_30d': viewing_seconds / 3600.0,
        }
    
    def _compute_web_features(self, customer_id: str, now: datetime) -> Dict[str, Any]:
        """Compute web analytics features."""
        thirty_days_ago = now - timedelta(days=30)
        
        events = self.db.query(WebAnalyticsEvent).filter(
            and_(
                WebAnalyticsEvent.customer_id == customer_id,
                WebAnalyticsEvent.timestamp >= thirty_days_ago
            )
        ).all()
        
        if not events:
            return {
                'web_sessions_30d': 0,
                'total_engagement_minutes_30d': 0.0,
                'days_since_last_web_activity': 999,
            }
        
        sessions = set(e.session_id for e in events)
        engagement_ms = sum(e.engagement_time_msec or 0 for e in events)
        last_activity = max(e.timestamp for e in events)
        
        return {
            'web_sessions_30d': len(sessions),
            'total_engagement_minutes_30d': engagement_ms / 60000.0,
            'days_since_last_web_activity': (now - last_activity).days,
        }
    
    def _compute_billing_features(self, customer_id: str, now: datetime) -> Dict[str, Any]:
        """Compute billing and payment features."""
        # Last 90 days for billing history
        ninety_days_ago = now - timedelta(days=90)
        
        events = self.db.query(BillingEvent).filter(
            and_(
                BillingEvent.customer_id == customer_id,
                BillingEvent.timestamp >= ninety_days_ago
            )
        ).order_by(BillingEvent.timestamp.desc()).all()
        
        if not events:
            return {
                'payment_failures_90d': 0,
                'disputes_90d': 0,
                'days_overdue': 0,
                'account_balance': 0.0,
            }
        
        failures = [e for e in events if e.event_type == 'payment_failed']
        disputes = [e for e in events if e.event_type == 'dispute_opened']
        latest_event = events[0]
        
        return {
            'payment_failures_90d': len(failures),
            'disputes_90d': len(disputes),
            'days_overdue': latest_event.days_overdue or 0,
            'account_balance': float(latest_event.account_balance or 0),
        }
    
    def _compute_behavioral_features(self, customer_id: str, customer: Customer, now: datetime) -> Dict[str, Any]:
        """Compute behavioral and engagement features."""
        # Combine various signals
        features = {}
        
        # Engagement score (composite)
        stb_features = self._compute_stb_features(customer_id, now)
        web_features = self._compute_web_features(customer_id, now)
        
        engagement_score = (
            min(stb_features.get('total_viewing_hours_30d', 0) / 100.0, 1.0) * 0.5 +
            min(web_features.get('web_sessions_30d', 0) / 30.0, 1.0) * 0.5
        )
        features['engagement_score'] = engagement_score
        
        # Risk indicators
        service_features = self._compute_service_features(customer_id, now)
        billing_features = self._compute_billing_features(customer_id, now)
        
        risk_score = (
            min(service_features.get('unresolved_calls_30d', 0) / 5.0, 1.0) * 0.3 +
            min(billing_features.get('payment_failures_90d', 0) / 3.0, 1.0) * 0.4 +
            min(billing_features.get('days_overdue', 0) / 30.0, 1.0) * 0.3
        )
        features['risk_score'] = risk_score
        
        return features
    
    def get_batch_features(self, customer_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get features for multiple customers (batch)."""
        return {cid: self.get_customer_features(cid) for cid in customer_ids}
