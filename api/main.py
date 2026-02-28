"""FastAPI application for churn prediction service."""

import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
from database import get_db, SessionLocal
from database.models import ChurnPrediction, Customer
from features.feature_store import FeatureStore
from ml.model_loader import ModelLoader
from action_engine.action_recommender import ActionRecommender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
prediction_counter = Counter('churn_predictions_total', 'Total number of churn predictions')
prediction_latency = Histogram('churn_prediction_latency_seconds', 'Churn prediction latency')

app = FastAPI(
    title="Churn Prediction API",
    description="Real-time customer churn prediction and retention optimization",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
feature_store = FeatureStore()
model_loader = ModelLoader()
action_recommender = ActionRecommender()
model = None


@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    global model
    logger.info("Loading model...")
    model = model_loader.get_active_model()
    if model is None:
        logger.warning("No model found. Please train a model first.")
    else:
        logger.info("Model loaded successfully")


# Request/Response models
class ChurnPredictionRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    prediction_horizon_days: int = Field(30, ge=1, le=90, description="Days ahead to predict")


class ChurnPredictionResponse(BaseModel):
    customer_id: str
    churn_probability: float = Field(..., ge=0, le=1)
    risk_level: str = Field(..., description="low, medium, high, or critical")
    prediction_timestamp: datetime
    model_version: str
    top_risk_factors: Optional[Dict[str, Any]] = None
    recommended_actions: Optional[List[Dict[str, Any]]] = None


class BatchPredictionRequest(BaseModel):
    customer_ids: List[str] = Field(..., min_items=1, max_items=1000)


class BatchPredictionResponse(BaseModel):
    predictions: List[ChurnPredictionResponse]
    total_processed: int
    processing_time_seconds: float


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "churn-prediction-api",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/predict/churn", response_model=ChurnPredictionResponse)
async def predict_churn(
    request: ChurnPredictionRequest,
    background_tasks: BackgroundTasks
):
    """
    Predict churn probability for a single customer.
    
    - **customer_id**: Customer identifier
    - **prediction_horizon_days**: Days ahead to predict (default: 30)
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    
    try:
        # Get features
        features = feature_store.get_customer_features(request.customer_id)
        
        if not features:
            raise HTTPException(status_code=404, detail=f"Customer {request.customer_id} not found")
        
        # Make prediction
        prediction_result = model_loader.predict(model, features)
        
        # Get risk factors (simplified - in production, use SHAP values)
        top_risk_factors = _extract_risk_factors(features, prediction_result['churn_probability'])
        
        # Get recommended actions
        recommended_actions = action_recommender.recommend_actions(
            request.customer_id,
            prediction_result['churn_probability'],
            prediction_result['risk_level']
        )
        
        response = ChurnPredictionResponse(
            customer_id=request.customer_id,
            churn_probability=prediction_result['churn_probability'],
            risk_level=prediction_result['risk_level'],
            prediction_timestamp=datetime.utcnow(),
            model_version="1.0.0",  # In production, get from model metadata
            top_risk_factors=top_risk_factors,
            recommended_actions=recommended_actions
        )
        
        # Save prediction to database (async)
        background_tasks.add_task(
            _save_prediction,
            request.customer_id,
            prediction_result['churn_probability'],
            prediction_result['risk_level'],
            request.prediction_horizon_days,
            top_risk_factors
        )
        
        # Update metrics
        prediction_counter.inc()
        prediction_latency.observe(time.time() - start_time)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting churn: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    """
    Batch prediction for multiple customers.
    
    - **customer_ids**: List of customer identifiers (max 1000)
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    predictions = []
    
    try:
        # Get features for all customers
        features_dict = feature_store.get_batch_features(request.customer_ids)
        
        for customer_id in request.customer_ids:
            if customer_id not in features_dict:
                continue
            
            features = features_dict[customer_id]
            prediction_result = model_loader.predict(model, features)
            
            top_risk_factors = _extract_risk_factors(features, prediction_result['churn_probability'])
            recommended_actions = action_recommender.recommend_actions(
                customer_id,
                prediction_result['churn_probability'],
                prediction_result['risk_level']
            )
            
            predictions.append(ChurnPredictionResponse(
                customer_id=customer_id,
                churn_probability=prediction_result['churn_probability'],
                risk_level=prediction_result['risk_level'],
                prediction_timestamp=datetime.utcnow(),
                model_version="1.0.0",
                top_risk_factors=top_risk_factors,
                recommended_actions=recommended_actions
            ))
        
        processing_time = time.time() - start_time
        
        return BatchPredictionResponse(
            predictions=predictions,
            total_processed=len(predictions),
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in batch prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predictions/history")
async def get_prediction_history(
    customer_id: Optional[str] = None,
    limit: int = 100,
    db=Depends(get_db)
):
    """Get prediction history."""
    query = db.query(ChurnPrediction)
    
    if customer_id:
        query = query.filter(ChurnPrediction.customer_id == customer_id)
    
    predictions = query.order_by(ChurnPrediction.prediction_timestamp.desc()).limit(limit).all()
    
    return {
        "predictions": [
            {
                "prediction_id": str(p.prediction_id),
                "customer_id": p.customer_id,
                "churn_probability": p.churn_probability,
                "risk_level": p.risk_level,
                "prediction_timestamp": p.prediction_timestamp.isoformat(),
                "model_version": p.model_version,
            }
            for p in predictions
        ]
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


def _extract_risk_factors(features: Dict[str, Any], churn_probability: float) -> Dict[str, Any]:
    """Extract top risk factors from features."""
    # Simplified - in production, use SHAP values
    risk_factors = []
    
    if features.get('payment_failures_90d', 0) > 0:
        risk_factors.append({
            'factor': 'payment_failures',
            'value': features['payment_failures_90d'],
            'impact': 'high'
        })
    
    if features.get('days_overdue', 0) > 0:
        risk_factors.append({
            'factor': 'days_overdue',
            'value': features['days_overdue'],
            'impact': 'high'
        })
    
    if features.get('unresolved_calls_30d', 0) > 2:
        risk_factors.append({
            'factor': 'unresolved_service_calls',
            'value': features['unresolved_calls_30d'],
            'impact': 'medium'
        })
    
    if features.get('avg_sentiment_30d', 0) < -0.3:
        risk_factors.append({
            'factor': 'negative_sentiment',
            'value': features['avg_sentiment_30d'],
            'impact': 'medium'
        })
    
    return {
        'top_factors': risk_factors[:5],
        'total_factors': len(risk_factors)
    }


def _save_prediction(
    customer_id: str,
    churn_probability: float,
    risk_level: str,
    prediction_horizon_days: int,
    top_risk_factors: Dict[str, Any]
):
    """Save prediction to database."""
    try:
        db = SessionLocal()
        prediction = ChurnPrediction(
            customer_id=customer_id,
            churn_probability=churn_probability,
            risk_level=risk_level,
            prediction_horizon_days=prediction_horizon_days,
            model_version="1.0.0",
            top_risk_factors=top_risk_factors
        )
        db.add(prediction)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Error saving prediction: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
