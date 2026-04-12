"""
ColonscopyVideoSim_Demo_v0.py
-----------------------------
Main menu and launcher for the Endoscopy Multimedia Test suite.
- Lets user choose between video review, practice test, official test, and polyp mask creator.
- Uses OpenCV for a graphical menu interface.
- Launches each tool as a separate process or function.

Usage:
- Run this script to start the main menu.
- Use W/S to navigate, Enter to select, F for fullscreen, Q to quit.
"""

import cv2
import csv
import math
import numpy as np
# import matplotlib.pyplot as plt
from video_review import run_video_review
# from archive.mock_test import run_mock_test
# from perception_test_v2 import run_perception_test_v2 
import sys
from pathlib import Path

# ------------------------------------------------------
# INITIALIZATION SECTION - VIDEO AND DATA CONFIGURATION
# ------------------------------------------------------

# Font and display settings for overlays
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 0.7
font_thickness = 2
max_text_width = 500  # Adjusted to fit within 550px sidebar width

# Define base directory for relative paths
BASE_DIR = Path(__file__).parent

# Define file paths for video and overlay data using pathlib for cross-platform compatibility
video_path = BASE_DIR / "videos" / "Without annotations (edited).mp4"
# Uncomment to use the other video
# video_path = BASE_DIR / "videos" / "Subtle SSL unedited.mp4"
# Uncomment to use the original markers
# markers_path = BASE_DIR / "data" / "markers.csv"
# Uncomment to use perception markers V2
# markers_path = BASE_DIR / "data" / "perception_markers_V2.csv"
# markers_path = BASE_DIR / "data" / "lumen_markers_for_review.csv"  # Use lumen markers for mask video review, need to add the polyp dection window time windows for masks. 
# markers_path = BASE_DIR / "data" / "polyp_markers_for_video_review.csv"  # Use polyp markers for video review
# markers_path = BASE_DIR / "data" / "polyp_markers_detailed_review.csv"  # Use detailed polyp markers with review periods
# markers_path = BASE_DIR / "data" / "polyp_markers_fixed.csv"  # Use fixed polyp markers with proper sequential timing
markers_path = BASE_DIR / "data" / "polyp_markers_clean.csv"  # Use clean polyp markers (default)
questions_path = BASE_DIR / "data" / "questions.csv"  # Path to questions data

# Menu options defined globally
MENU_OPTIONS = [
    "Video Review (All Markers)",      # Original markers with all phases
    "Perception Test (Practice Mode)", # Practice mode
    "Official Test Mode",              # Official, linear test mode
    "Polyp Mask Creator",              # New: Mask creator tool
    "Exit"
]

def format_time(seconds):
    """Format seconds as MM:SS for display."""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"

def create_menu(selected_option):
    """
    Create the OpenCV menu image with options, descriptions, and instructions.
    Highlights the currently selected option.
    """
    # Get screen dimensions (using Tkinter for cross-platform)
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()
    except:
        screen_width = 1920
        screen_height = 1080

    # Calculate menu dimensions based on screen size
    menu_width = min(screen_width - 100, 1200)
    menu_height = min(screen_height - 100, 800)
    
    # Create menu image (black background)
    menu = np.zeros((menu_height, menu_width, 3), dtype=np.uint8)
    
    # Calculate scaling factors based on menu size
    title_scale = menu_width / 1200
    title_thickness = max(2, int(title_scale * 2))
    option_scale = title_scale * 0.8
    desc_scale = title_scale * 0.5
    instruction_scale = title_scale * 0.5
    
    # Define instructions list early
    instructions = [
        "Use W/S to navigate",
        "Press Enter to select",
        "Press F to toggle fullscreen",
        "Press Q to quit"
    ]
    
    # Calculate positions with proper spacing
    title_x = int(menu_width * 0.1)
    title_y = int(menu_height * 0.12)  # Moved up slightly
    
    # Main menu section (options and descriptions)
    option_x = int(menu_width * 0.15)
    option_y_start = int(menu_height * 0.25)  # Start options higher
    option_spacing = int(menu_height * 0.11)  # Slightly reduced spacing
    
    # Instructions section (moved to bottom)
    instruction_x = int(menu_width * 0.1)
    instruction_y_start = int(menu_height * 0.85)  # Keep instructions at bottom
    instruction_spacing = int(menu_height * 0.04)  # Reduced spacing between instructions

    # Draw title
    cv2.putText(menu, "Endoscopy Multimedia Test", (title_x, title_y),
                cv2.FONT_HERSHEY_SIMPLEX, title_scale, (255, 255, 255), title_thickness, cv2.LINE_AA)

    # Draw options with descriptions
    y_offset = option_y_start
    for i, option in enumerate(MENU_OPTIONS):
        # Draw the main option
        color = (0, 255, 255) if i == selected_option else (200, 200, 200)
        cv2.putText(menu, option, (option_x, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, option_scale, color, 2, cv2.LINE_AA)
        
        # Add description for each option
        desc_color = (150, 150, 150)
        if i == 0:
            desc = "Review all markers including polyp detection"
        elif i == 1:
            desc = "Practice mode: test perception and decision making with all features"
        elif i == 2:
            desc = "Official test mode: strict, linear test (no skipping, overlays, or debug)"
        elif i == 3:
            desc = "Create polyp masks for video review"
        else:
            desc = "Close the application"
            
        # Draw description with proper spacing
        desc_y = y_offset + int(menu_height * 0.035)  # Slightly reduced spacing
        cv2.putText(menu, desc, (option_x + 30, desc_y),
                    cv2.FONT_HERSHEY_SIMPLEX, desc_scale, desc_color, 1, cv2.LINE_AA)
        
        # Move to next option
        y_offset += option_spacing

    # Draw instructions in a box at the bottom
    box_padding = 10
    box_y_start = instruction_y_start - box_padding
    box_height = (len(instructions) * instruction_spacing) + (2 * box_padding)
    cv2.rectangle(menu, 
                 (instruction_x - box_padding, box_y_start),
                 (menu_width - instruction_x + box_padding, box_y_start + box_height),
                 (40, 40, 40), -1)  # Dark background for instructions

    # Draw instructions
    y_offset = instruction_y_start
    for instruction in instructions:
        cv2.putText(menu, instruction, (instruction_x, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, instruction_scale, (200, 200, 200), 1, cv2.LINE_AA)
        y_offset += instruction_spacing
        
    return menu

def main():
    """
    Main application loop for the menu.
    Handles user input, menu navigation, and launches the selected tool.
    """
    # Get screen dimensions for window sizing
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()
    except:
        screen_width = 1920
        screen_height = 1080

    # Calculate window size
    window_width = min(screen_width - 100, 1200)
    window_height = min(screen_height - 100, 800)

    # Create window
    cv2.namedWindow("Endoscopy Multimedia Test", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Endoscopy Multimedia Test", window_width, window_height)
    
    # Center window on screen
    window_x = (screen_width - window_width) // 2
    window_y = (screen_height - window_height) // 2
    cv2.moveWindow("Endoscopy Multimedia Test", window_x, window_y)

    selected_option = 0
    fullscreen = False
    
    while True:
        menu = create_menu(selected_option)
        cv2.imshow("Endoscopy Multimedia Test", menu)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('w'):  # Up
            selected_option = (selected_option - 1) % len(MENU_OPTIONS)
        elif key == ord('s'):  # Down
            selected_option = (selected_option + 1) % len(MENU_OPTIONS)
        elif key == ord('f'):  # Toggle fullscreen
            fullscreen = not fullscreen
            if fullscreen:
                cv2.setWindowProperty("Endoscopy Multimedia Test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            else:
                cv2.setWindowProperty("Endoscopy Multimedia Test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                cv2.resizeWindow("Endoscopy Multimedia Test", window_width, window_height)
                cv2.moveWindow("Endoscopy Multimedia Test", window_x, window_y)
        elif key == 13:  # Enter key
            # Launch the selected tool
            if selected_option == 0:  # Video Review (All Markers)
                run_video_review(str(video_path), str(markers_path), font, font_scale, font_thickness, max_text_width)
                run_video_review(str(video_path), str(BASE_DIR / "data" / "withdrawal_markers.csv"), font, font_scale, font_thickness, max_text_width)
            elif selected_option == 1:  # Perception Test (Practice Mode)
                from perception_test_practice_demo_v1 import run_perception_test
                run_perception_test()
            elif selected_option == 2:  # Official Test Mode
                from perception_test_official_demo_v1 import run_perception_test
                run_perception_test()
            elif selected_option == 3:  # Polyp Mask Creator
                import subprocess
                import sys
                subprocess.run([sys.executable, str(BASE_DIR / "mask_creator.py")])
            elif selected_option == 4:  # Exit
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()