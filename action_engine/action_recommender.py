"""Retention action recommendation logic."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import SessionLocal
from database.models import Customer, RetentionAction
from config import CONFIG

logger = logging.getLogger(__name__)


class ActionRecommender:
    """Recommend retention actions based on churn risk."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.config = CONFIG['retention_actions']
    
    def recommend_actions(
        self,
        customer_id: str,
        churn_probability: float,
        risk_level: str
    ) -> List[Dict[str, Any]]:
        """
        Recommend retention actions for a customer.
        
        Args:
            customer_id: Customer identifier
            churn_probability: Predicted churn probability
            risk_level: Risk level (low, medium, high, critical)
            
        Returns:
            List of recommended actions
        """
        customer = self.db.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        
        if not customer:
            return []
        
        actions = []
        
        # Critical risk: Aggressive retention
        if risk_level == 'critical':
            actions.extend(self._get_critical_actions(customer, churn_probability))
        
        # High risk: Strong retention offers
        elif risk_level == 'high':
            actions.extend(self._get_high_risk_actions(customer, churn_probability))
        
        # Medium risk: Standard retention
        elif risk_level == 'medium':
            actions.extend(self._get_medium_risk_actions(customer, churn_probability))
        
        # Low risk: Light touch
        else:
            actions.extend(self._get_low_risk_actions(customer))
        
        # Sort by predicted impact
        actions.sort(key=lambda x: x.get('predicted_impact', 0), reverse=True)
        
        return actions[:3]  # Return top 3 recommendations
    
    def _get_critical_actions(self, customer: Customer, churn_prob: float) -> List[Dict[str, Any]]:
        """Get actions for critical risk customers."""
        actions = []
        
        # Immediate service call
        actions.append({
            'action_type': 'service_call',
            'priority': 'high',
            'description': 'Immediate proactive service call to address concerns',
            'predicted_impact': 0.25,
            'estimated_cost': 50,
            'offer_details': {
                'reason': 'Critical churn risk detected',
                'escalation': True
            }
        })
        
        # Significant discount
        if customer.monthly_recurring_revenue:
            discount_pct = min(25, churn_prob * 30)  # Up to 25% discount
            actions.append({
                'action_type': 'discount',
                'priority': 'high',
                'description': f'{discount_pct:.0f}% discount for 6 months',
                'predicted_impact': 0.30,
                'estimated_cost': customer.monthly_recurring_revenue * discount_pct / 100 * 6,
                'offer_details': {
                    'discount_percent': discount_pct,
                    'duration_months': 6,
                    'auto_apply': True
                }
            })
        
        # Loyalty reward
        if customer.lifetime_value and customer.lifetime_value > 1000:
            actions.append({
                'action_type': 'loyalty_reward',
                'priority': 'medium',
                'description': 'Exclusive loyalty reward for long-term customers',
                'predicted_impact': 0.15,
                'estimated_cost': 100,
                'offer_details': {
                    'reward_type': 'gift_card',
                    'amount': 100
                }
            })
        
        return actions
    
    def _get_high_risk_actions(self, customer: Customer, churn_prob: float) -> List[Dict[str, Any]]:
        """Get actions for high risk customers."""
        actions = []
        
        # Service call
        actions.append({
            'action_type': 'service_call',
            'priority': 'medium',
            'description': 'Proactive service check-in',
            'predicted_impact': 0.20,
            'estimated_cost': 30,
            'offer_details': {
                'reason': 'High churn risk',
                'escalation': False
            }
        })
        
        # Moderate discount
        if customer.monthly_recurring_revenue:
            discount_pct = min(15, churn_prob * 20)
            actions.append({
                'action_type': 'discount',
                'priority': 'high',
                'description': f'{discount_pct:.0f}% discount for 3 months',
                'predicted_impact': 0.25,
                'estimated_cost': customer.monthly_recurring_revenue * discount_pct / 100 * 3,
                'offer_details': {
                    'discount_percent': discount_pct,
                    'duration_months': 3
                }
            })
        
        # Upgrade offer
        if customer.customer_segment in ['residential', 'small_business']:
            actions.append({
                'action_type': 'upgrade',
                'priority': 'medium',
                'description': 'Upgrade to premium plan with special pricing',
                'predicted_impact': 0.18,
                'estimated_cost': 0,  # Revenue positive
                'offer_details': {
                    'upgrade_type': 'premium',
                    'special_pricing': True
                }
            })
        
        return actions
    
    def _get_medium_risk_actions(self, customer: Customer, churn_prob: float) -> List[Dict[str, Any]]:
        """Get actions for medium risk customers."""
        actions = []
        
        # Light discount
        if customer.monthly_recurring_revenue:
            discount_pct = min(10, churn_prob * 15)
            actions.append({
                'action_type': 'discount',
                'priority': 'medium',
                'description': f'{discount_pct:.0f}% discount for 2 months',
                'predicted_impact': 0.15,
                'estimated_cost': customer.monthly_recurring_revenue * discount_pct / 100 * 2,
                'offer_details': {
                    'discount_percent': discount_pct,
                    'duration_months': 2
                }
            })
        
        # Email campaign
        actions.append({
            'action_type': 'custom_offer',
            'priority': 'low',
            'description': 'Personalized retention email with special offer',
            'predicted_impact': 0.10,
            'estimated_cost': 5,
            'offer_details': {
                'channel': 'email',
                'personalized': True
            }
        })
        
        return actions
    
    def _get_low_risk_actions(self, customer: Customer) -> List[Dict[str, Any]]:
        """Get actions for low risk customers."""
        actions = []
        
        # Light engagement
        actions.append({
            'action_type': 'custom_offer',
            'priority': 'low',
            'description': 'Engagement email with tips and benefits',
            'predicted_impact': 0.05,
            'estimated_cost': 2,
            'offer_details': {
                'channel': 'email',
                'type': 'engagement'
            }
        })
        
        return actions
    
    def execute_action(self, action_id: str, customer_id: str) -> bool:
        """
        Execute a retention action.
        
        Args:
            action_id: Action identifier
            customer_id: Customer identifier
            
        Returns:
            True if successful
        """
        action = self.db.query(RetentionAction).filter(
            RetentionAction.action_id == action_id,
            RetentionAction.customer_id == customer_id
        ).first()
        
        if not action:
            logger.error(f"Action not found: {action_id}")
            return False
        
        if action.status != 'pending':
            logger.warning(f"Action already executed: {action_id}")
            return False
        
        # Update action status
        action.status = 'executed'
        action.executed_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Executed action {action_id} for customer {customer_id}")
        return True
