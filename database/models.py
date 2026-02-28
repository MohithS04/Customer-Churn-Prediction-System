"""SQLAlchemy models for the churn prediction system."""

from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, Text, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
import uuid


class Customer(Base):
    """Customer master data from CRM."""
    __tablename__ = 'customers'
    
    customer_id = Column(String(50), primary_key=True)
    account_created_date = Column(Date, nullable=False)
    customer_segment = Column(String(20), nullable=False)
    service_address_street = Column(String(255))
    service_address_city = Column(String(100))
    service_address_state = Column(String(2))
    service_address_zip_code = Column(String(10))
    age_range = Column(String(20))
    household_size = Column(Integer)
    estimated_income = Column(String(20))
    plan_id = Column(String(50))
    monthly_recurring_revenue = Column(Float)
    contract_end_date = Column(Date)
    auto_renew = Column(Boolean, default=True)
    lifetime_value = Column(Float)
    churn_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CustomerServiceInteraction(Base):
    """Customer service call center interactions."""
    __tablename__ = 'customer_service_interactions'
    
    interaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    duration_seconds = Column(Integer)
    reason_category = Column(String(100))
    resolution_status = Column(String(20))
    agent_id = Column(String(50))
    sentiment_score = Column(Float)
    transcript_text = Column(Text)
    transfer_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class STBTelemetry(Base):
    """Set-top box telemetry events."""
    __tablename__ = 'stb_telemetry'
    
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(100), nullable=False)
    customer_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String(20), nullable=False)
    channel_id = Column(String(50))
    content_id = Column(String(100))
    viewing_duration_seconds = Column(Integer)
    error_code = Column(String(50))
    buffer_events = Column(Integer, default=0)
    network_quality = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class WebAnalyticsEvent(Base):
    """Web and mobile app analytics events."""
    __tablename__ = 'web_analytics_events'
    
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(50), index=True)
    session_id = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_name = Column(String(100), nullable=False)
    page_url = Column(String(500))
    device_category = Column(String(20))
    app_version = Column(String(20))
    engagement_time_msec = Column(Integer)
    user_agent = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class BillingEvent(Base):
    """Billing and payment events."""
    __tablename__ = 'billing_events'
    
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(30), nullable=False)
    customer_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    transaction_id = Column(String(100), unique=True, nullable=False)
    amount = Column(Float)
    payment_method = Column(String(20))
    billing_cycle_day = Column(Integer)
    account_balance = Column(Float)
    days_overdue = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class ChurnPrediction(Base):
    """Churn prediction results."""
    __tablename__ = 'churn_predictions'
    
    prediction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(50), nullable=False, index=True)
    prediction_timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    churn_probability = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False, index=True)
    prediction_horizon_days = Column(Integer, nullable=False, default=30)
    model_version = Column(String(50), nullable=False)
    top_risk_factors = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())


class RetentionAction(Base):
    """Retention action recommendations and executions."""
    __tablename__ = 'retention_actions'
    
    action_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(50), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)
    recommended_at = Column(DateTime, nullable=False, default=func.now())
    executed_at = Column(DateTime)
    status = Column(String(20), nullable=False, default='pending', index=True)
    offer_details = Column(JSON)
    predicted_impact = Column(Float)
    actual_outcome = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())


class ModelMetadata(Base):
    """ML model metadata and versioning."""
    __tablename__ = 'model_metadata'
    
    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    model_type = Column(String(50), nullable=False)
    training_timestamp = Column(DateTime, nullable=False)
    performance_metrics = Column(JSON, nullable=False)
    feature_list = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=False)
    deployment_timestamp = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class DataQualityMetrics(Base):
    """Data quality metrics and validation results."""
    __tablename__ = 'data_quality_metrics'
    
    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_source = Column(String(50), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float)
    threshold_value = Column(Float)
    status = Column(String(20), nullable=False)
    computed_at = Column(DateTime, nullable=False, default=func.now())
    details = Column(JSON)
