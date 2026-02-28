"""Kafka consumer for processing events from Kafka topics."""

import json
import logging
from typing import Callable, List
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from config import CONFIG

logger = logging.getLogger(__name__)


class EventConsumer:
    """Kafka consumer for processing events."""
    
    def __init__(self, bootstrap_servers: str = None, group_id: str = 'churn-prediction-ingestion'):
        self.bootstrap_servers = bootstrap_servers or CONFIG['kafka']['bootstrap_servers']
        self.group_id = group_id
        self.consumer = None
    
    def _create_consumer(self, topics: List[str]):
        """Create Kafka consumer instance."""
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            consumer_timeout_ms=1000,  # Timeout for polling
        )
    
    def consume(self, topics: List[str], callback: Callable):
        """
        Consume messages from Kafka topics.
        
        Args:
            topics: List of topic names to consume from
            callback: Function to process each message (topic, message)
        """
        self._create_consumer(topics)
        logger.info(f"Starting consumer for topics: {topics}")
        
        try:
            for message in self.consumer:
                try:
                    callback(message.topic, message.value, message.key)
                except Exception as e:
                    logger.error(f"Error processing message from {message.topic}: {e}")
                    # Continue processing other messages
        except KafkaError as e:
            logger.error(f"Kafka consumer error: {e}")
            raise
        finally:
            self.close()
    
    def close(self):
        """Close the consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
