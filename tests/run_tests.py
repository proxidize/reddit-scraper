import subprocess
import sys
import os


def run_command(cmd):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
        
    return result.returncode == 0


def main():
    print("Reddit Scraper Test Suite")
    print("=" * 50)
    
    if not os.path.exists('reddit_scraper'):
        print("ERROR: Run this script from the project root directory")
        sys.exit(1)
    
    print("\nInstalling test dependencies...")
    if not run_command([sys.executable, '-m', 'pip', 'install', '-e', '.[dev]']):
        print("ERROR: Failed to install dependencies")
        sys.exit(1)
    
    test_commands = [
        ([sys.executable, '-m', 'pytest', 'tests/unit/', '-v', '-m', 'unit'], 
         "Unit Tests"),
        
        ([sys.executable, '-m', 'pytest', 'tests/integration/', '-v', '-m', 'integration'],
         "Integration Tests"),
        
        ([sys.executable, '-m', 'pytest', 'tests/', '-v', '--cov=reddit_scraper'],
         "All Tests with Coverage"),
        
        ([sys.executable, '-m', 'pytest', 'tests/', '-v', '-m', 'not slow'],
         "Fast Tests Only"),
    ]
    
    results = {}
    
    for cmd, description in test_commands:
        print(f"\n{description}")
        print("-" * 30)
        success = run_command(cmd)
        results[description] = success
        
        if success:
            print(f"PASS: {description}")
        else:
            print(f"FAIL: {description}")
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {status}: {test_name}")
    
    if not all(results.values()):
        print("\nSome tests failed!")
        sys.exit(1)
    else:
        print("\nAll tests passed!")


if __name__ == '__main__':
    main()