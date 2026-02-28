"""
Populate database tables directly, bypassing Kafka.
Used for testing/demos when streaming infrastructure is bypassed.
"""

from datetime import datetime, timedelta, timezone
import random
from faker import Faker
from database import SessionLocal
from database.models import (
    Customer, 
    CustomerServiceInteraction, 
    BillingEvent,
    STBTelemetry,
    WebAnalyticsEvent
)

fake = Faker()
db = SessionLocal()

def populate_interactions(n=500):
    print(f"Generating {n} interactions directly to DB...")
    customers = db.query(Customer).all()
    if not customers:
        print("No customers found!")
        return

    channels = ['phone', 'chat', 'email']
    statuses = ['resolved', 'escalated', 'unresolved']
    
    interactions = []
    for _ in range(n):
        customer = random.choice(customers)
        interaction = CustomerServiceInteraction(
            interaction_id=fake.uuid4(),
            customer_id=customer.customer_id,
            timestamp=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
            channel=random.choice(channels),
            duration_seconds=random.randint(60, 1800),
            reason_category=fake.word(),
            resolution_status=random.choice(statuses),
            agent_id=f"AGENT{random.randint(1, 50)}",
            sentiment_score=random.uniform(-1.0, 1.0),
            transfer_count=random.randint(0, 2),
            transcript_text=fake.text()
        )
        interactions.append(interaction)
    
    db.bulk_save_objects(interactions)
    db.commit()
    print("✅ Interactions populated.")

def populate_billing(n=200):
    print(f"Generating {n} billing events directly to DB...")
    customers = db.query(Customer).all()
    if not customers:
        return

    event_types = ['payment_received', 'payment_failed', 'dispute_opened']
    payment_methods = ['credit_card', 'bank_transfer', 'auto_pay']
    
    events = []
    for _ in range(n):
        customer = random.choice(customers)
        event = BillingEvent(
            event_id=fake.uuid4(),
            event_type=random.choice(event_types),
            customer_id=customer.customer_id,
            timestamp=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90)),
            transaction_id=f"TXN{fake.uuid4()}",
            amount=random.uniform(50, 200),
            payment_method=random.choice(payment_methods),
            billing_cycle_day=random.randint(1, 28),
            account_balance=random.uniform(-100, 500),
            days_overdue=random.randint(0, 30) if random.random() < 0.2 else 0
        )
        events.append(event)
        
    db.bulk_save_objects(events)
    db.commit()
    print("✅ Billing events populated.")

if __name__ == "__main__":
    populate_interactions(1000)
    populate_billing(500)
