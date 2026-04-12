import cv2
import csv
import os
import numpy as np

# VIDEO_PATH = r"C:/Users/milan/OneDrive - Liverpool John Moores University/Colonscopy_VideoSim/videos/Subtle SSL unedited.mp4"  # Uncomment to use the other video
VIDEO_PATH = r"C:/Users/milan/OneDrive - Liverpool John Moores University/Colonscopy_VideoSim/videos/With annotations (edited).mp4"

# markers_for_review = "data/markers.csv"  # Uncomment to use the original markers
# markers_for_review = "data/perception_markers_V2.csv"  # Uncomment to use perception markers V2
# markers_for_review = "data/lumen_markers_for_review.csv"  # Use lumen markers for review
# markers_for_review = "data/polyp_markers_for_video_review.csv"  # Use polyp markers for review
# markers_for_review = "data/polyp_markers_detailed_review.csv"  # Use detailed polyp markers with review periods
markers_for_review = "data/polyp_markers_clean.csv"  # Use clean polyp markers (default)

def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"
# data/paul_markers_video_review.csv | "data/markers.csv
def run_video_review(video_path, markers_path="data/polyp_markers_clean.csv", font=None, font_scale=0.7, font_thickness=2, max_text_width=500):
    """Run the video review mode with markers
    
    Args:
        video_path: Path to the video file
        markers_path: Path to the markers file (default: data/markers.csv)
        font: Font to use for text (default: cv2.FONT_HERSHEY_SIMPLEX)
        font_scale: Scale of the font (default: 0.7)
        font_thickness: Thickness of the font (default: 2)
        max_text_width: Maximum width for text wrapping (default: 500)
    """
    if font is None:
        font = cv2.FONT_HERSHEY_SIMPLEX

    print("\nStarting video review...")
    print(f"Loading video from: {video_path}")
    print(f"Loading markers from: {markers_path}")
    
    # Create masks directory if it doesn't exist
    if not os.path.exists("data/masks"):
        os.makedirs("data/masks")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error opening video file")
        return

    # Get video properties first
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_delay = int(1000/fps)  # Convert fps to milliseconds
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    current_frame = 0
    last_frame_time = cv2.getTickCount()  # For timing

    # Load time markers with their durations
    time_markers = []
    try:
        with open(markers_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            header = next(reader, None)  # Skip header row
            print("\nReading markers from CSV:")
            for row in reader:
                if not row or row[0].strip().startswith('#') or not row[0].strip():
                    continue  # Skip comments and empty lines
                start_time = float(row[0])
                end_time = float(row[1])
                description = row[2]
                time_markers.append((start_time, end_time, description))
                print(f"Loaded marker: {start_time}-{end_time}: {description}")
    except FileNotFoundError:
        print(f"ERROR: Markers file not found: {markers_path}")
        return
    except Exception as e:
        print(f"ERROR reading markers file: {str(e)}")
        return

    if not time_markers:
        print("WARNING: No markers were loaded!")
        return

    # Sort markers by time
    time_markers.sort(key=lambda x: x[0])
    print("\nMarkers after sorting:")
    for i, (start, end, desc) in enumerate(time_markers):
        print(f"Marker {i}: {start}-{end}: {desc}")
    
    # Start at first marker and pause
    if time_markers:
        first_marker_time = time_markers[0][0]
        current_frame = int(first_marker_time * fps)
        print(f"\nStarting at first marker: {format_time(first_marker_time)}")
        print("Press Space to start playing")
        auto_play = False  # Start paused
    else:
        auto_play = True  # If no markers, just play normally

    # Get video properties
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Calculate window size (video + sidebar)
    sidebar_width = 0
    # Scale video to a reasonable size for most screens
    max_video_width = 1920
    if video_width > max_video_width:
        scale_factor = max_video_width / video_width
        video_width = max_video_width
        video_height = int(video_height * scale_factor)

    window_width = video_width + sidebar_width
    window_height = video_height

    # Create window with proper size
    cv2.namedWindow("Video Review", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Video Review", window_width, window_height)
    
    # Get screen size
    screen_width = 1920  # Default to 1080p
    screen_height = 1080
    try:
        # Try to get actual screen size
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()
    except:
        pass  # Use defaults if we can't get screen size

    # Center window on screen
    window_x = (screen_width - window_width) // 2
    window_y = (screen_height - window_height) // 2
    cv2.moveWindow("Video Review", window_x, window_y)

    # Initialize variables
    current_marker_index = 0 if time_markers else -1  # Start at first marker if available
    show_sidebar = True
    seamless_mode = True
    blend_mode = False  # New state variable for blend mode
    last_segment_frame = None  # Store last frame of current segment
    is_blending = False  # Flag to indicate we're in a blend transition
    blend_alpha = 0.0  # Current blend alpha value
    num_blend_frames = 15  # Number of frames to use for blending
    
    while True:
        # Calculate time since last frame
        current_time = cv2.getTickCount()
        elapsed = (current_time - last_frame_time) / cv2.getTickFrequency()
        
        # Only advance frame if auto_play is enabled and enough time has passed
        if auto_play and elapsed >= (1.0 / fps):
            current_frame += 1
            last_frame_time = current_time
        
        # Position video at current frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret:
            break

        # Resize frame to match our calculated dimensions
        frame = cv2.resize(frame, (video_width, video_height))

        # Handle blending if enabled
        if blend_mode and is_blending and last_segment_frame is not None:
            # Blend current frame with last segment frame
            frame = blend_frames(last_segment_frame, frame, blend_alpha)
            # Update blend alpha
            blend_alpha += 1.0 / num_blend_frames
            if blend_alpha >= 1.0:
                is_blending = False
                last_segment_frame = None
                blend_alpha = 0.0

        time_in_seconds = current_frame / fps
        frame_height, frame_width = frame.shape[:2]

        # Sidebar and menu are drawn directly on the video frame as before
        if show_sidebar:
            sidebar_width = 550
            frame_height, frame_width = frame.shape[:2]
            
            # Create sidebar background
            cv2.rectangle(frame, (0, 0), (sidebar_width, frame_height), (0, 0, 0), -1)
            
            # Draw menu in sidebar with clear sections
            def draw_menu(x, y):
                # Section 1: Menu Controls
                cv2.putText(frame, "Menu Controls", (x, y),
                            font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
                y += 25
                
                # Navigation controls
                nav_items = [
                    "N/P - Jump to Next/Previous Marker",
                    "W/S - Step Frame by Frame",
                    "Space - Start/Continue Playing"
                ]
                for item in nav_items:
                    cv2.putText(frame, item, (x, y),
                                font, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
                    y += 20
                
                y += 10  # Add some space
                
                # Mode controls
                mode_items = [
                    "B - Toggle Blend Mode",
                    "M - Toggle Seamless/Manual Mode",
                    "H - Hide/Show Info",
                    "C - Capture Video Frame",
                    "F - Toggle Fullscreen",
                    "Q - Quit"
                ]
                for item in mode_items:
                    cv2.putText(frame, item, (x, y),
                                font, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
                    y += 20
                
                y += 20  # Add space before mode indicators
                
                # Mode indicators
                mode_text = f"Mode: {'Seamless' if seamless_mode else 'Manual'}"
                cv2.putText(frame, mode_text, (x, y),
                            font, 0.6, (0, 255, 0) if seamless_mode else (0, 165, 255), 2, cv2.LINE_AA)
                y += 25
                blend_text = f"Blend Mode: {'ON' if blend_mode else 'OFF'}"
                cv2.putText(frame, blend_text, (x, y),
                            font, 0.6, (0, 255, 0) if blend_mode else (0, 165, 255), 2, cv2.LINE_AA)
                y += 25
                desc_items = [
                    "Starts paused at first marker",
                    "Auto-pauses at each marker (Manual)",
                    "Seamless skips between segments"
                ]
                for item in desc_items:
                    cv2.putText(frame, item, (x, y),
                                font, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
                    y += 20
                
                return y  # Return the final y position

            # Draw menu and get its height
            menu_end_y = draw_menu(350, 30)
            
            # Section 2: Marker Information (starts after menu)
            y_offset = menu_end_y + 40  # Add space after menu
            cv2.putText(frame, "Marker Information", (10, y_offset),
                        font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
            y_offset += 30
            
            # Find and display current marker
            current_marker_found = False
            for i, (start_time, end_time, description) in enumerate(time_markers):
                if start_time <= time_in_seconds <= end_time:
                    current_marker_found = True
                    current_marker_index = i
                    cv2.putText(frame, f"Marker {i+1}/{len(time_markers)}", (10, y_offset),
                                font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
                    y_offset += 30
                    time_textstart = format_time(start_time)
                    time_textend = format_time(end_time)
                    cv2.putText(frame, f"{time_textstart} – {time_textend}", (10, y_offset),
                                font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
                    y_offset += 30
                    wrapped_text = wrap_text(description, font, font_scale, font_thickness, max_text_width)
                    for line in wrapped_text:
                        cv2.putText(frame, line, (10, y_offset),
                                    font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
                        y_offset += 25
                    break
            
            if not current_marker_found:
                cv2.putText(frame, "No active marker", (10, y_offset),
                            font, font_scale, (200, 200, 200), font_thickness, cv2.LINE_AA)
                y_offset += 40
                next_marker = None
                for start_time, end_time, description in time_markers:
                    if start_time > time_in_seconds:
                        next_marker = (start_time, end_time, description)
                        break
                if next_marker:
                    time_text = format_time(next_marker[0])
                    cv2.putText(frame, f"Next marker at: {time_text}", (10, y_offset),
                                font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
                    y_offset += 30
                    cv2.putText(frame, "Press N to jump to next marker", (10, y_offset),
                                font, font_scale, (200, 200, 200), font_thickness, cv2.LINE_AA)
            
            # Section 3: Status (at the bottom)
            status_y = frame_height - 40
            time_text = format_time(time_in_seconds)
            frame_text = f"Frame: {current_frame}"
            ms_text = f"Time (ms): {time_in_seconds:.3f}"
            cv2.putText(frame, f"Time: {time_text}", (10, status_y),
                        font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
            cv2.putText(frame, frame_text, (10, status_y - 25),
                        font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
            cv2.putText(frame, ms_text, (10, status_y - 50),
                        font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
        # Display frame
        cv2.imshow("Video Review", frame)

        # Handle keyboard input with reduced delay when paused
        if auto_play:
            key = cv2.waitKey(frame_delay) & 0xFF
        else:
            # When paused, use a longer delay to reduce CPU usage
            key = cv2.waitKey(100) & 0xFF  # 100ms delay when paused

        if key == ord('q'):
            break
        elif key == ord('h'):
            show_sidebar = not show_sidebar
        elif key == ord('m'):
            seamless_mode = not seamless_mode
            print(f"\nMode toggled: {'Seamless' if seamless_mode else 'Manual'}")
        elif key == ord(' '):  # Space bar
            auto_play = not auto_play
            if not auto_play:
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            print("\nAuto-play:", "ON" if auto_play else "OFF")
        elif key == ord('w') and not auto_play:
            current_frame += 1
        elif key == ord('s') and not auto_play:
            current_frame -= 1
        elif key == ord('n') and current_marker_index + 1 < len(time_markers):
            current_marker_index += 1
            next_start, _, _ = time_markers[current_marker_index]
            current_frame = int(next_start * fps)
            last_frame_time = cv2.getTickCount()
            auto_play = False  # Pause at marker
            print(f"Jumped to marker {current_marker_index+1} at frame {current_frame}, time {next_start:.3f}s")
            # Immediately read and display the correct frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (video_width, video_height))
                # Redraw sidebar/menu if needed
                if show_sidebar:
                    sidebar_width = 550
                    frame_height, frame_width = frame.shape[:2]
                    cv2.rectangle(frame, (0, 0), (sidebar_width, frame_height), (0, 0, 0), -1)
                cv2.imshow("Video Review", frame)
        elif key == ord('p') and current_marker_index > 0:
            current_marker_index -= 1
            prev_start, _, _ = time_markers[current_marker_index]
            current_frame = int(prev_start * fps)
            last_frame_time = cv2.getTickCount()
            auto_play = False  # Pause at marker
            print(f"Jumped to marker {current_marker_index+1} at frame {current_frame}, time {prev_start:.3f}s")
            # Immediately read and display the correct frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (video_width, video_height))
                if show_sidebar:
                    sidebar_width = 550
                    frame_height, frame_width = frame.shape[:2]
                    cv2.rectangle(frame, (0, 0), (sidebar_width, frame_height), (0, 0, 0), -1)
                cv2.imshow("Video Review", frame)
        elif key == ord('c'):  # Capture video frame
            # Get current time for filename
            time_str = format_time(time_in_seconds).replace(':', '_')
            screenshot_path = f"data/masks/frame_{time_str}.png"
            
            # Extract only the video portion (right side of the frame)
            video_portion = frame  # Get everything after the sidebar
            
            # Save only the video portion
            cv2.imwrite(screenshot_path, video_portion)
            print(f"\nScreenshot saved: {screenshot_path}")
            print("Now you can:")
            print("1. Open this in GIMP")
            print("2. Create a new layer")
            print("3. Paint the polyp area white")
            print("4. Make background black")
            print("5. Save as mask in data/masks/")
            print("6. Update questions.csv to use: masks/frame_{time_str}_mask.png")
        elif key == ord('f'):  # Toggle fullscreen
            cv2.setWindowProperty("Video Review", cv2.WND_PROP_FULLSCREEN, 
                                cv2.WINDOW_FULLSCREEN if not cv2.getWindowProperty("Video Review", cv2.WND_PROP_FULLSCREEN) else cv2.WINDOW_NORMAL)
        elif key == ord('b'):  # Toggle blend mode
            blend_mode = not blend_mode
            print(f"\nBlend mode toggled: {'ON' if blend_mode else 'OFF'}")

    cap.release()
    cv2.destroyAllWindows()

def wrap_text(text, font, font_scale, thickness, max_width):
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        (w, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
        
        if w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
            
    if current_line:
        lines.append(current_line)
    return lines

def blend_frames(frame1, frame2, alpha):
    """Blend two frames using alpha blending"""
    return cv2.addWeighted(frame1, 1.0 - alpha, frame2, alpha, 0.0) 

if __name__ == '__main__':
    # Define the paths for the video and the markers file
    video_to_review = VIDEO_PATH
    # markers_for_review is now set above for easy switching
    
    # Check if the files exist before running
    if not os.path.exists(video_to_review):
        print(f"ERROR: Video file not found at {video_to_review}")
    elif not os.path.exists(markers_for_review):
        print(f"ERROR: Markers file not found at {markers_for_review}")
    else:
        # Run the video review function with the specified files
        run_video_review(video_to_review, markers_path=markers_for_review) 