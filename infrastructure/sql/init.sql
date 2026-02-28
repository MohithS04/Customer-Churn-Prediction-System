-- Customer Churn Prediction System Database Schema

-- Customers table (from CRM)
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    account_created_date DATE NOT NULL,
    customer_segment VARCHAR(20) NOT NULL CHECK (customer_segment IN ('residential', 'small_business', 'enterprise')),
    service_address_street VARCHAR(255),
    service_address_city VARCHAR(100),
    service_address_state VARCHAR(2),
    service_address_zip_code VARCHAR(10),
    age_range VARCHAR(20),
    household_size INTEGER,
    estimated_income VARCHAR(20),
    plan_id VARCHAR(50),
    monthly_recurring_revenue DECIMAL(10, 2),
    contract_end_date DATE,
    auto_renew BOOLEAN DEFAULT TRUE,
    lifetime_value DECIMAL(10, 2),
    churn_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customer service interactions
CREATE TABLE IF NOT EXISTS customer_service_interactions (
    interaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    timestamp TIMESTAMP NOT NULL,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('phone', 'chat', 'email', 'social')),
    duration_seconds INTEGER,
    reason_category VARCHAR(100),
    resolution_status VARCHAR(20) CHECK (resolution_status IN ('resolved', 'escalated', 'unresolved')),
    agent_id VARCHAR(50),
    sentiment_score DECIMAL(3, 2) CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    transcript_text TEXT,
    transfer_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Set-top box telemetry events
CREATE TABLE IF NOT EXISTS stb_telemetry (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('channel_change', 'power_on', 'power_off', 'error', 'recording')),
    channel_id VARCHAR(50),
    content_id VARCHAR(100),
    viewing_duration_seconds INTEGER,
    error_code VARCHAR(50),
    buffer_events INTEGER DEFAULT 0,
    network_quality DECIMAL(5, 2) CHECK (network_quality >= 0 AND network_quality <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Web/mobile analytics events
CREATE TABLE IF NOT EXISTS web_analytics_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(50),
    session_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    event_name VARCHAR(100) NOT NULL,
    page_url VARCHAR(500),
    device_category VARCHAR(20) CHECK (device_category IN ('mobile', 'tablet', 'desktop')),
    app_version VARCHAR(20),
    engagement_time_msec INTEGER,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Billing and payment events
CREATE TABLE IF NOT EXISTS billing_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(30) NOT NULL CHECK (event_type IN ('payment_received', 'payment_failed', 'dispute_opened', 'plan_change')),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    timestamp TIMESTAMP NOT NULL,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    amount DECIMAL(10, 2),
    payment_method VARCHAR(20) CHECK (payment_method IN ('credit_card', 'bank_transfer', 'auto_pay')),
    billing_cycle_day INTEGER CHECK (billing_cycle_day >= 1 AND billing_cycle_day <= 31),
    account_balance DECIMAL(10, 2),
    days_overdue INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Churn predictions
CREATE TABLE IF NOT EXISTS churn_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    prediction_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    churn_probability DECIMAL(5, 4) NOT NULL CHECK (churn_probability >= 0 AND churn_probability <= 1),
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    prediction_horizon_days INTEGER NOT NULL DEFAULT 30,
    model_version VARCHAR(50) NOT NULL,
    top_risk_factors JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Retention actions
CREATE TABLE IF NOT EXISTS retention_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN ('discount', 'upgrade', 'service_call', 'loyalty_reward', 'custom_offer')),
    recommended_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'rejected', 'expired')),
    offer_details JSONB,
    predicted_impact DECIMAL(5, 4),
    actual_outcome VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature store (online features cache)
CREATE TABLE IF NOT EXISTS feature_store_online (
    customer_id VARCHAR(50) PRIMARY KEY REFERENCES customers(customer_id),
    feature_set JSONB NOT NULL,
    computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ttl_seconds INTEGER DEFAULT 3600
);

-- Model metadata
CREATE TABLE IF NOT EXISTS model_metadata (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    training_timestamp TIMESTAMP NOT NULL,
    performance_metrics JSONB NOT NULL,
    feature_list JSONB NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    deployment_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data quality metrics
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10, 4),
    threshold_value DECIMAL(10, 4),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pass', 'fail', 'warning')),
    computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_customers_segment ON customers(customer_segment);
CREATE INDEX IF NOT EXISTS idx_customers_churn_date ON customers(churn_date);
CREATE INDEX IF NOT EXISTS idx_interactions_customer_timestamp ON customer_service_interactions(customer_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_stb_customer_timestamp ON stb_telemetry(customer_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_customer_timestamp ON web_analytics_events(customer_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_billing_customer_timestamp ON billing_events(customer_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_customer_timestamp ON churn_predictions(customer_id, prediction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_risk_level ON churn_predictions(risk_level);
CREATE INDEX IF NOT EXISTS idx_actions_customer_status ON retention_actions(customer_id, status);

-- MLflow backend store (created separately if needed)
-- Note: PostgreSQL doesn't support IF NOT EXISTS for CREATE DATABASE
-- Run manually: CREATE DATABASE mlflow;
