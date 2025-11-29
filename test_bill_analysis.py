"""Test bill analysis locally before pushing."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from orchestrator.adk_orchestrator import EnergyAgentOrchestrator

def test_bill_analysis():
    """Test the bill analysis with sample data."""
    print("=" * 60)
    print("Testing Bill Analysis Locally")
    print("=" * 60)
    
    # Initialize orchestrator
    print("\n1. Initializing orchestrator...")
    try:
        orchestrator = EnergyAgentOrchestrator()
        print("   ✓ Orchestrator initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return False
    
    # Check sample bill exists
    print("\n2. Checking sample bill...")
    bill_path = Path("data/raw/sample_bill_1.txt")
    if not bill_path.exists():
        print(f"   ✗ Sample bill not found: {bill_path}")
        return False
    print(f"   ✓ Found: {bill_path}")
    
    # Read bill content
    print("\n3. Reading bill content...")
    bill_content = bill_path.read_text(encoding='utf-8')
    print(f"   ✓ Read {len(bill_content)} characters")
    print(f"   Preview: {bill_content[:100]}...")
    
    # Test analyze_bill with path
    print("\n4. Testing analyze_bill with bill_path...")
    try:
        result = orchestrator.analyze_bill(bill_path=str(bill_path))
        print("   ✓ Analysis completed successfully!")
        print(f"   Result keys: {list(result.keys())}")
        return True
    except Exception as e:
        print(f"   ✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bill_analysis()
    print("\n" + "=" * 60)
    if success:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ TESTS FAILED")
    print("=" * 60)
