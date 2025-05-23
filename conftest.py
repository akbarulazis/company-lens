import pytest

@pytest.fixture
def sample_data():
    return "Hello, World!"

def test_sample_data(sample_data):
    assert sample_data == "Hello, World!"