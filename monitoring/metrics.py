"""Prometheus metrics definitions."""

from prometheus_client import Counter, Histogram, Gauge, Summary

# Prediction metrics
churn_predictions_total = Counter(
    'churn_predictions_total',
    'Total number of churn predictions',
    ['risk_level', 'model_version']
)

churn_prediction_latency = Histogram(
    'churn_prediction_latency_seconds',
    'Churn prediction latency in seconds',
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

churn_prediction_probability = Histogram(
    'churn_prediction_probability',
    'Distribution of churn probabilities',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Data pipeline metrics
data_ingestion_events_total = Counter(
    'data_ingestion_events_total',
    'Total number of ingested events',
    ['source', 'status']
)

data_pipeline_lag_seconds = Gauge(
    'data_pipeline_lag_seconds',
    'Data pipeline lag in seconds',
    ['source']
)

feature_computation_duration = Summary(
    'feature_computation_duration_seconds',
    'Time taken to compute features',
    ['customer_id']
)

# Model metrics
model_accuracy = Gauge(
    'model_accuracy',
    'Current model accuracy',
    ['metric_name', 'model_version']
)

model_inference_count = Counter(
    'model_inference_count',
    'Total number of model inferences',
    ['model_version']
)

# System metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

database_connection_pool_size = Gauge(
    'database_connection_pool_size',
    'Database connection pool size'
)

redis_connection_pool_size = Gauge(
    'redis_connection_pool_size',
    'Redis connection pool size'
)
