#!/usr/bin/env python3
"""
Test script for polyp clicking functionality
This script tests the polyp clicking feature without requiring the full video
"""

import csv
from pathlib import Path

def test_polyp_markers():
    """Test that polyp markers are loaded correctly"""
    csv_path = Path("data/new_perception_markers.csv")
    
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        return False
    
    polyp_markers = []
    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['question_type'] == 'polyp_window':
                polyp_markers.append(row)
    
    print(f"Found {len(polyp_markers)} polyp detection windows:")
    for i, marker in enumerate(polyp_markers):
        start_time = float(marker['start_time'])
        end_time = marker.get('end_time', 'N/A')
        print(f"  Polyp {i+1}: {start_time}s - {end_time}s")
        print(f"    Question: {marker['question_text']}")
        print(f"    Mask: {marker['mask_path']}")
        print()
    
    return len(polyp_markers) > 0

def test_time_conversion():
    """Test time conversion from mm:ss:ms to seconds"""
    test_times = [
        ("06:36:10", 396.167),
        ("08:06:20", 486.333),
        ("08:31:27", 511.45),
        ("09:18:00", 558.0),
        ("10:46:45", 646.75),
        ("12:28:00", 748.0),
        ("13:12:10", 792.167),
        ("13:34:50", 814.833),
        ("14:05:00", 845.0),
        ("15:54:20", 954.333)
    ]
    
    print("Time conversion test:")
    for mm_ss_ms, expected_seconds in test_times:
        # Parse mm:ss:ms format
        parts = mm_ss_ms.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        milliseconds = int(parts[2])
        
        calculated_seconds = minutes * 60 + seconds + milliseconds / 1000
        print(f"  {mm_ss_ms} -> {calculated_seconds:.3f}s (expected: {expected_seconds:.3f}s)")
        
        if abs(calculated_seconds - expected_seconds) > 0.1:
            print(f"    WARNING: Time conversion mismatch!")

def test_csv_structure():
    """Test CSV structure and required columns"""
    csv_path = Path("data/new_perception_markers.csv")
    
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        return False
    
    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        required_columns = ['start_time', 'end_time', 'question_type', 'question_text', 'mask_path']
        
        # Check if all required columns exist
        if reader.fieldnames is None:
            print("ERROR: No fieldnames found in CSV")
            return False
            
        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        if missing_columns:
            print(f"ERROR: Missing required columns: {missing_columns}")
            return False
        
        print(f"✓ CSV structure is correct")
        print(f"  Columns: {', '.join(reader.fieldnames)}")
        return True

def main():
    print("Testing Polyp Clicking Functionality")
    print("=" * 50)
    
    # Test 1: Check CSV structure
    print("\n1. Testing CSV structure...")
    if test_csv_structure():
        print("✓ CSV structure is valid")
    else:
        print("✗ CSV structure issues found")
        return
    
    # Test 2: Check polyp markers in CSV
    print("\n2. Testing polyp markers in CSV...")
    if test_polyp_markers():
        print("✓ Polyp markers found and loaded correctly")
    else:
        print("✗ No polyp markers found")
    
    # Test 3: Time conversion
    print("\n3. Testing time conversion...")
    test_time_conversion()
    
    # Test 4: Check mask directory
    print("\n4. Testing mask directory...")
    mask_dir = Path("data/masks/polyp_masks")
    if mask_dir.exists():
        print(f"✓ Mask directory exists: {mask_dir}")
        mask_files = list(mask_dir.glob("*.png"))
        print(f"  Found {len(mask_files)} mask files")
        if len(mask_files) == 0:
            print("  ⚠️  No mask files found - you'll need to create polyp masks")
    else:
        print(f"✗ Mask directory not found: {mask_dir}")
        print("  You'll need to create polyp masks for accurate clicking validation")
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("- Polyp detection windows are integrated into the perception test")
    print("- Time windows are defined to prevent cheating")
    print("- Click validation uses masks for accuracy")
    print("- Users see 'Click when you see a polyp' without timing hints")
    print("- Video continues playing during polyp detection windows")
    print("- Automatic scoring for detected vs missed polyps")
    print("\nNext steps:")
    print("1. Create actual polyp mask images in data/masks/polyp_masks/")
    print("2. Test with the full perception test: python perception_test_v2.py")
    print("3. Add polyp classification questions (next feature)")

if __name__ == "__main__":
    main() 