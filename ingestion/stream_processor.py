"""Stream processor for real-time event processing."""

import logging
from datetime import datetime
from typing import Dict, Any
from database import SessionLocal
from database.models import (
    CustomerServiceInteraction,
    STBTelemetry,
    WebAnalyticsEvent,
    BillingEvent
)
from features.feature_store import FeatureStore

logger = logging.getLogger(__name__)


class StreamProcessor:
    """Process streaming events and update feature store."""
    
    def __init__(self):
        self.feature_store = FeatureStore()
        self.db = SessionLocal()
    
    def process_event(self, topic: str, message: Dict[str, Any], key: str = None):
        """
        Process an event from Kafka.
        
        Args:
            topic: Kafka topic name
            message: Event data
            key: Partition key (usually customer_id)
        """
        try:
            if 'customer-service-events' in topic:
                self._process_customer_service_event(message)
            elif 'stb-telemetry-events' in topic:
                self._process_stb_telemetry(message)
            elif 'web-analytics-events' in topic:
                self._process_web_analytics(message)
            elif 'billing-events' in topic:
                self._process_billing_event(message)
            else:
                logger.warning(f"Unknown topic: {topic}")
            
            # Update feature store after processing
            customer_id = message.get('customer_id') or key
            if customer_id:
                self.feature_store.update_customer_features(customer_id)
                
        except Exception as e:
            logger.error(f"Error processing event from {topic}: {e}", exc_info=True)
    
    def _process_customer_service_event(self, event: Dict[str, Any]):
        """Process customer service interaction event."""
        try:
            interaction = CustomerServiceInteraction(
                interaction_id=event.get('interaction_id'),
                customer_id=event['customer_id'],
                timestamp=datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')),
                channel=event.get('channel'),
                duration_seconds=event.get('duration_seconds'),
                reason_category=event.get('reason_category'),
                resolution_status=event.get('resolution_status'),
                agent_id=event.get('agent_id'),
                sentiment_score=event.get('sentiment_score'),
                transcript_text=event.get('transcript_text'),
                transfer_count=event.get('transfer_count', 0),
            )
            self.db.add(interaction)
            self.db.commit()
            logger.debug(f"Saved customer service interaction: {event.get('interaction_id')}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving customer service interaction: {e}")
            raise
    
    def _process_stb_telemetry(self, event: Dict[str, Any]):
        """Process STB telemetry event."""
        try:
            telemetry = STBTelemetry(
                device_id=event['device_id'],
                customer_id=event['customer_id'],
                timestamp=datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')),
                event_type=event.get('event_type'),
                channel_id=event.get('channel_id'),
                content_id=event.get('content_id'),
                viewing_duration_seconds=event.get('viewing_duration_seconds'),
                error_code=event.get('error_code'),
                buffer_events=event.get('buffer_events', 0),
                network_quality=event.get('network_quality'),
            )
            self.db.add(telemetry)
            self.db.commit()
            logger.debug(f"Saved STB telemetry: {event.get('device_id')}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving STB telemetry: {e}")
            raise
    
    def _process_web_analytics(self, event: Dict[str, Any]):
        """Process web analytics event."""
        try:
            analytics = WebAnalyticsEvent(
                customer_id=event.get('customer_id'),
                session_id=event['session_id'],
                timestamp=datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')),
                event_name=event.get('event_name'),
                page_url=event.get('page_url'),
                device_category=event.get('device_category'),
                app_version=event.get('app_version'),
                engagement_time_msec=event.get('engagement_time_msec'),
                user_agent=event.get('user_agent'),
            )
            self.db.add(analytics)
            self.db.commit()
            logger.debug(f"Saved web analytics event: {event.get('event_id')}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving web analytics event: {e}")
            raise
    
    def _process_billing_event(self, event: Dict[str, Any]):
        """Process billing event."""
        try:
            billing = BillingEvent(
                event_type=event['event_type'],
                customer_id=event['customer_id'],
                timestamp=datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')),
                transaction_id=event['transaction_id'],
                amount=event.get('amount'),
                payment_method=event.get('payment_method'),
                billing_cycle_day=event.get('billing_cycle_day'),
                account_balance=event.get('account_balance'),
                days_overdue=event.get('days_overdue', 0),
            )
            self.db.add(billing)
            self.db.commit()
            logger.debug(f"Saved billing event: {event.get('transaction_id')}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving billing event: {e}")
            raise
