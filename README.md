# Real-Time Customer Churn Prediction & Retention Optimization System

## Project Overview

An end-to-end real-time system that predicts customer churn risk 30-90 days in advance with 85%+ accuracy and recommends personalized retention interventions.

## Architecture

```
[Data Sources] → [Ingestion Layer] → [Stream Processing] → [Feature Store] 
→ [ML Pipeline] → [Prediction Service] → [Action Engine] → [Dashboard/API]
                           ↓
                    [Data Lake/Warehouse]
```

## Key Components

1. **Data Ingestion**: Kafka/Kinesis for real-time streaming, CDC for batch updates
2. **Stream Processing**: Apache Flink/Spark for real-time feature computation
3. **Feature Store**: Centralized feature management and serving
4. **ML Pipeline**: Model training, evaluation, and deployment
5. **Prediction API**: Real-time and batch scoring endpoints
6. **Action Engine**: Retention recommendation and campaign management
7. **Dashboards**: Executive and operational dashboards

## Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Kafka (via Docker)
- PostgreSQL
- Redis

### Fastest Way to Execute

**Option 1: Automated Script (Recommended)**
```bash
chmod +x scripts/quick_start.sh
./scripts/quick_start.sh
```

**Option 2: Manual Setup**

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start infrastructure:**
```bash
docker-compose up -d
```

3. **Initialize database:**
```bash
python scripts/init_db.py
```

4. **Generate sample data:**
```bash
python scripts/generate_sample_data.py
```

5. **Train initial model:**
```bash
python -m ml.train_model
```

6. **Start services (in separate terminals):**
```bash
# Terminal 1: Prediction API
python -m api.main

# Terminal 2: Dashboard
streamlit run dashboard/main.py

# Terminal 3 (Optional): Data Ingestion
python -m ingestion.start_ingestion
```

### Access Points

Once running, access:
- **API**: http://localhost:8000 (Docs: http://localhost:8000/docs)
- **Dashboard**: http://localhost:8501
- **MLflow**: http://localhost:5000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

### Detailed Execution Guide

For comprehensive step-by-step instructions, troubleshooting, and production deployment, see **[EXECUTION_GUIDE.md](EXECUTION_GUIDE.md)**

## Project Structure

```
.
├── ingestion/          # Data ingestion pipelines
├── streaming/          # Stream processing jobs
├── features/           # Feature store and engineering
├── ml/                 # ML pipeline and models
├── api/                # Prediction API service
├── action_engine/      # Retention action recommendations
├── dashboard/          # Web dashboards
├── data_quality/      # Data validation and quality checks
├── monitoring/         # Observability and alerting
├── infrastructure/     # Terraform, Docker configs
├── scripts/            # Utility scripts
└── tests/              # Test suites
```

## Success Metrics

- **Model Accuracy**: 85%+ precision, 80%+ recall
- **Latency**: <100ms per prediction
- **Uptime**: 99.9% availability
- **Data Freshness**: <5 minute lag from event to feature

## License

Proprietary - Internal Use Only
