import os
import time
import sqlite3
from unittest.mock import patch, MagicMock

# Set custom database for testing to avoid overwriting production cache
TEST_DB = "test_openf1_cache.db"
os.environ["OPENF1_CACHE_DB"] = TEST_DB

# Ensure clean test DB
if os.path.exists(TEST_DB):
    try:
        os.remove(TEST_DB)
    except OSError:
        pass

import openf1_client

def run_tests():
    print("Starting OpenF1 Cache and Rate Limiter Tests...")
    
    # 1. Test database initialization
    assert os.path.exists(TEST_DB), "Test SQLite database should be created"
    
    # 2. Test cache write & read
    path = "sessions"
    params = {"year": 2023}
    mock_payload = [{"session_key": 9000, "session_name": "Test Practice", "year": 2023}]
    
    with patch('openf1_client._session.get') as mock_get:
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_payload
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # First request (should go to API)
        print("Executing first request (should call live API/mock)...")
        res1 = openf1_client._request(path, params)
        assert res1 == mock_payload
        assert mock_get.call_count == 1, "API should be called once"
        
        # Second request (should hit cache, no API call)
        print("Executing second request (should load from cache)...")
        res2 = openf1_client._request(path, params)
        assert res2 == mock_payload
        assert mock_get.call_count == 1, "API should NOT be called again (cache hit)"
        
    # 3. Test rate limiter
    print("Testing rate limiter behavior...")
    
    # Insert 30 dummy requests in the last hour
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    now = time.time()
    for i in range(30):
        cursor.execute("INSERT INTO request_log (timestamp) VALUES (?)", (now - i * 10,))
    conn.commit()
    conn.close()
    
    # Check that rate limiter refuses requests
    assert not openf1_client.check_rate_limit(), "Rate limit check should return False (limit exceeded)"
    
    try:
        # A new path to guarantee cache miss
        openf1_client._request("drivers", {"session_key": 9000})
        assert False, "Should have raised RuntimeError due to rate limit"
    except RuntimeError as e:
        print(f"Correctly caught rate limit exception: {e}")
        assert "rate limit" in str(e).lower()
        
    # Clean up test DB
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except OSError:
            pass
        
    print("\nAll Tests Passed Successfully!")

if __name__ == "__main__":
    run_tests()
