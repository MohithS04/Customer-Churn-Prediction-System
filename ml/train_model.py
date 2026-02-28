"""Model training pipeline for churn prediction."""

import logging
import pickle
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    precision_recall_curve, roc_curve, classification_report
)
import xgboost as xgb
import lightgbm as lgb
import mlflow
import mlflow.sklearn
from config import CONFIG
from database import SessionLocal
from database.models import Customer, ChurnPrediction
from features.feature_store import FeatureStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChurnModelTrainer:
    """Train churn prediction models."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.feature_store = FeatureStore()
        # Try to connect to MLflow, fallback to file-based tracking if unavailable
        try:
            mlflow.set_tracking_uri(CONFIG['mlflow']['tracking_uri'])
            mlflow.set_experiment(CONFIG['mlflow']['experiment_name'])
            self.use_mlflow = True
        except Exception as e:
            print(f"Warning: MLflow not available ({e}), using file-based tracking")
            mlflow.set_tracking_uri("file:./mlruns")
            mlflow.set_experiment(CONFIG['mlflow']['experiment_name'])
            self.use_mlflow = True  # Still use MLflow, just file-based
    
    def prepare_training_data(self, lookback_days: int = 90, prediction_horizon: int = 30) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data with features and labels.
        
        Args:
            lookback_days: Days to look back for features
            prediction_horizon: Days ahead to predict churn
            
        Returns:
            Features DataFrame and labels Series
        """
        logger.info("Preparing training data...")
        
        # Get all customers
        customers = self.db.query(Customer).all()
        
        features_list = []
        labels = []
        
        for customer in customers:
            # Skip if customer doesn't have enough history
            if not customer.account_created_date:
                continue
            
            # Calculate label: churned within prediction_horizon days from lookback_date
            lookback_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            if customer.churn_date:
                # Label = 1 if churned within horizon, 0 otherwise
                days_until_churn = (customer.churn_date - lookback_date.date()).days
                label = 1 if 0 <= days_until_churn <= prediction_horizon else 0
            else:
                # Still active, label = 0
                label = 0
            
            # Get features at lookback_date (simplified - in production, use point-in-time correct features)
            try:
                features = self.feature_store.get_customer_features(customer.customer_id, use_cache=False)
                if features:
                    features_list.append(features)
                    labels.append(label)
            except Exception as e:
                logger.warning(f"Error getting features for {customer.customer_id}: {e}")
                continue
        
        logger.info(f"Prepared {len(features_list)} training samples")
        
        df = pd.DataFrame(features_list)
        y = pd.Series(labels)
        
        # Handle missing values
        df = df.fillna(0)
        
        # Encode categorical variables
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            df[col] = pd.Categorical(df[col]).codes
        
        return df, y
    
    def _safe_roc_auc(self, y_true, y_score):
        """Calculate ROC AUC safely, returning 0.5 if only one class exists."""
        try:
            return roc_auc_score(y_true, y_score)
        except ValueError:
            return 0.5

    def train_xgboost(self, X: pd.DataFrame, y: pd.Series) -> Tuple[xgb.XGBClassifier, Dict[str, float]]:
        """Train XGBoost model."""
        logger.info("Training XGBoost model...")
        
        params = CONFIG['ml_pipeline']['models'][0]['hyperparameters']
        
        model = xgb.XGBClassifier(
            max_depth=params['max_depth'],
            learning_rate=params['learning_rate'],
            n_estimators=params['n_estimators'],
            subsample=params['subsample'],
            random_state=42,
            eval_metric='logloss',
            base_score=0.5,  # Fix for logistic loss requirement
            use_label_encoder=False
        )
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        try:
            cv_scores = cross_val_score(model, X, y, cv=tscv, scoring='roc_auc')
        except ValueError:
            logger.warning("Could not compute cross-validation scores (likely single class in split)")
            cv_scores = np.array([0.5])
        
        # Train on full data
        model.fit(X, y)
        
        # Evaluate
        y_pred_proba = model.predict_proba(X)[:, 1]
        y_pred = model.predict(X)
        
        metrics = {
            'cv_auc_mean': float(np.nan_to_num(cv_scores.mean(), nan=0.5)),
            'cv_auc_std': float(np.nan_to_num(cv_scores.std(), nan=0.0)),
            'train_auc': self._safe_roc_auc(y, y_pred_proba),
            'train_precision': precision_score(y, y_pred, zero_division=0),
            'train_recall': recall_score(y, y_pred, zero_division=0),
            'train_f1': f1_score(y, y_pred, zero_division=0),
        }
        
        logger.info(f"XGBoost metrics: {metrics}")
        
        return model, metrics
    
    def train_lightgbm(self, X: pd.DataFrame, y: pd.Series) -> Tuple[lgb.LGBMClassifier, Dict[str, float]]:
        """Train LightGBM model."""
        logger.info("Training LightGBM model...")
        
        params = CONFIG['ml_pipeline']['models'][1]['hyperparameters']
        
        model = lgb.LGBMClassifier(
            max_depth=params['max_depth'],
            learning_rate=params['learning_rate'],
            n_estimators=params['n_estimators'],
            num_leaves=params['num_leaves'],
            random_state=42,
            verbose=-1
        )
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        try:
            cv_scores = cross_val_score(model, X, y, cv=tscv, scoring='roc_auc')
        except ValueError:
            logger.warning("Could not compute cross-validation scores (likely single class in split)")
            cv_scores = np.array([0.5])
        
        # Train on full data
        model.fit(X, y)
        
        # Evaluate
        y_pred_proba = model.predict_proba(X)[:, 1]
        y_pred = model.predict(X)
        
        metrics = {
            'cv_auc_mean': cv_scores.mean(),
            'cv_auc_std': cv_scores.std(),
            'train_auc': roc_auc_score(y, y_pred_proba),
            'train_precision': precision_score(y, y_pred),
            'train_recall': recall_score(y, y_pred),
            'train_f1': f1_score(y, y_pred),
        }
        
        logger.info(f"LightGBM metrics: {metrics}")
        
        return model, metrics
    
    def train_and_log(self, model_name: str = 'xgboost_churn'):
        """
        Train model and log to MLflow.
        
        Args:
            model_name: Name of the model to train
        """
        with mlflow.start_run():
            # Prepare data
            X, y = self.prepare_training_data()
            
            if len(X) == 0:
                logger.error("No training data available")
                return None
            
            # Train model
            if model_name == 'xgboost_churn':
                model, metrics = self.train_xgboost(X, y)
            elif model_name == 'lightgbm_churn':
                model, metrics = self.train_lightgbm(X, y)
            else:
                raise ValueError(f"Unknown model: {model_name}")
            
            # Log to MLflow
            mlflow.log_params({
                'model_name': model_name,
                'n_samples': len(X),
                'n_features': len(X.columns),
                'positive_class_ratio': y.mean(),
            })
            
            mlflow.log_metrics(metrics)
            
            # Log model (safely)
            try:
                mlflow.sklearn.log_model(model, "model")
            except Exception as e:
                logger.warning(f"Failed to log model to MLflow (likely artifact path issue): {e}")

            # Log feature importance
            if hasattr(model, 'feature_importances_'):
                feature_importance = dict(zip(X.columns, model.feature_importances_))
                try:
                    mlflow.log_dict(feature_importance, "feature_importance.json")
                except Exception as e:
                    logger.warning(f"Failed to log feature importance to MLflow: {e}")
            
            # Save model locally
            model_path = f"models/{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            import os
            os.makedirs('models', exist_ok=True)
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            logger.info(f"Model saved to {model_path}")
            logger.info(f"Model logged to MLflow run: {mlflow.active_run().info.run_id}")
            
            return model, metrics


def main():
    """Main training entry point."""
    trainer = ChurnModelTrainer()
    trainer.train_and_log('xgboost_churn')


if __name__ == '__main__':
    main()
