#!/usr/bin/env python3
"""
Polyp Frame Capture Guide
This script helps you use the polyp frame capture CSV with your video review tool
"""

import csv
from pathlib import Path

def print_capture_instructions():
    """Print instructions for capturing polyp frames"""
    print("=" * 60)
    print("POLYP FRAME CAPTURE GUIDE")
    print("=" * 60)
    
    csv_path = Path("data/polyp_frame_capture.csv")
    
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        return
    
    print("\n📋 CAPTURE WORKFLOW:")
    print("1. Use your video review tool to load the video")
    print("2. For each polyp below, jump to the 'best_frame_time'")
    print("3. Pause the video at that exact frame")
    print("4. Use the capture function to save the frame")
    print("5. Open the frame in GIMP to create the mask")
    print("6. Save the mask with the 'mask_filename'")
    
    print("\n🎯 POLYP FRAME CAPTURE LIST:")
    print("-" * 60)
    
    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            polyp_id = row['polyp_id']
            best_frame_time = float(row['best_frame_time'])
            description = row['description']
            capture_filename = row['capture_filename']
            mask_filename = row['mask_filename']
            
            # Convert seconds to mm:ss format
            minutes = int(best_frame_time // 60)
            seconds = int(best_frame_time % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            print(f"\nPolyp {polyp_id}:")
            print(f"  Time: {best_frame_time:.3f}s ({time_str})")
            print(f"  Description: {description}")
            print(f"  Capture as: {capture_filename}")
            print(f"  Save mask as: {mask_filename}")
    
    print("\n" + "=" * 60)
    print("📁 FILE ORGANIZATION:")
    print("Save captured frames to: data/masks/polyp_masks/")
    print("Save masks to: data/masks/polyp_masks/")
    print("\nExample:")
    print("  Frame: data/masks/polyp_masks/polyp_1_best_frame.png")
    print("  Mask:  data/masks/polyp_masks/polyp_1_best_frame_mask.png")
    
    print("\n🎨 MASK CREATION IN GIMP:")
    print("1. Open the captured frame in GIMP")
    print("2. Create a new layer")
    print("3. Paint the polyp area WHITE (255,255,255)")
    print("4. Make background BLACK (0,0,0)")
    print("5. Save as PNG with '_mask' suffix")
    print("6. Ensure mask is same size as video frames")
    
    print("\n✅ NEXT STEPS:")
    print("1. Capture all 10 polyp frames")
    print("2. Create masks in GIMP")
    print("3. Test the 2-point scoring system")
    print("4. Verify mask validation works correctly")

if __name__ == "__main__":
    print_capture_instructions() 