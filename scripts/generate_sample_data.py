"""Generate sample data for testing."""

import random
from datetime import datetime, timedelta, timezone
from faker import Faker
from database import SessionLocal
from database.models import Customer, CustomerServiceInteraction, BillingEvent
from ingestion.kafka_producer import (
    CustomerServiceEventProducer,
    BillingEventProducer
)

fake = Faker()
db = SessionLocal()


def generate_sample_customers(n: int = 100, force: bool = False):
    """Generate sample customer records."""
    # Check if customers already exist
    existing_count = db.query(Customer).count()
    if existing_count > 0 and not force:
        print(f"⚠️  {existing_count} customers already exist. Skipping customer generation.")
        print(f"   To regenerate, use: generate_sample_customers({n}, force=True)")
        return existing_count
    
    # Clear existing customers if force is True
    if force and existing_count > 0:
        print(f"🗑️  Clearing {existing_count} existing customers...")
        db.query(Customer).delete()
        db.commit()
    
    segments = ['residential', 'small_business', 'enterprise']
    age_ranges = ['18-25', '26-35', '36-45', '46-55', '56+']
    income_ranges = ['<30k', '30k-50k', '50k-75k', '75k-100k', '100k+']
    
    customers_to_add = []
    for i in range(n):
        created_date = fake.date_between(start_date='-2y', end_date='today')
        customer = Customer(
            customer_id=f"CUST{10000 + i:05d}",
            account_created_date=created_date,
            customer_segment=random.choice(segments),
            service_address_street=fake.street_address(),
            service_address_city=fake.city(),
            service_address_state=fake.state_abbr(),
            service_address_zip_code=fake.zipcode(),
            age_range=random.choice(age_ranges),
            household_size=random.randint(1, 5),
            estimated_income=random.choice(income_ranges),
            plan_id=f"PLAN{random.randint(1, 5)}",
            monthly_recurring_revenue=random.uniform(50, 200),
            contract_end_date=fake.date_between(start_date='today', end_date='+1y'),
            auto_renew=random.choice([True, False]),
            lifetime_value=random.uniform(500, 5000),
            churn_date=fake.date_between(start_date='-6m', end_date='today') if random.random() < 0.1 else None
        )
        customers_to_add.append(customer)
    
    # Bulk insert
    db.bulk_save_objects(customers_to_add)
    db.commit()
    print(f"✅ Generated {n} sample customers")
    return n


def generate_sample_interactions(n: int = 500):
    """Generate sample customer service interactions."""
    customers = db.query(Customer).all()
    if not customers:
        print("⚠️  No customers found. Please generate customers first.")
        return 0
    
    channels = ['phone', 'chat', 'email']
    statuses = ['resolved', 'escalated', 'unresolved']
    
    producer = CustomerServiceEventProducer()
    
    for i in range(n):
        customer = random.choice(customers)
        interaction = {
            'interaction_id': f"INT{fake.uuid4()}",
            'customer_id': customer.customer_id,
            'timestamp': (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))).isoformat(),
            'channel': random.choice(channels),
            'duration_seconds': random.randint(60, 1800),
            'reason_category': fake.word(),
            'resolution_status': random.choice(statuses),
            'agent_id': f"AGENT{random.randint(1, 50)}",
            'sentiment_score': random.uniform(-1.0, 1.0),
            'transfer_count': random.randint(0, 2)
        }
        producer.publish_interaction(interaction)
    
    print(f"✅ Generated {n} sample interactions")
    return n


def generate_sample_billing_events(n: int = 200):
    """Generate sample billing events."""
    customers = db.query(Customer).all()
    if not customers:
        print("⚠️  No customers found. Please generate customers first.")
        return 0
    
    event_types = ['payment_received', 'payment_failed', 'dispute_opened']
    payment_methods = ['credit_card', 'bank_transfer', 'auto_pay']
    
    producer = BillingEventProducer()
    
    for i in range(n):
        customer = random.choice(customers)
        event = {
            'event_type': random.choice(event_types),
            'customer_id': customer.customer_id,
            'timestamp': (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90))).isoformat(),
            'transaction_id': f"TXN{fake.uuid4()}",
            'amount': random.uniform(50, 200),
            'payment_method': random.choice(payment_methods),
            'billing_cycle_day': random.randint(1, 28),
            'account_balance': random.uniform(-100, 500),
            'days_overdue': random.randint(0, 30) if random.random() < 0.2 else 0
        }
        producer.publish_billing_event(event)
    
    print(f"✅ Generated {n} sample billing events")
    return n


if __name__ == '__main__':
    print("Generating sample data...")
    generate_sample_customers(100)
    generate_sample_interactions(500)
    generate_sample_billing_events(200)
    print("Sample data generation complete!")
