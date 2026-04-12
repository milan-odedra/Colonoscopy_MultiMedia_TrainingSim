import cv2
import numpy as np
import time
import csv
from pathlib import Path

# Use relative paths for video and markers
BASE_DIR = Path(__file__).parent
VIDEO_PATH = BASE_DIR / "videos" / "Without annotations (edited).mp4"
MARKERS_PATH = BASE_DIR / "data" / "new_perception_markers.csv"

class PerceptionTestV2:
    def __init__(self):
        self.window_name = "Perception Test V2"
        self.sidebar_width = 400  # Increased for MCQ display
        self.status = "Paused"
        self.time_sec = 0.0
        self.speed = 1.0
        self.is_playing = False
        self.show_sidebar = True
        self.marker_display = True
        self.fullscreen = False
        self.correct = 0
        self.incorrect = 0
        self.current_marker = None
        self.markers = self.load_markers()
        self.next_marker_idx = 0  # Always points to the NEXT marker to process
        self.mask = None
        self.waiting_for_click = False
        self.waiting_for_mcq = False
        self.mcq_options = []
        self.selected_mcq_option = 0
        self.correct_option = None
        self.feedback = None
        self.feedback_timer = 0
        
        # Debug mode toggle
        self.debug_mode = False
        
        # Polyp detection specific variables
        self.polyp_detection_active = False
        self.polyp_window_start = 0
        self.polyp_window_end = 0
        self.polyps_detected = 0
        self.polyps_missed = 0
        
        # 2-point polyp system variables
        self.polyp_timing_point_awarded = False
        self.polyp_accuracy_point_awarded = False
        self.waiting_for_polyp_accuracy_click = False
        
        self.cap = cv2.VideoCapture(str(VIDEO_PATH))
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video: {VIDEO_PATH}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0
        
        # Get original video frame size
        self.original_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.original_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.window_width = self.original_width + self.sidebar_width
        self.window_height = self.original_height
        self.display_video_width = self.original_width
        self.display_video_height = self.original_height
        self.last_click_pos = None
        self.mask_overlay_on = True  # Toggle for mask overlay
        self.last_click_coords = None

        # Debug: Print loaded markers
        print(f"Loaded {len(self.markers)} markers:")
        for i, marker in enumerate(self.markers):
            print(f"  Marker {i}: time={marker['start_time']}s, type={marker['question_type']}, question={marker['question_text']}")

    def load_markers(self):
        markers = []
        with open(MARKERS_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                markers.append(row)
        return markers

    def format_time(self, seconds):
        return f"{int(seconds//60):02d}:{int(seconds%60):02d}.{int((seconds%1)*100):02d}"

    def load_mask_for_marker(self, marker):
        mask_path = marker['mask_path']
        if not mask_path or mask_path.strip() == '':
            return None
        if not Path(mask_path).is_absolute():
            mask_path = BASE_DIR / mask_path
        print(f"DEBUG: Loading mask from: {mask_path}")
        if not Path(mask_path).exists():
            print(f"WARNING: Mask file not found: {mask_path}")
            return None
        try:
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                print(f"WARNING: Could not read mask file: {mask_path}")
                return None
            mask = cv2.resize(mask, (self.original_width, self.original_height), interpolation=cv2.INTER_NEAREST)
            print(f"DEBUG: Successfully loaded mask with dimensions: {mask.shape}")
            return mask
        except Exception as e:
            print(f"WARNING: Error loading mask {mask_path}: {e}")
            return None

    def setup_mcq_question(self, marker):
        """Setup MCQ question from marker data"""
        options_str = marker.get('question_options', '')
        if not options_str:
            return False
        
        self.mcq_options = options_str.split('|')
        self.correct_option = int(marker.get('correct_option', 1)) - 1  # Convert to 0-based index
        self.selected_mcq_option = 0
        return True

    def is_time_window_marker(self, marker):
        """Check if marker has an end_time (making it a time window)"""
        end_time = marker.get('end_time', '')
        return end_time and end_time.strip() != ''

    def trigger_marker(self, marker_idx):
        if marker_idx >= len(self.markers):
            print(f"DEBUG: No more markers to trigger (requested idx: {marker_idx}, total: {len(self.markers)})")
            return False
        
        marker = self.markers[marker_idx]
        marker_time = float(marker['start_time'])
        question_type = marker['question_type']
        
        print(f"DEBUG: Triggering marker {marker_idx}")
        print(f"  - Marker time: {marker_time}s")
        print(f"  - Current video time: {self.time_sec:.3f}s")
        print(f"  - Question: {marker['question_text']}")
        print(f"  - Type: {question_type}")
        
        # Reset states
        self.waiting_for_click = False
        self.waiting_for_mcq = False
        self.mask = None
        self.mcq_options = []
        self.polyp_detection_active = False
        
        # Handle different question types
        if question_type == 'marker':
            # Information marker - display message and continue
            self.current_marker = marker
            self.feedback = marker['question_text']
            self.feedback_timer = 120  # Show message longer
            self.advance_to_next_marker()
            return True
            
        elif question_type == 'polyp_window':
            # Handle polyp detection time window
            if self.is_time_window_marker(marker):
                self.polyp_window_start = marker_time
                self.polyp_window_end = float(marker['end_time'])
                self.polyp_detection_active = True
                self.current_marker = marker
                self.mask = self.load_mask_for_marker(marker)  # Load mask for later use
                print(f"DEBUG: Polyp detection window active: {self.polyp_window_start}s - {self.polyp_window_end}s")
                # Don't pause for polyp windows - let video continue playing
                self.is_playing = True
                self.status = "Playing"
                return True
            else:
                print(f"DEBUG: Polyp window marker missing end_time")
                self.advance_to_next_marker()
                return False
                
        elif question_type == 'lumen':
            # Handle lumen questions (click-based, freeze-frame)
            self.is_playing = False
            self.status = "Paused"
            self.current_marker = marker
            self.mask = self.load_mask_for_marker(marker)
            if self.mask is not None:
                print(f"DEBUG: Mask loaded successfully for lumen question {marker_idx}")
                self.waiting_for_click = True
            else:
                print(f"DEBUG: No mask available for lumen question {marker_idx}")
                self.advance_to_next_marker()
                return False
                
        elif question_type in ['location', 'position']:
            # Handle MCQ questions (freeze-frame)
            self.is_playing = False
            self.status = "Paused"
            self.current_marker = marker
            if self.setup_mcq_question(marker):
                print(f"DEBUG: MCQ setup successfully for {question_type} question {marker_idx}")
                print(f"  - Options: {self.mcq_options}")
                print(f"  - Correct answer: {self.correct_option + 1}")
                self.waiting_for_mcq = True
            else:
                print(f"DEBUG: Failed to setup MCQ for {question_type} question {marker_idx}")
                self.advance_to_next_marker()
                return False
        
        self.feedback = None
        self.feedback_timer = 0
        return True

    def process_next_marker_if_ready(self):
        # Check if polyp detection window has ended
        if self.polyp_detection_active and self.time_sec > self.polyp_window_end:
            print(f"DEBUG: Polyp detection window ended at {self.time_sec:.3f}s")
            self.polyps_missed += 1
            self.feedback = f"Polyp missed! (+1 missed)"
            self.feedback_timer = 60
            self.polyp_detection_active = False
            self.advance_to_next_marker()
            return
            
        # Don't process new markers if we're waiting for user input or in active polyp window
        if self.waiting_for_click or self.waiting_for_mcq or self.polyp_detection_active:
            return
            
        if self.next_marker_idx >= len(self.markers):
            return
            
        marker = self.markers[self.next_marker_idx]
        marker_time = float(marker['start_time'])
        
        if self.time_sec >= marker_time:
            print(f"DEBUG: Time {self.time_sec:.3f}s >= marker time {marker_time}s, triggering marker {self.next_marker_idx}")
            if self.trigger_marker(self.next_marker_idx):
                pass
        else:
            if self.next_marker_idx == 0:
                print(f"DEBUG: Waiting for time {marker_time}s (current: {self.time_sec:.3f}s) to trigger marker {self.next_marker_idx}")

    def advance_to_next_marker(self):
        self.next_marker_idx += 1
        self.current_marker = None
        self.mask = None
        self.waiting_for_click = False
        self.waiting_for_mcq = False
        self.mcq_options = []
        self.polyp_detection_active = False
        print(f"DEBUG: Advanced to next marker index: {self.next_marker_idx}")
        
        # Only resume playing if we're not at another freeze-frame marker
        if self.next_marker_idx < len(self.markers):
            next_marker = self.markers[self.next_marker_idx]
            if next_marker['question_type'] not in ['lumen', 'location', 'position']:
                self.is_playing = True
                self.status = "Playing"

    def jump_to_marker(self, idx):
        if not (0 <= idx < len(self.markers)):
            print(f"DEBUG: Invalid marker index: {idx}")
            return
        marker = self.markers[idx]
        marker_time = float(marker['start_time'])
        print(f"DEBUG: Manually jumping to marker {idx} at time {marker_time}s")
        self.current_frame = int(marker_time * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.time_sec = self.current_frame / self.fps
        self.next_marker_idx = idx
        self.trigger_marker(idx)

    def draw_sidebar(self, frame):
        sidebar = np.zeros((self.window_height, self.sidebar_width, 3), dtype=np.uint8)
        y = 30
        cv2.putText(sidebar, "Perception Test V2", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
        y += 40
        
        cv2.putText(sidebar, f"Status: {self.status}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        y += 30
        cv2.putText(sidebar, f"Time: {self.format_time(self.time_sec)}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        y += 30
        cv2.putText(sidebar, f"Frame: {self.current_frame}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 1)
        y += 25
        cv2.putText(sidebar, f"Time (ms): {self.time_sec:.3f}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 1)
        y += 30
        cv2.putText(sidebar, f"Speed: {self.speed:.1f}x", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        y += 30
        cv2.putText(sidebar, f"Next Marker: {self.next_marker_idx}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 1)
        y += 30
        
        # Show polyp detection status
        if self.polyp_detection_active:
            cv2.putText(sidebar, "POLYP DETECTION ACTIVE", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            y += 25
            
            if not self.polyp_timing_point_awarded:
                cv2.putText(sidebar, "Click when you see a polyp!", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1)
                y += 25
                cv2.putText(sidebar, "Point 1: Timing", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
            elif self.waiting_for_polyp_accuracy_click:
                cv2.putText(sidebar, "Now click on the polyp area!", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 1)
                y += 25
                cv2.putText(sidebar, "Point 2: Accuracy", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
                y += 20
                cv2.putText(sidebar, "Mask overlay: ON", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)
            
            y += 30
            
            # Debug mode: Show timing information
            if self.debug_mode:
                y += 10
                cv2.putText(sidebar, f"Window: {self.polyp_window_start:.1f}s - {self.polyp_window_end:.1f}s", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
                y += 20
                cv2.putText(sidebar, f"Time left: {max(0, self.polyp_window_end - self.time_sec):.1f}s", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
                y += 20
        elif self.current_marker:
            cv2.putText(sidebar, f"Type: {self.current_marker['question_type'].upper()}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,255), 1)
            y += 25
            cv2.putText(sidebar, f"Marker: {self.format_time(float(self.current_marker['start_time']))}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 1)
            y += 25
            
            # Display question text (wrap if too long)
            question = self.current_marker['question_text']
            if len(question) > 40:
                # Split long questions into multiple lines
                words = question.split()
                lines = []
                current_line = ""
                for word in words:
                    if len(current_line + word) > 35:
                        lines.append(current_line.strip())
                        current_line = word + " "
                    else:
                        current_line += word + " "
                if current_line:
                    lines.append(current_line.strip())
                
                for line in lines:
                    cv2.putText(sidebar, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
                    y += 20
            else:
                cv2.putText(sidebar, question, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
                y += 25
            
            # Display MCQ options if available
            if self.waiting_for_mcq and self.mcq_options:
                y += 10
                cv2.putText(sidebar, "Options:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
                y += 25
                for i, option in enumerate(self.mcq_options):
                    color = (0,255,0) if i == self.selected_mcq_option else (200,200,200)
                    prefix = f"{i+1}. "
                    if i == self.selected_mcq_option:
                        prefix = f"> {i+1}. "
                    cv2.putText(sidebar, prefix + option, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
                    y += 22
                y += 10
                cv2.putText(sidebar, "Use 1-5 keys or W/S + Enter", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)
                y += 20
            
            # Show click instruction for lumen questions
            elif self.waiting_for_click:
                y += 10
                cv2.putText(sidebar, "Click on the lumen!", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            y += 30
        
        cv2.putText(sidebar, f"Correct: {self.correct}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 1)
        y += 25
        cv2.putText(sidebar, f"Incorrect: {self.incorrect}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 1)
        y += 25
        cv2.putText(sidebar, f"Polyps Detected: {self.polyps_detected}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 1)
        y += 25
        cv2.putText(sidebar, f"Polyps Missed: {self.polyps_missed}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0), 1)
        y += 40
        
        cv2.putText(sidebar, "Controls:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 1)
        y += 25
        controls = [
            "Space: Play/Pause",
            "+/-: Speed Up/Down",
            "F: Fullscreen",
            "S: Toggle Sidebar",
            "M: Toggle Marker Info",
            "N/P: Next/Previous Marker",
            "O: Toggle Mask Overlay",
            "D: Toggle Debug Mode",
            "W/S: Navigate MCQ",
            "Enter: Select MCQ",
            "1-5: Direct MCQ Select",
            "Q: Quit"
        ]
        for ctrl in controls:
            cv2.putText(sidebar, ctrl, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200,200,200), 1)
            y += 18
        
        if self.last_click_coords and (self.waiting_for_click or self.polyp_detection_active):
            y += 15
            cv2.putText(sidebar, f"Click: {self.last_click_coords}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 1)
        
        if self.feedback and self.feedback_timer > 0:
            y += 20
            color = (0,255,0) if "Correct" in self.feedback or "Complete" in self.feedback else (0,0,255)
            cv2.putText(sidebar, self.feedback, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        frame[:, :self.sidebar_width] = sidebar
        return frame

    def handle_mcq_answer(self, selected_idx):
        """Handle MCQ answer selection"""
        if selected_idx == self.correct_option:
            self.correct += 1
            self.feedback = "Correct!"
            print(f"DEBUG: Correct MCQ answer! Selected: {selected_idx + 1}, Correct: {self.correct_option + 1}")
        else:
            self.incorrect += 1
            self.feedback = f"Incorrect! Answer was {self.correct_option + 1}"
            print(f"DEBUG: Incorrect MCQ answer! Selected: {selected_idx + 1}, Correct: {self.correct_option + 1}")
        
        self.feedback_timer = 90  # Show feedback longer for MCQ
        self.advance_to_next_marker()

    def handle_polyp_click(self, x, y):
        """Handle polyp detection click - 2-point system"""
        if not self.polyp_detection_active:
            return
            
        print(f"DEBUG: Polyp click at x: {x}, y: {y}")
        
        # Check if click is within time window
        if self.polyp_window_start <= self.time_sec <= self.polyp_window_end:
            if not self.polyp_timing_point_awarded:
                # First click - award timing point
                self.polyp_timing_point_awarded = True
                self.correct += 1
                self.feedback = "Timing correct! (+1 point) Now click on the polyp area"
                print(f"DEBUG: Timing point awarded! Total correct: {self.correct}")
                
                # Show mask overlay for accuracy click
                self.waiting_for_polyp_accuracy_click = True
                self.mask_overlay_on = True  # Force mask overlay on
                self.feedback_timer = 120  # Show message longer
                return
                
            elif self.waiting_for_polyp_accuracy_click:
                # Second click - check accuracy with mask
                if self.mask is not None:
                    if 0 <= x < self.mask.shape[1] and 0 <= y < self.mask.shape[0]:
                        if self.mask[y, x] == 255:
                            self.polyp_accuracy_point_awarded = True
                            self.correct += 1
                            self.polyps_detected += 1
                            self.feedback = "Accuracy correct! (+1 point) Polyp fully detected!"
                            print(f"DEBUG: Accuracy point awarded! Total correct: {self.correct}")
                        else:
                            self.incorrect += 1
                            self.feedback = "Accuracy missed - click was outside polyp area"
                            print(f"DEBUG: Accuracy point missed")
                    else:
                        self.incorrect += 1
                        self.feedback = "Click outside valid area"
                else:
                    # No mask available - just award point for completing the process
                    self.polyp_accuracy_point_awarded = True
                    self.correct += 1
                    self.polyps_detected += 1
                    self.feedback = "Accuracy point awarded (no mask validation)"
                    print(f"DEBUG: Accuracy point awarded (no mask)")
                
                # End polyp detection
                self.feedback_timer = 60
                self.polyp_detection_active = False
                self.waiting_for_polyp_accuracy_click = False
                self.polyp_timing_point_awarded = False
                self.polyp_accuracy_point_awarded = False
                self.advance_to_next_marker()
        else:
            print(f"DEBUG: Click outside time window ({self.polyp_window_start}-{self.polyp_window_end})")

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            x_adj = x - self.sidebar_width
            y_adj = y
            self.last_click_coords = (x_adj, y_adj)
            
            if self.waiting_for_click and self.mask is not None:
                # Handle lumen click
                print(f"DEBUG: Lumen click at x: {x_adj}, y: {y_adj}")
                if 0 <= x_adj < self.mask.shape[1] and 0 <= y_adj < self.mask.shape[0]:
                    if self.mask[y_adj, x_adj] == 255:
                        self.correct += 1
                        self.feedback = "Correct!"
                        print(f"DEBUG: Correct lumen click! Total correct: {self.correct}")
                    else:
                        self.incorrect += 1
                        self.feedback = "Incorrect!"
                        print(f"DEBUG: Incorrect lumen click! Total incorrect: {self.incorrect}")
                    self.feedback_timer = 60
                    self.advance_to_next_marker()
                    
            elif self.polyp_detection_active:
                # Handle polyp detection click (2-point system)
                self.handle_polyp_click(x_adj, y_adj)
        
    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.window_width, self.window_height)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        print("DEBUG: Starting perception test")
        
        while True:
            if self.is_playing:
                ret, frame = self.cap.read()
                if not ret:
                    print("DEBUG: End of video reached")
                    break
                self.current_frame += 1
                self.time_sec = self.current_frame / self.fps
                wait_time = 10
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                ret, frame = self.cap.read()
                if not ret:
                    break
                wait_time = 100
            
            self.process_next_marker_if_ready()
            
            video_disp = frame.copy()
            full_frame = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
            full_frame[:, self.sidebar_width:] = video_disp
            
            if self.show_sidebar:
                full_frame = self.draw_sidebar(full_frame)
            
            # Show mask overlay for lumen questions (not for polyp detection)
            if self.mask is not None and self.mask_overlay_on and self.waiting_for_click:
                mask_rgb = np.zeros((self.display_video_height, self.display_video_width, 3), dtype=np.uint8)
                mask_rgb[self.mask == 255] = [0, 255, 255]  # Yellow overlay for mask areas
                overlay = cv2.addWeighted(video_disp, 0.7, mask_rgb, 0.3, 0)
                full_frame[:, self.sidebar_width:] = overlay
            
            # Show mask overlay for polyp detection (ADDED!)
            elif self.mask is not None and self.mask_overlay_on and self.polyp_detection_active:
                mask_rgb = np.zeros((self.display_video_height, self.display_video_width, 3), dtype=np.uint8)
                mask_rgb[self.mask == 255] = [0, 255, 255]  # Yellow overlay for mask areas
                overlay = cv2.addWeighted(video_disp, 0.7, mask_rgb, 0.3, 0)
                full_frame[:, self.sidebar_width:] = overlay
            
            # Show mask overlay for polyp accuracy phase (2-point system)
            elif self.mask is not None and self.waiting_for_polyp_accuracy_click:
                mask_rgb = np.zeros((self.display_video_height, self.display_video_width, 3), dtype=np.uint8)
                mask_rgb[self.mask == 255] = [0, 255, 255]  # Yellow overlay for mask areas
                overlay = cv2.addWeighted(video_disp, 0.7, mask_rgb, 0.3, 0)
                full_frame[:, self.sidebar_width:] = overlay
            
            if self.feedback_timer > 0:
                self.feedback_timer -= 1
                if self.feedback_timer == 0:
                    self.feedback = None
            
            cv2.imshow(self.window_name, full_frame)
            key = cv2.waitKey(wait_time) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):
                if not (self.waiting_for_click or self.waiting_for_mcq):
                    self.is_playing = not self.is_playing
                    self.status = "Playing" if self.is_playing else "Paused"
                    print(f"DEBUG: Video {'resumed' if self.is_playing else 'paused'}")
            elif key in [ord('+'), ord('=')]:
                self.speed = min(self.speed + 0.5, 10.0)
            elif key in [ord('-'), ord('_')]:
                self.speed = max(self.speed - 0.5, 0.5)
            elif key == ord('f'):
                self.fullscreen = not self.fullscreen
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if self.fullscreen else cv2.WINDOW_NORMAL)
            elif key == ord('h'):
                self.show_sidebar = not self.show_sidebar
            elif key == ord('m'):
                self.marker_display = not self.marker_display
            elif key == ord('n'):
                if self.next_marker_idx < len(self.markers):
                    self.jump_to_marker(self.next_marker_idx)
            elif key == ord('p'):
                if self.next_marker_idx > 0:
                    self.jump_to_marker(self.next_marker_idx - 1)
            elif key == ord('o'):
                self.mask_overlay_on = not self.mask_overlay_on
            elif key == ord('d'):
                self.debug_mode = not self.debug_mode
                print(f"DEBUG: Debug mode {'enabled' if self.debug_mode else 'disabled'}")
            
            # MCQ controls
            elif self.waiting_for_mcq:
                if key == ord('w'):  # Move up in MCQ
                    self.selected_mcq_option = max(0, self.selected_mcq_option - 1)
                elif key == ord('s'):  # Move down in MCQ
                    self.selected_mcq_option = min(len(self.mcq_options) - 1, self.selected_mcq_option + 1)
                elif key == 13:  # Enter - select current option
                    self.handle_mcq_answer(self.selected_mcq_option)
                elif key in [ord('1'), ord('2'), ord('3'), ord('4'), ord('5')]:  # Direct selection
                    option_idx = key - ord('1')
                    if 0 <= option_idx < len(self.mcq_options):
                        self.handle_mcq_answer(option_idx)
        
        self.cap.release()
        cv2.destroyAllWindows()
        print(f"DEBUG: Test completed. Final scores - Correct: {self.correct}, Incorrect: {self.incorrect}")
        print(f"DEBUG: Polyp detection - Detected: {self.polyps_detected}, Missed: {self.polyps_missed}")

def run_perception_test():
    PerceptionTestV2().run()

if __name__ == "__main__":
    run_perception_test() 