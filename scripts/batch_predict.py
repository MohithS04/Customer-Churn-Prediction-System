"""
Batch prediction script to populate ChurnPrediction and RetentionAction tables.
"""

from datetime import datetime, timezone
import random
from database import SessionLocal
from database.models import Customer, ChurnPrediction, RetentionAction
from features.feature_store import FeatureStore
from ml.model_loader import ModelLoader

def run_batch_predictions():
    print("Starting batch predictions...")
    db = SessionLocal()
    feature_store = FeatureStore()
    model_loader = ModelLoader()
    
    # Load model
    model = model_loader.get_active_model()
    if not model:
        print("❌ No model found! Please train a model first.")
        return

    # Get all customers
    customers = db.query(Customer).all()
    print(f"Found {len(customers)} customers.")
    
    predictions = []
    actions = []
    
    for customer in customers:
        try:
            # Get features
            features = feature_store.get_customer_features(customer.customer_id)
            
            # Predict
            result = model_loader.predict(model, features)
            
            # Create prediction record
            prediction = ChurnPrediction(
                prediction_id=None, # Auto-generated
                customer_id=customer.customer_id,
                prediction_timestamp=datetime.now(timezone.utc),
                churn_probability=result['churn_probability'],
                risk_level=result['risk_level'],
                prediction_horizon_days=30,
                model_version="xgboost_v1"
            )
            predictions.append(prediction)
            
            # Create retention action if high risk
            if result['risk_level'] in ['high', 'critical']:
                action_type = random.choice(['discount_offer', 'service_upgrade', 'priority_support'])
                action = RetentionAction(
                    action_id=None,
                    customer_id=customer.customer_id,
                    action_type=action_type,
                    recommended_at=datetime.now(timezone.utc),
                    status='pending',
                    predicted_impact=random.uniform(0.1, 0.4)
                )
                actions.append(action)
                
        except Exception as e:
            print(f"Error processing customer {customer.customer_id}: {e}")
            continue
            
    # Bulk save
    if predictions:
        print(f"Saving {len(predictions)} predictions...")
        db.bulk_save_objects(predictions)
    
    if actions:
        print(f"Saving {len(actions)} retention actions...")
        db.bulk_save_objects(actions)
        
    db.commit()
    print("✅ Batch predictions complete!")

if __name__ == "__main__":
    run_batch_predictions()
