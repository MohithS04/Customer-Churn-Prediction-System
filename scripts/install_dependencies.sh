#!/bin/bash

# Fixed dependency installation script
# This script installs dependencies while avoiding problematic packages

set -e

echo "🔧 Installing dependencies (fixed version)..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Upgrade pip and build tools
echo "📦 Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install PyYAML first (fixes build issues)
echo "📦 Installing PyYAML..."
pip install "pyyaml>=6.0.1"

# Install core packages in batches
echo "📦 Installing core data processing..."
pip install pandas numpy pyarrow

echo "📦 Installing stream processing..."
pip install kafka-python confluent-kafka

echo "📦 Installing feature store..."
pip install redis

echo "📦 Installing ML libraries..."
pip install scikit-learn xgboost lightgbm shap mlflow optuna

echo "📦 Installing API framework..."
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings

echo "📦 Installing database..."
pip install sqlalchemy psycopg2-binary alembic

echo "📦 Installing monitoring..."
pip install prometheus-client

echo "📦 Installing dashboard..."
pip install streamlit plotly

echo "📦 Installing utilities..."
pip install python-dotenv click tqdm python-dateutil pytz

echo "📦 Installing testing..."
pip install pytest pytest-cov pytest-asyncio faker

echo "📦 Installing security..."
pip install cryptography "python-jose[cryptography]" passlib[bcrypt]

echo "📦 Installing HTTP clients..."
pip install httpx requests

echo "📦 Installing data validation..."
pip install pandera marshmallow cerberus

# Optional: Try to install polars (may fail on some systems)
echo "📦 Installing optional packages..."
pip install polars || echo "⚠️  Polars installation failed (optional, continuing...)"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Note: catboost, apache-flink, pyspark, and great-expectations were skipped"
echo "      as they are optional and may cause build issues."
echo ""
echo "If you need these packages, install them separately:"
echo "  pip install catboost  # (may require Python 3.11 or earlier)"
