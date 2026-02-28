"""Data source connectors for various external systems."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from ingestion.kafka_producer import (
    CustomerServiceEventProducer,
    STBTelemetryProducer,
    WebAnalyticsProducer,
    BillingEventProducer
)

logger = logging.getLogger(__name__)


class CustomerServiceConnector:
    """Connector for customer service call center data."""
    
    def __init__(self):
        self.producer = CustomerServiceEventProducer()
    
    def fetch_interactions(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        Fetch customer service interactions from external API.
        
        In production, this would call Genesys/Twilio API.
        For now, returns mock data structure.
        """
        # TODO: Implement actual API integration
        logger.info(f"Fetching interactions from {start_time} to {end_time}")
        return []
    
    def process_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Process incoming webhook from call center platform."""
        try:
            interaction = {
                'interaction_id': webhook_data.get('id'),
                'customer_id': webhook_data.get('customer_id'),
                'timestamp': webhook_data.get('timestamp', datetime.utcnow().isoformat()),
                'channel': webhook_data.get('channel', 'phone'),
                'duration_seconds': webhook_data.get('duration_seconds'),
                'reason_category': webhook_data.get('reason'),
                'resolution_status': webhook_data.get('status'),
                'agent_id': webhook_data.get('agent_id'),
                'sentiment_score': webhook_data.get('sentiment_score'),
                'transcript_text': webhook_data.get('transcript'),
                'transfer_count': webhook_data.get('transfer_count', 0),
            }
            
            return self.producer.publish_interaction(interaction)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False


class STBTelemetryConnector:
    """Connector for set-top box telemetry data."""
    
    def __init__(self):
        self.producer = STBTelemetryProducer()
    
    def process_mqtt_message(self, message: Dict[str, Any]) -> bool:
        """Process MQTT message from STB device."""
        try:
            telemetry = {
                'device_id': message.get('device_id'),
                'customer_id': message.get('customer_id'),
                'timestamp': message.get('timestamp', datetime.utcnow().isoformat()),
                'event_type': message.get('event_type'),
                'channel_id': message.get('channel_id'),
                'content_id': message.get('content_id'),
                'viewing_duration_seconds': message.get('viewing_duration'),
                'error_code': message.get('error_code'),
                'buffer_events': message.get('buffer_events', 0),
                'network_quality': message.get('network_quality'),
            }
            
            return self.producer.publish_telemetry(telemetry)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
            return False


class WebAnalyticsConnector:
    """Connector for web/mobile analytics data."""
    
    def __init__(self):
        self.producer = WebAnalyticsProducer()
    
    def process_analytics_event(self, event: Dict[str, Any]) -> bool:
        """Process analytics event from GA4 or custom tracking."""
        try:
            analytics_event = {
                'event_id': event.get('event_id'),
                'customer_id': event.get('user_id'),
                'session_id': event.get('session_id'),
                'timestamp': event.get('timestamp', datetime.utcnow().isoformat()),
                'event_name': event.get('event_name'),
                'page_url': event.get('page_location'),
                'device_category': event.get('device_category'),
                'app_version': event.get('app_version'),
                'engagement_time_msec': event.get('engagement_time_msec'),
                'user_agent': event.get('user_agent'),
            }
            
            return self.producer.publish_event(analytics_event)
        except Exception as e:
            logger.error(f"Error processing analytics event: {e}")
            return False


class BillingConnector:
    """Connector for billing and payment data via CDC."""
    
    def __init__(self):
        self.producer = BillingEventProducer()
    
    def process_cdc_event(self, cdc_event: Dict[str, Any]) -> bool:
        """Process Change Data Capture event from billing database."""
        try:
            # Extract after state from CDC event
            after = cdc_event.get('after', {})
            
            billing_event = {
                'event_type': self._determine_event_type(cdc_event),
                'customer_id': after.get('customer_id'),
                'timestamp': after.get('transaction_date', datetime.utcnow().isoformat()),
                'transaction_id': after.get('transaction_id'),
                'amount': float(after.get('amount', 0)),
                'payment_method': after.get('payment_method'),
                'billing_cycle_day': after.get('billing_cycle_day'),
                'account_balance': float(after.get('account_balance', 0)),
                'days_overdue': after.get('days_overdue', 0),
            }
            
            return self.producer.publish_billing_event(billing_event)
        except Exception as e:
            logger.error(f"Error processing CDC event: {e}")
            return False
    
    def _determine_event_type(self, cdc_event: Dict[str, Any]) -> str:
        """Determine event type from CDC operation."""
        op = cdc_event.get('op', '')
        after = cdc_event.get('after', {})
        
        if op == 'c':  # create
            if after.get('payment_status') == 'failed':
                return 'payment_failed'
            elif after.get('dispute_flag'):
                return 'dispute_opened'
            else:
                return 'payment_received'
        elif op == 'u':  # update
            if 'plan_id' in after:
                return 'plan_change'
        
        return 'payment_received'


class CRMConnector:
    """Connector for CRM customer master data."""
    
    def __init__(self):
        # For batch updates, we'll write directly to database
        pass
    
    def fetch_customers(self, last_sync_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch customer data from CRM system.
        
        In production, this would call Salesforce API or database.
        """
        # TODO: Implement actual CRM integration
        logger.info(f"Fetching customers updated since {last_sync_date}")
        return []
    
    def sync_customer(self, customer_data: Dict[str, Any]) -> bool:
        """Sync a single customer record to database."""
        # TODO: Implement database upsert
        return True
