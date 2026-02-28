"""Model loading and serving utilities."""

import pickle
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import mlflow
from config import CONFIG

logger = logging.getLogger(__name__)


class ModelLoader:
    """Load and manage ML models."""
    
    def __init__(self):
        self.model_cache: Dict[str, Any] = {}
        mlflow.set_tracking_uri(CONFIG['mlflow']['tracking_uri'])
    
    def load_model(self, model_path: str):
        """Load model from pickle file."""
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    
    def load_from_mlflow(self, run_id: str, model_name: str = "model"):
        """Load model from MLflow."""
        model_uri = f"runs:/{run_id}/{model_name}"
        return mlflow.sklearn.load_model(model_uri)
    
    def get_active_model(self) -> Optional[Any]:
        """Get the currently active model."""
        # In production, query database for active model
        # For now, load latest from models directory
        models_dir = Path("models")
        if not models_dir.exists():
            return None
        
        model_files = sorted(models_dir.glob("*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not model_files:
            return None
        
        latest_model = model_files[0]
        logger.info(f"Loading model: {latest_model}")
        return self.load_model(str(latest_model))
    
    def predict(self, model: Any, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make prediction with model.
        
        Args:
            model: Trained model
            features: Feature dictionary
            
        Returns:
            Prediction results with probability and risk level
        """
        import pandas as pd
        import numpy as np
        
        # Convert features to DataFrame
        df = pd.DataFrame([features])
        
        # Encode categorical variables (convert to numeric codes)
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col in df.columns:
                df[col] = pd.Categorical(df[col]).codes
        
        # Convert all columns to numeric (handle any remaining non-numeric)
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Fill NaN values with 0
        df = df.fillna(0)
        
        # Handle missing columns (fill with 0)
        if hasattr(model, 'feature_names_in_'):
            for col in model.feature_names_in_:
                if col not in df.columns:
                    df[col] = 0
            df = df[model.feature_names_in_]
        
        # Ensure all values are numeric
        df = df.astype(float)
        
        # Predict
        proba = model.predict_proba(df)[0, 1]
        prediction = model.predict(df)[0]
        
        # Determine risk level
        thresholds = CONFIG['retention_actions']['risk_thresholds']
        if proba >= thresholds['critical']:
            risk_level = 'critical'
        elif proba >= thresholds['high']:
            risk_level = 'high'
        elif proba >= thresholds['medium']:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'churn_probability': float(proba),
            'churn_prediction': int(prediction),
            'risk_level': risk_level,
        }
