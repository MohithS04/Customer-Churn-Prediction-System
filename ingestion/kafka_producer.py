"""Kafka producer for publishing events to Kafka topics."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
from config import CONFIG

logger = logging.getLogger(__name__)


class EventProducer:
    """Kafka producer for publishing events."""
    
    def __init__(self, bootstrap_servers: str = None):
        self.bootstrap_servers = bootstrap_servers or CONFIG['kafka']['bootstrap_servers']
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1,
        )
    
    def publish_event(self, topic: str, event: Dict[str, Any], key: Optional[str] = None) -> bool:
        """
        Publish an event to Kafka topic.
        
        Args:
            topic: Kafka topic name
            event: Event data dictionary
            key: Optional partition key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata
            event['_ingestion_timestamp'] = datetime.utcnow().isoformat()
            
            future = self.producer.send(topic, value=event, key=key)
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Published event to topic={topic}, partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish event to {topic}: {e}")
            return False
    
    def publish_batch(self, topic: str, events: list[Dict[str, Any]], key_field: str = None) -> int:
        """
        Publish a batch of events.
        
        Args:
            topic: Kafka topic name
            events: List of event dictionaries
            key_field: Optional field name to use as partition key
            
        Returns:
            Number of successfully published events
        """
        success_count = 0
        for event in events:
            key = event.get(key_field) if key_field else None
            if self.publish_event(topic, event, key):
                success_count += 1
        
        logger.info(f"Published {success_count}/{len(events)} events to {topic}")
        return success_count
    
    def close(self):
        """Close the producer."""
        self.producer.close()


class CustomerServiceEventProducer(EventProducer):
    """Producer for customer service interaction events."""
    
    def __init__(self):
        topic = CONFIG['kafka']['topics']['customer_service']
        super().__init__()
        self.topic = topic
    
    def publish_interaction(self, interaction: Dict[str, Any]) -> bool:
        """Publish a customer service interaction event."""
        return self.publish_event(self.topic, interaction, key=interaction.get('customer_id'))


class STBTelemetryProducer(EventProducer):
    """Producer for set-top box telemetry events."""
    
    def __init__(self):
        topic = CONFIG['kafka']['topics']['stb_telemetry']
        super().__init__()
        self.topic = topic
    
    def publish_telemetry(self, telemetry: Dict[str, Any]) -> bool:
        """Publish a STB telemetry event."""
        return self.publish_event(self.topic, telemetry, key=telemetry.get('customer_id'))


class WebAnalyticsProducer(EventProducer):
    """Producer for web analytics events."""
    
    def __init__(self):
        topic = CONFIG['kafka']['topics']['analytics']
        super().__init__()
        self.topic = topic
    
    def publish_event(self, event: Dict[str, Any]) -> bool:
        """Publish a web analytics event."""
        return super().publish_event(self.topic, event, key=event.get('customer_id'))


class BillingEventProducer(EventProducer):
    """Producer for billing events."""
    
    def __init__(self):
        topic = CONFIG['kafka']['topics']['billing']
        super().__init__()
        self.topic = topic
    
    def publish_billing_event(self, event: Dict[str, Any]) -> bool:
        """Publish a billing event."""
        return self.publish_event(self.topic, event, key=event.get('customer_id'))
