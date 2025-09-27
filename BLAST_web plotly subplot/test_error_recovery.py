#!/usr/bin/env python
"""
Test error recovery system
"""

import sys
import os
sys.path.append(os.getcwd())

from app.logging.error_recovery import ErrorRecovery, ErrorType

def test_retry():
    """Test retry with backoff"""
    recovery = ErrorRecovery()
    
    attempt = 0
    def failing_function():
        nonlocal attempt
        attempt += 1
        print(f"Attempt {attempt}")
        if attempt < 3:
            raise ConnectionError("Simulated failure")
        return "Success!"
    
    print("Testing retry with backoff...")
    result = recovery.retry_with_backoff(failing_function, ErrorType.NETWORK)
    print(f"Result: {result}\n")
    
def test_circuit_breaker():
    """Test circuit breaker"""
    recovery = ErrorRecovery()
    
    print("Testing circuit breaker...")
    # Trigger many errors to open circuit
    for i in range(12):
        success = recovery.recover(
            Exception(f"Error {i}"),
            ErrorType.SERIAL_TIMEOUT
        )
        print(f"Recovery attempt {i+1}: {'Success' if success else 'Failed'}")
    
    print("\nCircuit should now be open")
    # Try one more - should fail immediately
    success = recovery.recover(
        Exception("Should fail immediately"),
        ErrorType.SERIAL_TIMEOUT
    )
    print(f"With open circuit: {'Success' if success else 'Failed (expected)'}")

if __name__ == "__main__":
    print("Error Recovery System Test")
    print("="*50)
    
    test_retry()
    test_circuit_breaker()
    
    print("\nTest complete!")