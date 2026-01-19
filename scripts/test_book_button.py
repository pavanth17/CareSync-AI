#!/usr/bin/env python3
"""
Test that the Book button fix is working:
1. Verify initializeButtonHandlers function is in template
2. Verify emergency fallback handler is in template
3. Verify DOMContentLoaded + window.load pattern is present
"""

import requests
import re

BASE_URL = "http://localhost:5000"

def test_book_button_handlers():
    """Test that button handlers are properly initialized"""
    
    print("=" * 70)
    print("TESTING BOOK BUTTON HANDLER FIX")
    print("=" * 70)
    
    # Fetch the discharged dashboard
    print("\n1. Fetching discharged dashboard...")
    try:
        # First login as discharged patient
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/login-discharged",
            data={'patient_id': 'PAT000001', 'password': 'password'},
            allow_redirects=True
        )
        
        dashboard_response = session.get(f"{BASE_URL}/discharged-dashboard")
        
        if dashboard_response.status_code != 200:
            print(f"✗ Failed to fetch dashboard: {dashboard_response.status_code}")
            return False
            
        html = dashboard_response.text
        print(f"✓ Dashboard loaded (Status: {dashboard_response.status_code}, Size: {len(html)} bytes)")
        
    except Exception as e:
        print(f"✗ Error fetching dashboard: {e}")
        return False
    
    # Test 1: Check for initializeButtonHandlers function
    print("\n2. Checking for initializeButtonHandlers function...")
    if "function initializeButtonHandlers()" in html:
        print("✓ Found: function initializeButtonHandlers()")
    else:
        print("✗ Missing: function initializeButtonHandlers()")
        return False
    
    # Test 2: Check for attachBookingFormHandler function
    print("\n3. Checking for attachBookingFormHandler function...")
    if "function attachBookingFormHandler()" in html:
        print("✓ Found: function attachBookingFormHandler()")
    else:
        print("✗ Missing: function attachBookingFormHandler()")
        return False
    
    # Test 3: Check for DOMContentLoaded listener
    print("\n4. Checking for DOMContentLoaded event listener...")
    if "document.addEventListener('DOMContentLoaded'" in html:
        print("✓ Found: DOMContentLoaded listener")
    else:
        print("✗ Missing: DOMContentLoaded listener")
        return False
    
    # Test 4: Check for window load listener
    print("\n5. Checking for window.load event listener...")
    if "window.addEventListener('load', initializeButtonHandlers)" in html:
        print("✓ Found: window.load listener for initializeButtonHandlers")
    else:
        print("✗ Missing: window.load listener for initializeButtonHandlers")
        return False
    
    # Test 5: Check for emergency fallback handler
    print("\n6. Checking for emergency fallback click handler...")
    if "document.addEventListener('click', function(e)" in html and "Emergency:" in html:
        print("✓ Found: Emergency fallback handler")
    else:
        print("✗ Missing: Emergency fallback handler")
        return False
    
    # Test 6: Check for openBookBtn handler
    print("\n7. Checking for openBookBtn handler with preventDefault...")
    if "openBookBtn.addEventListener('click'" in html and "e.preventDefault()" in html:
        print("✓ Found: openBookBtn handler with preventDefault")
    else:
        print("✗ Missing: openBookBtn handler with preventDefault")
        return False
    
    # Test 7: Check for console logging
    print("\n8. Checking for console.log debugging statements...")
    console_logs = re.findall(r"console\.(log|error)\(['\"]([^'\"]+)['\"]", html)
    if console_logs:
        print(f"✓ Found {len(console_logs)} console logging statements:")
        for level, msg in console_logs[:5]:  # Show first 5
            print(f"  - console.{level}(\"{msg}\")")
        if len(console_logs) > 5:
            print(f"  ... and {len(console_logs) - 5} more")
    else:
        print("⚠ No console logging found (but not critical)")
    
    # Test 8: Check for modal initialization
    print("\n9. Checking for Bootstrap Modal initialization...")
    if "new bootstrap.Modal" in html and "bookModal" in html:
        print("✓ Found: Bootstrap Modal initialization for bookModal")
    else:
        print("✗ Missing: Bootstrap Modal initialization")
        return False
    
    # Test 9: Verify oldString patterns are removed (no duplicate handlers)
    print("\n10. Checking for duplicate old handlers...")
    old_pattern_count = html.count("console.log('Attaching")
    if old_pattern_count == 0:
        print("✓ No duplicate old-style handlers found")
    else:
        print(f"⚠ Found {old_pattern_count} old-style handler attachments (may be duplicates)")
    
    # Test 10: Verify document.readyState check
    print("\n11. Checking for document.readyState check...")
    if "document.readyState === 'loading'" in html:
        print("✓ Found: document.readyState check for early initialization")
    else:
        print("✗ Missing: document.readyState check")
        return False
    
    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nNEXT STEPS:")
    print("1. Open browser to http://localhost:5000/discharged-portal")
    print("2. Login with patient_id='PAT000001' password='password'")
    print("3. In the chat page, click the 'Book' button")
    print("4. Should see: 'Book button CLICKED!' in browser DevTools (F12 → Console)")
    print("5. Should see: Modal appears on screen")
    print("\nIf button still doesn't work:")
    print("  - Open DevTools (F12)")
    print("  - Go to Console tab")
    print("  - Look for any red error messages")
    print("  - Check if 'Initializing button handlers...' appears")
    print("  - Click Book button and check console for '🔔 Book button CLICKED!'")
    
    return True

if __name__ == "__main__":
    success = test_book_button_handlers()
    exit(0 if success else 1)
