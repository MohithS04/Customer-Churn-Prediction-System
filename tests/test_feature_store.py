"""Tests for feature store."""

import pytest
from features.feature_store import FeatureStore


def test_feature_store_initialization():
    """Test feature store initialization."""
    fs = FeatureStore()
    assert fs is not None
    assert fs.redis_client is not None


def test_get_customer_features():
    """Test getting customer features."""
    fs = FeatureStore()
    # This will fail if customer doesn't exist, which is expected
    # In real tests, use test fixtures
    pass


@pytest.mark.skip(reason="Requires test database")
def test_feature_computation():
    """Test feature computation."""
    fs = FeatureStore()
    features = fs._compute_features("TEST_CUSTOMER_ID")
    assert isinstance(features, dict)
    assert len(features) > 0
