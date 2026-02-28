"""Streamlit dashboard for churn prediction system."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import SessionLocal
from database.models import (
    Customer, ChurnPrediction, RetentionAction,
    CustomerServiceInteraction, BillingEvent
)
from features.feature_store import FeatureStore
from ml.model_loader import ModelLoader
import httpx

st.set_page_config(
    page_title="Churn Prediction Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize components
@st.cache_resource
def get_db():
    return SessionLocal()

@st.cache_resource
def get_feature_store():
    return FeatureStore()

@st.cache_resource
def get_model_loader():
    return ModelLoader()

db = get_db()
feature_store = get_feature_store()
model_loader = get_model_loader()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Select Page",
    ["Executive Dashboard", "Customer Risk Analysis", "Retention Campaigns", "Model Performance"]
)

# Executive Dashboard
if page == "Executive Dashboard":
    st.title("📊 Executive Dashboard")
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    # Total customers
    total_customers = db.query(Customer).count()
    col1.metric("Total Customers", f"{total_customers:,}")
    
    # High risk customers
    high_risk = db.query(ChurnPrediction).filter(
        ChurnPrediction.risk_level.in_(['high', 'critical'])
    ).count()
    col2.metric("High Risk Customers", f"{high_risk:,}", delta=f"{high_risk/total_customers*100:.1f}%")
    
    # Revenue at risk
    at_risk_customers = db.query(Customer).join(ChurnPrediction, Customer.customer_id == ChurnPrediction.customer_id).filter(
        ChurnPrediction.risk_level.in_(['high', 'critical'])
    ).all()
    revenue_at_risk = sum(c.monthly_recurring_revenue or 0 for c in at_risk_customers)
    col3.metric("Monthly Revenue at Risk", f"${revenue_at_risk:,.0f}")
    
    # Pending actions
    pending_actions = db.query(RetentionAction).filter(
        RetentionAction.status == 'pending'
    ).count()
    col4.metric("Pending Actions", f"{pending_actions:,}")
    
    # Charts
    col1, col2 = st.columns(2)
    
    # Churn risk distribution
    with col1:
        st.subheader("Churn Risk Distribution")
        predictions = db.query(ChurnPrediction).order_by(
            ChurnPrediction.prediction_timestamp.desc()
        ).limit(1000).all()
        
        if predictions:
            risk_counts = pd.Series([p.risk_level for p in predictions]).value_counts()
            fig = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title="Risk Level Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Churn probability distribution
    with col2:
        st.subheader("Churn Probability Distribution")
        if predictions:
            probs = [p.churn_probability for p in predictions]
            fig = px.histogram(
                x=probs,
                nbins=20,
                title="Churn Probability Histogram",
                labels={'x': 'Churn Probability', 'y': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent predictions table
    st.subheader("Recent High-Risk Predictions")
    recent_high_risk = db.query(ChurnPrediction).filter(
        ChurnPrediction.risk_level.in_(['high', 'critical'])
    ).order_by(ChurnPrediction.prediction_timestamp.desc()).limit(20).all()
    
    if recent_high_risk:
        df = pd.DataFrame([{
            'Customer ID': p.customer_id,
            'Churn Probability': f"{p.churn_probability:.2%}",
            'Risk Level': p.risk_level,
            'Prediction Time': p.prediction_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for p in recent_high_risk])
        st.dataframe(df, use_container_width=True)

# Customer Risk Analysis
elif page == "Customer Risk Analysis":
    st.title("🔍 Customer Risk Analysis")
    
    # Customer search
    customer_id = st.text_input("Enter Customer ID")
    
    if customer_id:
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        
        if customer:
            # Customer info
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Customer Information")
                st.write(f"**Segment:** {customer.customer_segment}")
                st.write(f"**MRR:** ${customer.monthly_recurring_revenue or 0:,.2f}")
                st.write(f"**LTV:** ${customer.lifetime_value or 0:,.2f}")
                st.write(f"**Tenure:** {(datetime.utcnow().date() - customer.account_created_date).days} days")
            
            with col2:
                st.subheader("Latest Prediction")
                latest_pred = db.query(ChurnPrediction).filter(
                    ChurnPrediction.customer_id == customer_id
                ).order_by(ChurnPrediction.prediction_timestamp.desc()).first()
                
                if latest_pred:
                    st.metric("Churn Probability", f"{latest_pred.churn_probability:.2%}")
                    st.metric("Risk Level", latest_pred.risk_level.upper())
                    st.write(f"**Predicted:** {latest_pred.prediction_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    st.info("No predictions available. Click 'Predict Now' to generate prediction.")
                    if st.button("Predict Now"):
                        with st.spinner("Generating prediction..."):
                            try:
                                features = feature_store.get_customer_features(customer_id)
                                model = model_loader.get_active_model()
                                if model:
                                    result = model_loader.predict(model, features)
                                    st.success(f"Churn Probability: {result['churn_probability']:.2%}")
                                    st.success(f"Risk Level: {result['risk_level']}")
                                else:
                                    st.error("Model not loaded")
                            except Exception as e:
                                st.error(f"Error: {e}")
            
            # Features
            st.subheader("Customer Features")
            features = feature_store.get_customer_features(customer_id)
            if features:
                features_df = pd.DataFrame([features]).T
                features_df.columns = ['Value']
                st.dataframe(features_df, use_container_width=True)
            
            # Service history
            st.subheader("Service Interaction History")
            interactions = db.query(CustomerServiceInteraction).filter(
                CustomerServiceInteraction.customer_id == customer_id
            ).order_by(CustomerServiceInteraction.timestamp.desc()).limit(10).all()
            
            if interactions:
                interactions_df = pd.DataFrame([{
                    'Date': i.timestamp.strftime('%Y-%m-%d %H:%M'),
                    'Channel': i.channel,
                    'Duration (min)': i.duration_seconds / 60 if i.duration_seconds else 0,
                    'Status': i.resolution_status,
                    'Sentiment': f"{i.sentiment_score:.2f}" if i.sentiment_score else "N/A"
                } for i in interactions])
                st.dataframe(interactions_df, use_container_width=True)
            else:
                st.info("No service interactions found")
        else:
            st.error(f"Customer {customer_id} not found")

# Retention Campaigns
elif page == "Retention Campaigns":
    st.title("🎯 Retention Campaigns")
    
    # Pending actions
    st.subheader("Pending Retention Actions")
    pending = db.query(RetentionAction).filter(
        RetentionAction.status == 'pending'
    ).order_by(RetentionAction.recommended_at.desc()).limit(50).all()
    
    if pending:
        actions_df = pd.DataFrame([{
            'Action ID': str(a.action_id),
            'Customer ID': a.customer_id,
            'Action Type': a.action_type,
            'Priority': 'High' if a.predicted_impact and a.predicted_impact > 0.2 else 'Medium',
            'Predicted Impact': f"{a.predicted_impact:.2%}" if a.predicted_impact else "N/A",
            'Recommended At': a.recommended_at.strftime('%Y-%m-%d %H:%M:%S')
        } for a in pending])
        st.dataframe(actions_df, use_container_width=True)
    else:
        st.info("No pending actions")
    
    # Campaign performance
    st.subheader("Campaign Performance")
    executed = db.query(RetentionAction).filter(
        RetentionAction.status == 'executed'
    ).count()
    rejected = db.query(RetentionAction).filter(
        RetentionAction.status == 'rejected'
    ).count()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Executed", executed)
    col2.metric("Rejected", rejected)
    col3.metric("Success Rate", f"{(executed/(executed+rejected)*100):.1f}%" if (executed+rejected) > 0 else "0%")

# Model Performance
elif page == "Model Performance":
    st.title("🤖 Model Performance")
    
    st.subheader("Model Information")
    model = model_loader.get_active_model()
    if model:
        st.success("✅ Model loaded successfully")
        st.write(f"**Model Type:** {type(model).__name__}")
    else:
        st.warning("⚠️ No model loaded")
    
    # Prediction statistics
    st.subheader("Prediction Statistics")
    total_predictions = db.query(ChurnPrediction).count()
    recent_predictions = db.query(ChurnPrediction).filter(
        ChurnPrediction.prediction_timestamp >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    col1, col2 = st.columns(2)
    col1.metric("Total Predictions", f"{total_predictions:,}")
    col2.metric("Predictions (Last 7 Days)", f"{recent_predictions:,}")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Churn Prediction System v1.0**")
st.sidebar.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
