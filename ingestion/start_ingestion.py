"""Main entry point for starting data ingestion services."""

import logging
import signal
import sys
from ingestion.kafka_consumer import EventConsumer
from ingestion.stream_processor import StreamProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionService:
    """Main ingestion service orchestrator."""
    
    def __init__(self):
        self.consumer = EventConsumer()
        self.processor = StreamProcessor()
        self.running = False
    
    def start(self):
        """Start ingestion service."""
        logger.info("Starting ingestion service...")
        self.running = True
        
        # Start consuming from Kafka topics
        topics = [
            'customer-service-events',
            'stb-telemetry-events',
            'web-analytics-events',
            'billing-events'
        ]
        
        try:
            self.consumer.consume(topics, self.processor.process_event)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.stop()
    
    def stop(self):
        """Stop ingestion service."""
        logger.info("Stopping ingestion service...")
        self.running = False
        self.consumer.close()
        logger.info("Ingestion service stopped")


def main():
    """Main entry point."""
    service = IngestionService()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal")
        service.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    service.start()


if __name__ == '__main__':
    main()
