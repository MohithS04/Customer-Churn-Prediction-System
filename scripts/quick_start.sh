#!/bin/bash

# Quick Start Script for Churn Prediction System

set -e

echo "🚀 Starting Churn Prediction System Setup..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip and build tools first
echo "📦 Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

# Install dependencies using fixed method
echo "📥 Installing dependencies..."
if [ -f "scripts/install_dependencies.sh" ]; then
    bash scripts/install_dependencies.sh
else
    # Fallback: install PyYAML first, then requirements
    pip install "pyyaml>=6.0.1"
    pip install -r requirements.txt || {
        echo "⚠️  Some packages failed to install. Trying minimal requirements..."
        pip install -r requirements-minimal.txt 2>/dev/null || echo "⚠️  Installation had issues. See TROUBLESHOOTING.md"
    }
fi

# Copy .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "⚙️  Creating .env file..."
        cp .env.example .env
        echo "⚠️  Please update .env with your configuration"
    else
        echo "⚠️  .env.example not found, creating basic .env file..."
        cat > .env << EOF
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_DB=churn_prediction
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_HOST=localhost
REDIS_PORT=6379
MLFLOW_TRACKING_URI=http://localhost:5001
EOF
    fi
fi

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Initialize database
echo "🗄️  Initializing database..."
PYTHONPATH=. python scripts/init_db.py

# Generate sample data
echo "📊 Generating sample data..."
PYTHONPATH=. python scripts/generate_sample_data.py

# Train model
echo "🤖 Training initial model..."
PYTHONPATH=. python -m ml.train_model

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start API: python -m api.main"
echo "2. Start Dashboard: streamlit run dashboard/main.py"
echo "3. Start Ingestion: python -m ingestion.start_ingestion"
echo ""
echo "Access points:"
echo "- API: http://localhost:8000"
echo "- Dashboard: http://localhost:8501"
echo "- MLflow: http://localhost:5000"
echo "- Grafana: http://localhost:3000"
