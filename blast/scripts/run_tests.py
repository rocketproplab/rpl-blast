#!/usr/bin/env python3
"""Test runner script for BLAST application"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle the result"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
        else:
            print(f"❌ {description} failed with exit code {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False


def main():
    """Main test runner"""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    python_exe = "/Users/andrewyang/miniconda3/envs/RPL/bin/python"
    
    print("🚀 BLAST Test Suite Runner")
    print(f"📁 Working directory: {project_root}")
    
    # Test categories to run
    test_categories = [
        {
            "name": "Unit Tests (Models & Core)",
            "cmd": [python_exe, "-m", "pytest", "tests/test_sensor_models.py", "tests/test_calibration_models.py", "tests/test_config.py", "-v"],
            "required": True
        },
        {
            "name": "Service Tests",
            "cmd": [python_exe, "-m", "pytest", "tests/test_calibration_service.py", "tests/test_data_sources.py", "-v"],
            "required": True
        },
        {
            "name": "WebSocket Tests",
            "cmd": [python_exe, "-m", "pytest", "tests/test_websocket.py", "-v"],
            "required": False
        },
        {
            "name": "Backend Integration Tests",
            "cmd": [python_exe, "-m", "pytest", "tests/test_backend_services.py", "-v", "-k", "not test_health_endpoint"],
            "required": False
        },
        {
            "name": "Security Tests",
            "cmd": [python_exe, "-m", "pytest", "tests/test_security.py", "-v", "--tb=short"],
            "required": False
        },
        {
            "name": "Performance Tests",
            "cmd": [python_exe, "-m", "pytest", "tests/test_performance.py", "-v", "--tb=short", "-k", "not test_memory"],
            "required": False
        }
    ]
    
    # Summary tracking
    results = {}
    total_passed = 0
    total_failed = 0
    
    for category in test_categories:
        success = run_command(category["cmd"], category["name"])
        results[category["name"]] = success
        
        if success:
            total_passed += 1
        else:
            total_failed += 1
            if category["required"]:
                print(f"❌ Required test category '{category['name']}' failed!")
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    
    for name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nOverall: {total_passed} passed, {total_failed} failed")
    
    # Generate simple coverage report
    print(f"\n{'='*60}")
    print("📈 GENERATING COVERAGE REPORT")
    print('='*60)
    
    coverage_cmd = [python_exe, "-m", "pytest", "tests/test_sensor_models.py", "tests/test_calibration_models.py", "--cov=app", "--cov-report=term-missing", "--cov-report=html:htmlcov"]
    run_command(coverage_cmd, "Coverage Report Generation")
    
    # Exit with appropriate code
    if total_failed == 0:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_failed} test categories failed")
        sys.exit(1)


if __name__ == "__main__":
    main()