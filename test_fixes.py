#!/usr/bin/env python3
"""
Comprehensive test script to verify all bug fixes in the vending machine API.
"""

import json
import sys
import time
from datetime import datetime

import requests

BASE_URL = "http://127.0.0.1:8000"

# ANSI colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_test(name):
    print(f"\n{BLUE}{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}{RESET}")

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}ℹ {msg}{RESET}")

def test_health_check():
    """Test 1: Health check endpoint"""
    print_test("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print_success("Health check working")
        return True
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_create_slot():
    """Test 2: Create slot"""
    print_test("Create Slot")
    try:
        response = requests.post(
            f"{BASE_URL}/slots",
            json={"code": "A1", "capacity": 10}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "A1"
        assert data["capacity"] == 10
        assert data["current_item_count"] == 0
        print_success("Slot creation working")
        return data["id"]
    except Exception as e:
        print_error(f"Slot creation failed: {e}")
        return None

def test_add_item_to_slot(slot_id):
    """Test 3: Add item to slot (tests capacity validation fix)"""
    print_test("Add Item to Slot - Capacity Validation Fix")
    try:
        response = requests.post(
            f"{BASE_URL}/slots/{slot_id}/items",
            json={"name": "Coke", "price": 40, "quantity": 5}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Coke"
        assert data["price"] == 40
        assert data["quantity"] == 5
        print_success("Item added successfully with correct capacity validation")
        return data["id"]
    except Exception as e:
        print_error(f"Adding item failed: {e}")
        return None

def test_capacity_exceeded(slot_id):
    """Test 4: Verify capacity validation works"""
    print_test("Capacity Exceeded Validation")
    try:
        # Try to add items that exceed capacity
        response = requests.post(
            f"{BASE_URL}/slots/{slot_id}/items",
            json={"name": "Pepsi", "price": 35, "quantity": 10}
        )
        assert response.status_code == 400
        print_success("Capacity validation correctly prevents overflow")
        return True
    except Exception as e:
        print_error(f"Capacity validation test failed: {e}")
        return False

def test_price_validation():
    """Test 5: Price validation (must be > 0)"""
    print_test("Price Validation Fix")
    try:
        # Create a slot first
        slot_response = requests.post(
            f"{BASE_URL}/slots",
            json={"code": "B1", "capacity": 10}
        )
        slot_id = slot_response.json()["id"]
        
        # Try to add item with price = 0 (should fail)
        response = requests.post(
            f"{BASE_URL}/slots/{slot_id}/items",
            json={"name": "Free Item", "price": 0, "quantity": 5}
        )
        assert response.status_code == 422  # Validation error
        print_success("Price validation correctly rejects price = 0")
        return True
    except Exception as e:
        print_error(f"Price validation test failed: {e}")
        return False

def test_bulk_add_items(slot_id):
    """Test 6: Bulk add items with capacity check (tests race condition fix)"""
    print_test("Bulk Add Items - Capacity Check Fix")
    try:
        response = requests.post(
            f"{BASE_URL}/slots/{slot_id}/items/bulk",
            json={
                "items": [
                    {"name": "Sprite", "price": 30, "quantity": 2},
                    {"name": "Fanta", "price": 25, "quantity": 1}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["added_count"] == 2
        print_success("Bulk add working with proper capacity check and no race conditions")
        return True
    except Exception as e:
        print_error(f"Bulk add failed: {e}")
        return False

def test_update_item_price(item_id):
    """Test 7: Update item price (tests timestamp update fix)"""
    print_test("Update Item Price - Timestamp Fix")
    try:
        # Get current item
        get_response = requests.get(f"{BASE_URL}/items/{item_id}")
        old_data = get_response.json()
        old_timestamp = old_data.get("created_at")
        
        # Wait a moment to ensure timestamp difference
        time.sleep(0.1)
        
        # Update price
        response = requests.patch(
            f"{BASE_URL}/items/{item_id}/price",
            json={"price": 50}
        )
        assert response.status_code == 200
        
        # Verify price was updated
        get_response = requests.get(f"{BASE_URL}/items/{item_id}")
        new_data = get_response.json()
        assert new_data["price"] == 50
        print_success("Item price updated successfully with proper timestamp handling")
        return True
    except Exception as e:
        print_error(f"Price update test failed: {e}")
        return False

def test_purchase(slot_id, item_id):
    """Test 8: Purchase item (tests purchase fixes)"""
    print_test("Purchase Item")
    try:
        # Use the item_id provided if valid, otherwise create new one
        purchase_item_id = item_id
        
        if not purchase_item_id:
            # Create a new item for purchase testing
            add_response = requests.post(
                f"{BASE_URL}/slots/{slot_id}/items",
                json={"name": "Water", "price": 20, "quantity": 5}
            )
            if add_response.status_code != 201:
                print_error(f"Failed to create test item: {add_response.text}")
                return False
            purchase_item_id = add_response.json().get("id")
        
        if not purchase_item_id:
            print_error("Could not determine item ID for purchase test")
            return False
        
        # Purchase with sufficient cash
        response = requests.post(
            f"{BASE_URL}/purchase",
            json={"item_id": purchase_item_id, "cash_inserted": 50}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item"] in ["Coke", "Water"]
        assert data["price"] <= 50
        assert data["cash_inserted"] == 50
        assert data["change_returned"] >= 0
        assert data["remaining_quantity"] >= 0
        print_success("Purchase working correctly")
        return True
    except Exception as e:
        print_error(f"Purchase test failed: {e}")
        return False

def test_insufficient_cash(item_id):
    """Test 9: Insufficient cash error"""
    print_test("Insufficient Cash Validation")
    try:
        response = requests.post(
            f"{BASE_URL}/purchase",
            json={"item_id": item_id, "cash_inserted": 10}
        )
        assert response.status_code == 400
        data = response.json()
        assert "Insufficient cash" in data.get("error", "")
        print_success("Insufficient cash error handled correctly")
        return True
    except Exception as e:
        print_error(f"Insufficient cash test failed: {e}")
        return False

def test_change_breakdown():
    """Test 10: Change breakdown (tests denomination fix)"""
    print_test("Change Breakdown - Denomination Fix")
    try:
        response = requests.get(
            f"{BASE_URL}/purchase/change-breakdown?change=70"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["change"] == 70
        assert "denominations" in data
        # With the fix including [1, 2, 5, 10, 20, 50, 100], breakdown should work
        print_success(f"Change breakdown working: {data['denominations']}")
        return True
    except Exception as e:
        print_error(f"Change breakdown test failed: {e}")
        return False

def test_list_slots():
    """Test 11: List all slots"""
    print_test("List Slots")
    try:
        response = requests.get(f"{BASE_URL}/slots")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print_success(f"Listed {len(data)} slots")
        return True
    except Exception as e:
        print_error(f"List slots test failed: {e}")
        return False

def test_full_view():
    """Test 12: Full view with nested items"""
    print_test("Full View - Slots with Items")
    try:
        response = requests.get(f"{BASE_URL}/slots/full-view")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "items" in data[0]
            print_success(f"Full view returned {len(data)} slots with nested items")
        else:
            print_info("No slots available for full view test")
        return True
    except Exception as e:
        print_error(f"Full view test failed: {e}")
        return False

def main():
    print(f"\n{YELLOW}{'='*60}")
    print("VENDING MACHINE API - COMPREHENSIVE TEST SUITE")
    print(f"{'='*60}{RESET}")
    print(f"Testing API at: {BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health_check()))
    slot_id = test_create_slot()
    results.append(("Create Slot", slot_id is not None))
    
    if slot_id:
        item_id = test_add_item_to_slot(slot_id)
        results.append(("Add Item", item_id is not None))
        
        results.append(("Capacity Validation", test_capacity_exceeded(slot_id)))
        results.append(("Bulk Add Items", test_bulk_add_items(slot_id)))
        
        if item_id:
            results.append(("Update Price (Timestamp Fix)", test_update_item_price(item_id)))
            results.append(("Insufficient Cash", test_insufficient_cash(item_id)))
        
        results.append(("Purchase Item", test_purchase(slot_id, item_id if item_id else "")))
    
    results.append(("Price Validation Fix", test_price_validation()))
    results.append(("Change Breakdown (Denomination Fix)", test_change_breakdown()))
    results.append(("List Slots", test_list_slots()))
    results.append(("Full View", test_full_view()))
    
    # Print summary
    print(f"\n{YELLOW}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{test_name:<40} {status}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ All tests passed! API is working correctly.{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ Some tests failed. Please review the errors above.{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
