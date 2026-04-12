import cv2
import csv
import math

def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"

class Question:
    def __init__(self, time, question_text, options, correct_answer, correct_location=None, mask_path=None):
        self.time = float(time)
        self.question_text = question_text
        self.options = options
        self.correct_answer = correct_answer
        self.correct_location = correct_location
        self.mask = None
        self.display_mask = None  # Add this line to store the display mask
        self.mask_path = mask_path  # Path to mask image if using detection
        self.answered = False
        self.multiple_choice_answered = False
        self.click_answered = False
        if mask_path:
            try:
                self.mask = cv2.imread(mask_path)
                if self.mask is None:
                    print(f"Warning: Could not load mask image: {mask_path}")
            except Exception as e:
                print(f"Error loading mask image: {e}")

def run_mock_test(video_path, questions_path, font, font_scale, font_thickness, max_text_width):
    """Run the mock test mode with questions"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error opening video file")
        return

    # Get video properties first
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_delay = int(1000/fps)  # Convert fps to milliseconds
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    current_frame = 0
    last_frame_time = cv2.getTickCount()  # For timing

    # Calculate window size (video + sidebar)
    sidebar_width = 350  # Keep sidebar compact
    
    # Get screen size for better scaling
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

    # Calculate optimal video size - make it much larger for better quality
    # Use 90% of available screen space
    max_video_width = min(original_width, int((screen_width - sidebar_width) * 0.95))  # Use 95% of available width
    max_video_height = min(original_height, int(screen_height * 0.95))  # Use 95% of available height

    # Calculate scale factors while maintaining aspect ratio
    width_scale = max_video_width / original_width
    height_scale = max_video_height / original_height
    scale_factor = min(width_scale, height_scale)  # Use the smaller scale to fit both dimensions

    # Calculate final video dimensions
    video_width = int(original_width * scale_factor)
    video_height = int(original_height * scale_factor)

    window_width = video_width + sidebar_width
    window_height = video_height

    # Adjust text sizes for more compact display but keep readable
    question_font_scale = 0.65  # Slightly increased from 0.6 for better readability
    option_font_scale = 0.65    # Slightly increased from 0.6 for better readability
    control_font_scale = 0.55   # Slightly increased from 0.5 for better readability
    status_font_scale = 0.55    # Slightly increased from 0.5 for better readability

    # Create window with proper size
    cv2.namedWindow("Mock Test", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Mock Test", window_width, window_height)
    
    # Center window on screen
    window_x = (screen_width - window_width) // 2
    window_y = (screen_height - window_height) // 2
    cv2.moveWindow("Mock Test", window_x, window_y)

    # Question handling variables
    current_question = None
    questions = []
    user_answer = None
    answer_feedback = None
    feedback_timer = 0
    click_answer = None
    click_feedback = None
    question_state = "multiple_choice"  # States: "multiple_choice", "click", "completed"
    mouse_x, mouse_y = 0, 0
    auto_play = False  # Start paused
    show_answers = False
    show_sidebar = True  # Add sidebar toggle
    feedback_display_time = 100  # Frames to show feedback
    show_mouse_coords = True  # Always show mouse coordinates
    number_buffer = ''  # For multi-digit question jump

    # Load questions
    try:
        with open(questions_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 6:
                    time = row[0]
                    question = row[1]
                    options = {
                        'A': row[2],
                        'B': row[3],
                        'C': row[4],
                        'D': row[5]
                    }
                    correct_answer = row[6]
                    correct_location = None
                    mask_path = None
                    
                    if len(row) >= 8:
                        if row[7].strip() and row[7] != "No location needed":
                            if row[7].endswith('.png'):  # If it's a mask image
                                mask_path = row[7]
                                correct_location = row[7]
                            else:  # Otherwise it's coordinates
                                correct_location = row[7]
                    
                    questions.append(Question(time, question, options, correct_answer, 
                                           correct_location, mask_path))
    except FileNotFoundError:
        print(f"Questions file not found: {questions_path}")
        return

    # Sort questions by time
    questions.sort(key=lambda x: x.time)

    # Start at first question
    if questions:
        current_question = questions[0]
        current_frame = int(current_question.time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        auto_play = False
        question_state = "multiple_choice"

    # Create black sidebar for information
    def create_sidebar(frame):
        frame_height, frame_width = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (sidebar_width, frame_height), (0, 0, 0), -1)  # Use sidebar_width instead of hardcoded 500
        return frame

    # Mouse callback
    def mouse_callback(event, x, y, flags, param):
        nonlocal mouse_x, mouse_y, click_answer, click_feedback, current_question, question_state, auto_play, current_frame
        if event == cv2.EVENT_MOUSEMOVE:
            mouse_x, mouse_y = x, y
        elif event == cv2.EVENT_LBUTTONDOWN and current_question and question_state == "click":
            if sidebar_width <= x <= window_width:
                click_answer = (x, y)
                print(f"\nClick detected at ({x}, {y})")
                
                if current_question.correct_location:
                    if current_question.correct_location == "Click required":
                        # For click-required questions, any click in the video area is accepted
                        current_question.click_answered = True
                        current_question.answered = True
                        question_state = "completed"
                        click_feedback = "Correct! Moving to next question..."
                        feedback_timer = feedback_display_time
                        
                        # Find and jump to next question
                        current_idx = questions.index(current_question)
                        if current_idx < len(questions) - 1:
                            next_q = questions[current_idx + 1]
                            current_frame = int(next_q.time * fps)
                            current_question = next_q
                            question_state = "multiple_choice"
                            answer_feedback = None
                            click_feedback = None
                            auto_play = False  # Pause at next question
                        else:
                            print("This was the last question!")
                            auto_play = True  # Continue if it was the last question
                    else:
                        # Check using either mask or rectangle
                        is_correct, feedback = check_click_answer(
                            (x, y), 
                            current_question.correct_location,
                            current_question.display_mask if current_question.display_mask is not None else current_question.mask
                        )
                        if is_correct:
                            current_question.click_answered = True
                            current_question.answered = True
                            question_state = "completed"
                            click_feedback = "Correct! Moving to next question..."
                            feedback_timer = feedback_display_time
                            # Find and jump to next question
                            current_idx = questions.index(current_question)
                            if current_idx < len(questions) - 1:
                                next_q = questions[current_idx + 1]
                                current_frame = int(next_q.time * fps)
                                current_question = next_q
                                question_state = "multiple_choice"
                                answer_feedback = None
                                click_feedback = None
                                auto_play = False  # Pause at next question
                            else:
                                print("This was the last question!")
                                auto_play = True  # Continue if it was the last question
                        else:
                            click_feedback = feedback
                            feedback_timer = feedback_display_time
                            current_question.click_answered = False
                            current_question.answered = False

    # Set up window
    cv2.namedWindow("Mock Test")
    cv2.setMouseCallback("Mock Test", mouse_callback)

    # Display controls
    def display_controls(frame, y_offset, question_state):
        cv2.putText(frame, "Controls:", (10, y_offset),
                    font, control_font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
        y_offset += 18

        # Always show these controls
        controls = [
            "H: Show/Hide Sidebar",
            "T: Toggle Hints (currently " + ("ON" if show_answers else "OFF") + ")",
            "Space: Play/Pause",
            "W/S: Frame Forward/Back",
            "N/P: Next/Previous Question",
            "Q: Quit"
        ]

        # Add question-specific controls
        if question_state == "multiple_choice":
            controls.insert(1, "A/B/C/D: Select Answer")
        elif question_state == "click":
            controls.insert(1, "Click: Select Location")

        # Display all controls
        for control in controls:
            cv2.putText(frame, control, (10, y_offset),
                        font, control_font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
            y_offset += 18

        return y_offset

    # Main test loop
    while True:
        # Calculate time since last frame
        current_time = cv2.getTickCount()
        elapsed = (current_time - last_frame_time) / cv2.getTickFrequency()
        
        # Position video at current frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret:
            break

        time_in_seconds = current_frame / fps
        frame_height, frame_width = frame.shape[:2]

        # Resize frame to maintain aspect ratio with better quality
        if frame_width != video_width or frame_height != video_height:
            # Use INTER_CUBIC for better quality when upscaling
            # Use INTER_AREA for better quality when downscaling
            interpolation = cv2.INTER_CUBIC if scale_factor > 1 else cv2.INTER_AREA
            frame = cv2.resize(frame, (video_width, video_height), interpolation=interpolation)

        # Create a black overlay to hide patient ID in background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (video_width, 40), (0, 0, 0), -1)  # Black bar at top
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)  # Blend with original

        # Create sidebar for information if enabled
        if show_sidebar:
            frame = create_sidebar(frame)

        # Draw answer hints if enabled
        if show_answers and current_question and current_question.correct_location:
            if current_question.mask is not None:
                # For mask-based questions, overlay the mask with transparency
                overlay = frame.copy()
                # Convert mask to binary (white = polyp area) and resize to match frame
                mask_gray = cv2.cvtColor(current_question.mask, cv2.COLOR_BGR2GRAY)
                mask_gray = cv2.resize(mask_gray, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
                _, mask_binary = cv2.threshold(mask_gray, 200, 255, cv2.THRESH_BINARY)
                # Create colored overlay (green for polyp area)
                mask_overlay = cv2.cvtColor(mask_binary, cv2.COLOR_GRAY2BGR)
                mask_overlay[mask_binary > 0] = [0, 255, 0]  # Set white areas to green
                # Blend with original frame
                cv2.addWeighted(mask_overlay, 0.3, overlay, 0.7, 0, overlay)
                frame = overlay
                
                # Store the resized mask for click detection
                current_question.display_mask = mask_binary
                
                # Draw click feedback if available
                if click_answer and question_state == "click":
                    click_x, click_y = click_answer
                    # Draw click point
                    cv2.circle(frame, (click_x, click_y), 5, (0, 0, 255), -1)  # Red dot
                    # If click is outside white area, draw line to nearest white pixel
                    if mask_binary[click_y, click_x] == 0:
                        # Find nearest white pixel (simple implementation)
                        min_dist = float('inf')
                        nearest_x, nearest_y = click_x, click_y
                        for y in range(max(0, click_y-50), min(mask_binary.shape[0], click_y+50)):
                            for x in range(max(0, click_x-50), min(mask_binary.shape[1], click_x+50)):
                                if mask_binary[y, x] > 0:
                                    dist = math.sqrt((x-click_x)**2 + (y-click_y)**2)
                                    if dist < min_dist:
                                        min_dist = dist
                                        nearest_x, nearest_y = x, y
                        if min_dist != float('inf'):
                            cv2.line(frame, (click_x, click_y), (nearest_x, nearest_y), (0, 0, 255), 1)
            elif ',' in current_question.correct_location:
                coords = current_question.correct_location.split(',')
                if len(coords) == 4:
                    # Draw rectangle
                    x1, y1, x2, y2 = map(int, coords)
                    # Draw semi-transparent rectangle
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)  # Filled rectangle
                    cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)  # Blend with original
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Rectangle outline
                    
                    # Draw click feedback if available
                    if click_answer and question_state == "click":
                        click_x, click_y = click_answer
                        # Draw click point
                        cv2.circle(frame, (click_x, click_y), 5, (0, 0, 255), -1)  # Red dot
                        # Draw line to rectangle if outside
                        if not (x1 <= click_x <= x2 and y1 <= click_y <= y2):
                            # Find nearest point on rectangle
                            nearest_x = max(x1, min(click_x, x2))
                            nearest_y = max(y1, min(click_y, y2))
                            cv2.line(frame, (click_x, click_y), (nearest_x, nearest_y), (0, 0, 255), 1)  # Red line

        # Display current time and controls
        if show_sidebar:
            # Display current time
            time_text = format_time(time_in_seconds)
            cv2.putText(frame, f"Time: {time_text}", (10, 30),
                        font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

            # Display mouse coordinates
            if show_mouse_coords and sidebar_width <= mouse_x <= window_width:  # Only show coordinates when mouse is in video area
                cv2.putText(frame, f"Mouse: ({mouse_x}, {mouse_y})", (10, 60),
                            font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
                y_offset = 90
            else:
                y_offset = 60

            # Display question list
            cv2.putText(frame, "Questions:", (10, y_offset),
                        font, status_font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
            y_offset += 25  # Reduced from 30

            # Show only current question and next 2 questions
            current_idx = questions.index(current_question) if current_question else -1
            visible_questions = []
            if current_idx >= 0:
                visible_questions = questions[max(0, current_idx-1):min(len(questions), current_idx+3)]
            else:
                visible_questions = questions[:3] if questions else []

            for question in visible_questions:
                # Determine question status
                if question.answered:
                    status = "✓"  # Completed
                    color = (0, 255, 0)  # Green
                elif current_question == question:
                    if question_state == "multiple_choice":
                        status = "→"  # Current question, multiple choice
                        color = (0, 255, 255)  # Yellow
                    elif question_state == "click":
                        status = "•"  # Current question, click phase
                        color = (0, 255, 255)  # Yellow
                    else:
                        status = " "  # Current question, completed
                        color = (255, 255, 255)  # White
                else:
                    status = " "  # Not started
                    color = (255, 255, 255)  # White

                time_text = format_time(question.time)
                question_text = f"{questions.index(question)+1}: {time_text} {status}"
                cv2.putText(frame, question_text, (10, y_offset),
                            font, status_font_scale, color, font_thickness, cv2.LINE_AA)
                y_offset += 18  # Reduced from 20

                # Show answer hints if enabled
                if show_answers and question.correct_location and question == current_question:
                    if ',' in question.correct_location:
                        coords = question.correct_location.split(',')
                        if len(coords) == 4:
                            x1, y1, x2, y2 = map(int, coords)
                            cv2.putText(frame, f"   Click in rectangle: ({x1},{y1}) to ({x2},{y2})", (10, y_offset),
                                        font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
                        y_offset += 18  # Reduced from 20

            # Show progress
            if current_question:
                progress_text = f"Question {questions.index(current_question)+1} of {len(questions)}"
                cv2.putText(frame, progress_text, (10, y_offset),
                            font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
                y_offset += 30

            # Check for current question
            if not current_question or current_question.answered:
                for question in questions:
                    if abs(time_in_seconds - question.time) < (1 / fps) and not question.answered:
                        current_question = question
                        auto_play = False
                        question_state = "multiple_choice"
                        answer_feedback = None
                        click_feedback = None
                        break

            # Display question if present
            if current_question and not current_question.answered:
                y_offset = display_question(frame, current_question, question_state, y_offset, 
                                          font, font_scale, font_thickness, max_text_width, 
                                          show_answers, question_font_scale, option_font_scale)
                
                # Display feedback if any
                if feedback_timer > 0:
                    y_offset = display_feedback(frame, answer_feedback, click_feedback, y_offset, font, font_scale, font_thickness)
                    feedback_timer -= 1

                # Display current phase
                if question_state == "multiple_choice":
                    cv2.putText(frame, "Phase: Multiple Choice", (10, y_offset),
                                font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
                    y_offset += 18  # Reduced from 20
                elif question_state == "click" and current_question.correct_location and current_question.correct_location != "No location needed":
                    cv2.putText(frame, "Phase: Click Location", (10, y_offset),
                                font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
                    y_offset += 18  # Reduced from 20
                    cv2.putText(frame, "Click inside the green rectangle", (10, y_offset),
                                font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
                    y_offset += 18  # Reduced from 20

                # Display controls
                y_offset = display_controls(frame, y_offset, question_state)
            else:
                # Display controls when no question is active
                y_offset = display_controls(frame, y_offset, "none")
        else:
            # When sidebar is hidden, show minimal controls with background
            menu_x = 10
            menu_y = 30
            cv2.rectangle(frame, (menu_x - 10, menu_y - 25), (menu_x + 150, menu_y + 130), (0, 0, 0), -1)
            cv2.putText(frame, "Controls:", (menu_x, menu_y),
                        font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
            menu_y += 25
            controls = [
                "H: Show/Hide Info",
                "Space: Play/Pause",
                "W/S: Frame Forward/Back",
                "N/P: Next/Previous",
                "Q: Quit"
            ]
            for control in controls:
                cv2.putText(frame, control, (menu_x, menu_y),
                            font, control_font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
                menu_y += 20

        # Display frame
        cv2.imshow("Mock Test", frame)

        # Handle keyboard input
        key = cv2.waitKey(frame_delay) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('f'):  # Add fullscreen toggle
            cv2.setWindowProperty("Mock Test", cv2.WND_PROP_FULLSCREEN, 
                                cv2.WINDOW_FULLSCREEN if not cv2.getWindowProperty("Mock Test", cv2.WND_PROP_FULLSCREEN) else cv2.WINDOW_NORMAL)
        elif key == ord('h'):  # Toggle sidebar
            show_sidebar = not show_sidebar
        elif key == ord('t'):  # Toggle hints
            show_answers = not show_answers
        elif key == ord(' '):
            auto_play = not auto_play
        elif key == ord('w') and not auto_play:
            current_frame += 1
        elif key == ord('s') and not auto_play:
            current_frame -= 1
        elif key == ord('n'):
            if current_question:
                idx = questions.index(current_question)
                if idx < len(questions) - 1:
                    next_q = questions[idx + 1]
                    current_frame = int(next_q.time * fps)
                    current_question = next_q
                    auto_play = False
                    question_state = "multiple_choice"
                    answer_feedback = None
                    click_feedback = None
            elif questions:
                # If no question is active, jump to the first question
                current_frame = int(questions[0].time * fps)
                current_question = questions[0]
                auto_play = False
                question_state = "multiple_choice"
                answer_feedback = None
                click_feedback = None
            print("Jumped to question (N):", (current_question.question_text if current_question else "None"))

        elif key == ord('p'):
            if current_question:
                idx = questions.index(current_question)
                if idx > 0:
                    prev_q = questions[idx - 1]
                    current_frame = int(prev_q.time * fps)
                    current_question = prev_q
                    auto_play = False
                    question_state = "multiple_choice"
                    answer_feedback = None
                    click_feedback = None
            elif questions:
                # If no question is active, jump to the last question
                current_frame = int(questions[-1].time * fps)
                current_question = questions[-1]
                auto_play = False
                question_state = "multiple_choice"
                answer_feedback = None
                click_feedback = None
            print("Jumped to question (P):", (current_question.question_text if current_question else "None"))

        # Handle multiple choice
        if current_question and not current_question.answered and question_state == "multiple_choice":
            if key in [ord('a'), ord('b'), ord('c'), ord('d')]:
                selected = chr(key).upper()
                if selected in current_question.options:
                    if selected == current_question.correct_answer:
                        # Correct answer
                        if (current_question.correct_location and 
                            (current_question.correct_location != "No location needed" or 
                             current_question.correct_location == "Click required")):
                            if (',' in current_question.correct_location or 
                                current_question.correct_location.endswith('.png') or 
                                current_question.correct_location == "Click required"):
                                answer_feedback = "Correct! Now click on the location in the video."
                                current_question.multiple_choice_answered = True
                                question_state = "click"  # Move to click phase
                                current_question.answered = False
                                auto_play = False  # Pause for click
                            else:
                                # No click needed, mark as complete and move to next
                                answer_feedback = "Correct! Moving to next question..."
                                current_question.multiple_choice_answered = True
                                current_question.answered = True
                                question_state = "completed"
                                # Find and jump to next question
                                current_idx = questions.index(current_question)
                                if current_idx < len(questions) - 1:
                                    next_q = questions[current_idx + 1]
                                    current_frame = int(next_q.time * fps)
                                    current_question = next_q
                                    question_state = "multiple_choice"
                                    answer_feedback = None
                                    click_feedback = None
                                    auto_play = False  # Pause at next question
                                else:
                                    print("This was the last question!")
                                    auto_play = True  # Continue if it was the last question
                            feedback_timer = feedback_display_time
                        else:
                            # No location needed, mark as complete and move to next
                            answer_feedback = "Correct! Moving to next question..."
                            current_question.multiple_choice_answered = True
                            current_question.answered = True
                            question_state = "completed"
                            # Find and jump to next question
                            current_idx = questions.index(current_question)
                            if current_idx < len(questions) - 1:
                                next_q = questions[current_idx + 1]
                                current_frame = int(next_q.time * fps)
                                current_question = next_q
                                question_state = "multiple_choice"
                                answer_feedback = None
                                click_feedback = None
                                auto_play = False  # Pause at next question
                            else:
                                print("This was the last question!")
                                auto_play = True  # Continue if it was the last question
                            feedback_timer = feedback_display_time
                    else:
                        answer_feedback = f"Wrong! The correct answer was {current_question.correct_answer}. Try again!"
                        current_question.multiple_choice_answered = False
                        current_question.answered = False
                        auto_play = False  # Pause for retry
                        feedback_timer = feedback_display_time

        # Update frame
        if auto_play:
            # Calculate how many frames to advance based on elapsed time
            frames_to_advance = int(elapsed * fps)
            if frames_to_advance > 0:
                current_frame += frames_to_advance
                last_frame_time = current_time
        else:
            current_frame = max(0, min(current_frame, total_frames - 1))
            last_frame_time = current_time

    cap.release()
    cv2.destroyAllWindows()

def check_click_answer(click_pos, correct_pos, mask=None, threshold=50):
    """Check if clicked position is within the correct area using either rectangle or mask"""
    if mask is not None:
        # Use mask-based detection
        try:
            # Check if click is within image bounds
            if (0 <= click_pos[1] < mask.shape[0] and 
                0 <= click_pos[0] < mask.shape[1]):
                # Get pixel value at click position
                pixel_value = mask[click_pos[1], click_pos[0]]
                # Check if pixel is white (or near white)
                if pixel_value > 200:
                    return True, "Correct location!"
                else:
                    return False, "Click must be on the white area!"
            return False, "Click outside image bounds"
        except Exception as e:
            print(f"Error in mask detection: {e}")
            return False, "Error in mask detection"
    
    # Fall back to rectangle-based detection
    if not correct_pos:
        return False, "No correct location specified"
    
    try:
        if ',' in correct_pos:
            coords = correct_pos.split(',')
            if len(coords) == 4:
                # Rectangle format (x1,y1,x2,y2)
                x1, y1, x2, y2 = map(int, coords)
                if (x1 <= click_pos[0] <= x2) and (y1 <= click_pos[1] <= y2):
                    return True, "Correct location!"
                else:
                    dx = max(x1 - click_pos[0], 0, click_pos[0] - x2)
                    dy = max(y1 - click_pos[1], 0, click_pos[1] - y2)
                    distance = math.sqrt(dx*dx + dy*dy)
                    return False, f"Click must be inside the green rectangle! (Distance: {int(distance)} pixels)"
            elif len(coords) == 2:
                # Single point format (x,y)
                x, y = map(int, coords)
                distance = math.sqrt((click_pos[0] - x)**2 + (click_pos[1] - y)**2)
                if distance <= threshold:
                    return True, "Correct location!"
                else:
                    return False, f"Not quite right. Try again! (Distance: {int(distance)} pixels)"
    except ValueError as e:
        print(f"Error parsing coordinates: {e}")
        return False, "Invalid location format"
    # Always return a tuple if nothing else matches
    return False, "Invalid click or mask configuration"

def display_question(frame, question, question_state, y_offset, font, font_scale, font_thickness, 
                    max_text_width, show_answers=False, question_font_scale=0.6, option_font_scale=0.6):
    """Display the current question and options"""
    if not question:
        return y_offset
        
    # Display question text
    cv2.putText(frame, "Question:", (10, y_offset),
                font, question_font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
    y_offset += 25  # Reduced from 30
    
    # Wrap and display question text
    wrapped_question = wrap_text(question.question_text, font, question_font_scale, font_thickness, max_text_width)
    for line in wrapped_question:
        cv2.putText(frame, line, (10, y_offset),
                    font, question_font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
        y_offset += 18  # Reduced from 20
    
    y_offset += 8  # Reduced from 10
    
    # Display options if in multiple choice state
    if question_state == "multiple_choice":
        for key, option in question.options.items():
            # Highlight correct answer if show_answers is enabled
            if show_answers and key == question.correct_answer:
                # Draw a green background for the correct answer
                text_size = cv2.getTextSize(f"{key}: {option}", font, option_font_scale, font_thickness)[0]
                cv2.rectangle(frame, (5, y_offset - text_size[1] - 2), 
                            (text_size[0] + 15, y_offset + 2), (0, 100, 0), -1)
                cv2.putText(frame, f"{key}: {option}", (10, y_offset),
                            font, option_font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
            else:
                option_text = f"{key}: {option}"
                cv2.putText(frame, option_text, (10, y_offset),
                            font, option_font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
            y_offset += 18  # Reduced from 20
        
        # Add hint text if show_answers is enabled
        if show_answers:
            y_offset += 8  # Add some space
            cv2.putText(frame, "Hint: Green option is the correct answer", (10, y_offset),
                        font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
            y_offset += 18  # Reduced from 20

    # Display click instruction if in click state
    if question_state == "click" and question.correct_location and question.correct_location != "No location needed":
        y_offset += 8  # Reduced from 10
        cv2.putText(frame, "Click on the correct location in the video", (10, y_offset),
                    font, font_scale, (0, 255, 255), font_thickness, cv2.LINE_AA)
        y_offset += 18  # Reduced from 20
        if show_answers:
            if question.mask is not None:
                cv2.putText(frame, "Hint: Click inside the green overlay (polyp area)", (10, y_offset),
                            font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
                y_offset += 18  # Reduced from 20
                cv2.putText(frame, "The green area shows where the polyp is located", (10, y_offset),
                            font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
            else:
                cv2.putText(frame, "Hint: Click inside the green rectangle", (10, y_offset),
                            font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
            y_offset += 18  # Reduced from 20
    
    return y_offset

def display_feedback(frame, answer_feedback, click_feedback, y_offset, font, font_scale, font_thickness):
    """Display feedback for answers"""
    if answer_feedback:
        cv2.putText(frame, answer_feedback, (10, y_offset),
                    font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
        y_offset += 18  # Reduced from 20
    
    if click_feedback:
        cv2.putText(frame, click_feedback, (10, y_offset),
                    font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)
        y_offset += 18  # Reduced from 20
    
    return y_offset

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