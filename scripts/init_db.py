"""Initialize database schema."""

import logging
from database import engine, Base
from database.models import (
    Customer, CustomerServiceInteraction, STBTelemetry,
    WebAnalyticsEvent, BillingEvent, ChurnPrediction,
    RetentionAction, ModelMetadata, DataQualityMetrics
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Create all database tables."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


if __name__ == '__main__':
    init_database()
