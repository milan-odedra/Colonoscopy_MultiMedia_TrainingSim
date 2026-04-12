import cv2
import numpy as np
import time
import csv
from pathlib import Path
import re
import os

# Use relative paths for video and markers
BASE_DIR = Path(__file__).parent
VIDEO_PATH = BASE_DIR / "videos" / "Without annotations (edited).mp4"
MARKERS_PATH = BASE_DIR / "data" / "new_perception_markers.csv"

class PerceptionTestV2:
    def __init__(self):
        self.window_name = "Perception Test V2"
        self.sidebar_width = 540  # Match the actual sidebar overlay width
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
        self.resume_frame = None  # Store frame to resume after accuracy click
        self.resume_time = None   # Store time to resume after accuracy click
        self.testing_mode = True  # Set to False for final version

        # Debug: Print loaded markers
        print(f"Loaded {len(self.markers)} markers:")
        for i, marker in enumerate(self.markers):
            print(f"  Marker {i}: time={marker['start_time']}s, type={marker['question_type']}, question={marker['question_text']}")

        self.polyp_report_fields = [
            'site', 'size_estimate', 'paris_classification', 
            'nice_classification', 'likely_histology', 'excision_technique'
        ]
        self.waiting_for_polyp_report = False
        self.polyp_report_data = {}
        self.current_polyp_number = 0
        self.polyp_report_field_index = 0
        self.polyp_report_input = ""

        # Add this to __init__
        self.polyp_report_dropdown_options = {
            'site': [
                'Rectum', 'Sigmoid colon', 'Descending colon', 'Transverse colon', 'Ascending colon', 'Caecum'
            ],
            'paris_classification': [
                '0-Ip (Pedunculated)', '0-Is (Sessile)', '0-IIa (Flat elevated)', '0-IIb (Completely flat)', '0-IIc (Flat depressed)', '0-III (Excavated)'
            ],
            'nice_classification': [
                'Type 1 (Hyperplastic)', 'Type 2 (Adenoma/SSA/P)', 'Type 3 (Deep submucosal invasive cancer)'
            ],
            'likely_histology': [
                'Hyperplastic', 'Adenoma', 'Sessile serrated lesion', 'Traditional serrated adenoma', 'Carcinoma'
            ],
            'excision_technique': [
                'Cold snare', 'Hot snare', 'EMR', 'ESD', 'Biopsy forceps', 'Surgery'
            ],
            'size_estimate': [
                '0–5 mm', '5–10 mm', '10–15 mm', '15–20 mm', '20–25 mm', '25+ mm'
            ]
        }
        self.polyp_report_dropdown_indices = {field: 0 for field in self.polyp_report_fields}

        # --- Add to __init__ ---
        self.polyp_report_option_boxes = {}  # For clickable option rectangles
        self.polyp_report_submit_box = None  # For clickable submit button
        self.polyp_report_expanded_field = None  # Track which field's dropdown is expanded

        # Set sensible defaults for dropdowns
        for field in self.polyp_report_fields:
            options = self.polyp_report_dropdown_options.get(field)
            if options:
                self.polyp_report_data[field] = options[0]
            else:
                self.polyp_report_data[field] = ''

        results_dir = BASE_DIR / 'data' / 'results'
        os.makedirs(results_dir, exist_ok=True)
        self.results_csv_path = results_dir / 'perception_test_results.csv'
        self.results_csv_header_written = False

        self.active_polyp_number = None
        self.active_polyp_report_data = None
        self.active_polyp_report_dropdown_indices = None

        # --- Score popup state ---
        self.score_popup_message = None
        self.score_popup_color = (0,255,0)
        self.score_popup_timer = 0
        self.score_popup_max_timer = 45  # ~0.75s at 60fps
        self.score_popup_scale = 1.0

        # --- Jump mode state ---
        self.jump_mode = False
        self.jump_input = ""
        self.jump_timer = 0
        self.jump_max_timer = 180  # 3 seconds to enter number

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

    def setup_polyp_report(self, marker):
        """Setup polyp report form"""
        match = re.search(r'Polyp (\d+)', marker['question_text'])
        if match:
            self.current_polyp_number = int(match.group(1))
        else:
            self.current_polyp_number = 0
        
        # Only reset data if we don't have any active polyp report data
        # This preserves answers until the user submits the report
        if self.active_polyp_report_data is None:
            self.polyp_report_dropdown_indices = {field: 0 for field in self.polyp_report_fields}
            self.polyp_report_data = {}
            for field in self.polyp_report_fields:
                options = self.polyp_report_dropdown_options.get(field)
                if options:
                    self.polyp_report_data[field] = options[0]
                    self.polyp_report_dropdown_indices[field] = 0
                else:
                    self.polyp_report_data[field] = ''
            self.active_polyp_number = self.current_polyp_number
            self.active_polyp_report_data = self.polyp_report_data.copy()
            self.active_polyp_report_dropdown_indices = self.polyp_report_dropdown_indices.copy()
        else:
            # Restore previous state for the current polyp report
            if self.active_polyp_report_data is not None:
                self.polyp_report_data = self.active_polyp_report_data.copy()
            if self.active_polyp_report_dropdown_indices is not None:
                self.polyp_report_dropdown_indices = self.active_polyp_report_dropdown_indices.copy()
            self.active_polyp_number = self.current_polyp_number
        
        self.polyp_report_field_index = 0
        self.polyp_report_input = ""
        self.waiting_for_polyp_report = True
        return True

    def complete_polyp_report(self):
        """Complete and save polyp report"""
        print(f"DEBUG: Polyp {self.current_polyp_number} Report Completed:")
        for field, value in self.polyp_report_data.items():
            print(f"  {field.replace('_', ' ').title()}: {value}")
        # Log to CSV
        row = {
            'type': 'polyp_report',
            'polyp_number': self.current_polyp_number,
            'video_time': self.format_time(self.time_sec),
        }
        for field in self.polyp_report_fields:
            options = self.polyp_report_dropdown_options.get(field)
            idx_to_use = self.polyp_report_dropdown_indices.get(field, 0)
            if idx_to_use is None or not isinstance(idx_to_use, int):
                idx_to_use = 0
            idx_to_use = int(idx_to_use)
            if options:
                value_to_log = options[idx_to_use] if 0 <= idx_to_use < len(options) else options[0]
                row[field] = value_to_log
            else:
                row[field] = self.polyp_report_data[field]
        self.log_result(row)
        self.feedback = f"Polyp {self.current_polyp_number} Report Completed!"
        self.feedback_timer = 90
        self.waiting_for_polyp_report = False
        self.advance_to_next_marker()
        self.active_polyp_number = None
        self.active_polyp_report_data = None
        self.active_polyp_report_dropdown_indices = None

    def get_field_display_name(self, field):
        display_names = {
            'site': 'Site',
            'size_estimate': 'Size Estimate (mm)',
            'paris_classification': 'Paris Classification',
            'nice_classification': 'NICE Classification',
            'likely_histology': 'Likely Histology',
            'excision_technique': 'Excision Technique'
        }
        return display_names.get(field, field)

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
                print(f"  - Correct answer: {(self.correct_option or 0) + 1}")
                self.waiting_for_mcq = True
            else:
                print(f"DEBUG: Failed to setup MCQ for {question_type} question {marker_idx}")
                self.advance_to_next_marker()
                return False
        
        elif question_type == 'polyp_report':
            self.is_playing = False
            self.status = "Paused"
            self.current_marker = marker
            if self.setup_polyp_report(marker):
                print(f"DEBUG: Polyp report setup for {marker['question_text']}")
                return True
            else:
                print(f"DEBUG: Failed to setup polyp report")
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
            self.show_score_popup("Missed!", (0,0,255))
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

        self.waiting_for_polyp_report = False
        self.polyp_report_data = {}
        self.polyp_report_input = ""

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
        # === DRAW MENU/FORM IN OVERLAY REGION ===
        overlay_x = 0
        overlay_y = 0
        overlay_width = self.sidebar_width  # Use the same sidebar width as everywhere else
        overlay_height = 775
        # Draw semi-transparent black background
        overlay_color = (50, 50, 50)  # Black
        alpha = 1  # 0 = transparent, 1 = opaque
        menu_overlay = frame.copy()
        cv2.rectangle(menu_overlay, (overlay_x, overlay_y), (overlay_x + overlay_width, overlay_height), overlay_color, -1)
        cv2.addWeighted(menu_overlay, alpha, frame, 1 - alpha, 0, frame)
        # Start drawing inside overlay region
        y = overlay_y + 30
        x = overlay_x + 20
        # Show DEBUG MODE banner if enabled
        if self.debug_mode:
            cv2.putText(frame, "DEBUG MODE ON", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 2)
            y += 35
        cv2.putText(frame, "Perception Test V2", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
        y += 40
        cv2.putText(frame, f"Status: {self.status}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        y += 30
        cv2.putText(frame, f"Time: {self.format_time(self.time_sec)}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        y += 30
        cv2.putText(frame, f"Time (ms): {self.time_sec:.3f}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 1)
        y += 30
        cv2.putText(frame, f"Speed: {self.speed:.1f}x", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        y += 30
        cv2.putText(frame, f"Next Marker: {self.next_marker_idx}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 1)
        y += 30
        if self.polyp_detection_active:
            cv2.putText(frame, "POLYP DETECTION ACTIVE", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            y += 25
            if not self.polyp_timing_point_awarded:
                cv2.putText(frame, "Click when you see a polyp!", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1)
                y += 25
                cv2.putText(frame, "Point 1: Timing", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
            elif self.waiting_for_polyp_accuracy_click:
                cv2.putText(frame, "Now click on the polyp area!", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 1)
                y += 25
                cv2.putText(frame, "Point 2: Accuracy", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
                y += 20
                cv2.putText(frame, "Mask overlay: ON", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)
            y += 30
            if self.debug_mode:
                y += 10
                cv2.putText(frame, f"Window: {self.polyp_window_start:.1f}s - {self.polyp_window_end:.1f}s", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
                y += 20
                cv2.putText(frame, f"Time left: {max(0, self.polyp_window_end - self.time_sec):.1f}s", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
                y += 20
        elif self.current_marker:
            cv2.putText(frame, f"Type: {self.current_marker['question_type'].upper()}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,255), 1)
            y += 25
            cv2.putText(frame, f"Marker: {self.format_time(float(self.current_marker['start_time']))}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 1)
            y += 25
            question = self.current_marker['question_text']
            if len(question) > 40:
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
                    cv2.putText(frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
                    y += 20
            else:
                cv2.putText(frame, question, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
                y += 25
            if self.waiting_for_mcq and self.mcq_options:
                y += 10
                cv2.putText(frame, "Options:", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
                y += 25
                for i, option in enumerate(self.mcq_options):
                    color = (0,255,0) if i == self.selected_mcq_option else (200,200,200)
                    prefix = f"{i+1}. "
                    if i == self.selected_mcq_option:
                        prefix = f"> {i+1}. "
                    cv2.putText(frame, prefix + option, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
                    y += 22
                y += 10
                cv2.putText(frame, "Use 1-5 keys or W/S + Enter", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)
                y += 20
            elif self.waiting_for_click:
                y += 10
                cv2.putText(frame, "Click on the lumen!", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            y += 30
        # Polyp report form
        if self.waiting_for_polyp_report:
            y += 10
            cv2.putText(frame, f"Polyp {self.current_polyp_number} Report:", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            y += 30
            self.polyp_report_option_boxes = {}
            for i, field in enumerate(self.polyp_report_fields):
                color = (0,255,0) if i == self.polyp_report_field_index else (200,200,200)
                prefix = "> " if i == self.polyp_report_field_index else "  "
                field_name = self.get_field_display_name(field)
                current_value = self.polyp_report_data[field]
                options = self.polyp_report_dropdown_options.get(field)
                # Measure question text width
                question_text = f"{prefix}{field_name}: "
                (q_w, q_h), _ = cv2.getTextSize(question_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                bar_x1, bar_y1 = x, y-18
                bar_x2 = x + q_w + 40  # Add gap for answer
                bar_y2 = y+10
                cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (60,60,60), -1)
                cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (100,100,100), 1)
                cv2.putText(frame, question_text, (x+5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
                # Draw dropdown arrow if options
                if options:
                    arrow = 'v' if self.polyp_report_expanded_field == i else '>'
                    cv2.putText(frame, arrow, (x+q_w+20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,0), 1)
                self.polyp_report_option_boxes[(i, -1)] = (bar_x1, bar_y1, bar_x2, bar_y2)
                # Draw value or expanded dropdown
                if options:
                    if self.polyp_report_expanded_field == i:
                        # Calculate dropdown height
                        dropdown_height = len(options) * 28
                        # If not enough space below, draw above
                        if y + 10 + dropdown_height > overlay_y + overlay_height:
                            opt_y = y - dropdown_height
                        else:
                            opt_y = y + 10
                        for idx, opt in enumerate(options):
                            (text_w, text_h), _ = cv2.getTextSize(opt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                            box_w, box_h = text_w + 20, 28
                            box_color = (0,255,255) if idx == int(self.polyp_report_dropdown_indices.get(field, 0)) else (80,80,80)
                            text_color = (0,0,0) if idx == int(self.polyp_report_dropdown_indices.get(field, 0)) else (200,200,200)
                            if idx == int(self.polyp_report_dropdown_indices.get(field, 0)):
                                overlay_box = frame.copy()
                                cv2.rectangle(overlay_box, (x, opt_y), (x+box_w, opt_y+box_h), box_color, -1)
                                alpha = 0.5
                                cv2.addWeighted(overlay_box, alpha, frame, 1 - alpha, 0, frame)
                            else:
                                cv2.rectangle(frame, (x, opt_y), (x+box_w, opt_y+box_h), box_color, -1)
                            cv2.rectangle(frame, (x, opt_y), (x+box_w, opt_y+box_h), (100,100,100), 1)
                            cv2.putText(frame, opt, (x+10, opt_y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
                            self.polyp_report_option_boxes[(i, idx)] = (x, opt_y, x+box_w, opt_y+box_h)
                            opt_y += box_h
                        y = y + 10 + dropdown_height if y + 10 + dropdown_height <= overlay_y + overlay_height else y + 10
                    else:
                        # Show current value with gap
                        idx_to_use = self.polyp_report_dropdown_indices.get(field, 0)
                        if idx_to_use is None or not isinstance(idx_to_use, int):
                            idx_to_use = 0
                        idx_to_use = int(idx_to_use)
                        value_to_show = options[idx_to_use] if options and isinstance(idx_to_use, int) and 0 <= idx_to_use < len(options) else (options[0] if options else '')
                        if value_to_show == '???':
                            value_to_show = ''
                        cv2.putText(frame, f"{value_to_show}", (x+q_w+45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
                        y += 30
                else:
                    # Free text
                    display_value = self.polyp_report_input if (i == self.polyp_report_field_index) else current_value
                    cv2.putText(frame, f"{display_value}_", (x+q_w+45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
                    y += 30
            # Draw submit button
            btn_x, btn_y, btn_w, btn_h = x+200, y+10, 180, 40
            self.polyp_report_submit_box = (btn_x, btn_y, btn_x+btn_w, btn_y+btn_h)
            cv2.rectangle(frame, (btn_x, btn_y), (btn_x+btn_w, btn_y+btn_h), (0,200,0), -1)
            cv2.rectangle(frame, (btn_x, btn_y), (btn_x+btn_w, btn_y+btn_h), (0,100,0), 2)
            cv2.putText(frame, "Submit Report", (btn_x+10, btn_y+28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            y += btn_h + 20
        cv2.putText(frame, f"Correct: {self.correct or 0}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 1)
        y += 25
        cv2.putText(frame, f"Incorrect: {self.incorrect or 0}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 1)
        y += 25
        cv2.putText(frame, f"Polyps Detected: {self.polyps_detected or 0}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 1)
        y += 25
        cv2.putText(frame, f"Polyps Missed: {self.polyps_missed or 0}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 1)
        y += 40
        cv2.putText(frame, "Controls:", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 1)
        y += 25
        controls = [
            "Space: Play/Pause",
            "+/-: Speed Up/Down",
            "F: Fullscreen",
            "M: Toggle Marker Info",
            "N/P: Next/Previous Marker",
            "J: Jump to Marker",
            "O: Toggle Mask Overlay",
            "D: Toggle Debug Mode",
            "W/S: Navigate MCQ",
            "Enter: Select MCQ",
            "Q: Quit"
        ]
        controls_x = x
        controls_y = y
        line_height = 18
        controls_max_y = overlay_y + overlay_height - 20
        for ctrl in controls:
            if controls_y + line_height > controls_max_y:
                break  # Don't overflow sidebar
            cv2.putText(frame, ctrl, (controls_x, controls_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200,200,200), 1)
            controls_y += line_height
        y = max(y, controls_y)
        if self.debug_mode and self.last_click_coords and (self.waiting_for_click or self.polyp_detection_active):
            y += 15
            cv2.putText(frame, f"Click: {self.last_click_coords}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 1)
        if self.feedback and self.feedback_timer > 0:
            y += 20
            color = (0,255,0) if "Correct" in self.feedback or "Complete" in self.feedback else (0,0,255)
            cv2.putText(frame, self.feedback, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        # Draw jump mode indicator
        if self.jump_mode:
            y += 20
            cv2.putText(frame, f"JUMP MODE: {self.jump_input}_", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            y += 25
            cv2.putText(frame, "Type marker number (0-" + str(len(self.markers)-1) + ") and press Enter", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
            y += 20
            cv2.putText(frame, "Press Escape to cancel", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
        return frame

    def handle_mcq_answer(self, selected_idx):
        """Handle MCQ answer selection"""
        correct_option_display = (self.correct_option or 0) + 1
        selected_idx_display = (selected_idx or 0) + 1
        is_correct = selected_idx == self.correct_option
        if is_correct:
            self.correct += 1
            self.feedback = "Correct!"
            print(f"DEBUG: Correct MCQ answer! Selected: {selected_idx_display}, Correct: {correct_option_display}")
        else:
            self.incorrect += 1
            self.feedback = f"Incorrect! Answer was {correct_option_display}"
            print(f"DEBUG: Incorrect MCQ answer! Selected: {selected_idx_display}, Correct: {correct_option_display}")
        self.feedback_timer = 90  # Show feedback longer for MCQ
        # Log to CSV
        row = {
            'type': 'mcq',
            'video_time': self.format_time(self.time_sec),
            'question': self.current_marker['question_text'] if self.current_marker else '',
            'selected_option': self.mcq_options[selected_idx] if self.mcq_options and selected_idx is not None and 0 <= selected_idx < len(self.mcq_options) else '',
            'correct_option': self.mcq_options[self.correct_option] if self.mcq_options and self.correct_option is not None and 0 <= self.correct_option < len(self.mcq_options) else '',
            'is_correct': is_correct
        }
        self.log_result(row)
        self.advance_to_next_marker()

    def extract_time_from_mask_path(self, mask_path):
        """Extracts the best frame time in seconds from a mask filename like 'Polyp-6_frame_12_30_600_mask.png' or 'frame_12_30_600.png'. Returns 0 if not found or mask_path is None/empty."""
        if not mask_path or not isinstance(mask_path, str):
            return 0
        filename = os.path.basename(mask_path)
        # Match frame_12_30_600 or Polyp-6_frame_12_30_600_mask.png
        match = re.search(r'frame_(\d{2})_(\d{2})(?:_(\d{1,3}))?', filename)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            ms = int(match.group(3)) if match.group(3) else 0
            return minutes * 60 + seconds + ms / 1000.0
        return 0

    def handle_polyp_click(self, x, y):
        """Handle polyp detection click - 2-point system with jump to best frame"""
        if not self.polyp_detection_active or self.current_marker is None:
            return
        print(f"DEBUG: Polyp click at x: {x}, y: {y}")
        # Check if click is within time window
        if self.polyp_window_start <= self.time_sec <= self.polyp_window_end:
            if not self.polyp_timing_point_awarded:
                # First click - award timing point
                self.polyp_timing_point_awarded = True
                self.correct += 1
                self.feedback = "Timing correct! (+1 point) Now click on the polyp area"
                self.show_score_popup("+1 Point! Polyp Spotted", (0,200,255))
                print(f"DEBUG: Timing point awarded! Total correct: {self.correct}")
                # Pause video and show mask overlay for accuracy click
                self.is_playing = False
                self.status = "Paused"
                self.waiting_for_polyp_accuracy_click = True
                self.mask_overlay_on = True  # Force mask overlay on
                self.feedback_timer = 120  # Show message longer
                # Store resume frame/time
                self.resume_frame = self.current_frame
                self.resume_time = self.time_sec
                # Jump to best frame (use mask_path time if available)
                mask_path = self.current_marker.get('mask_path', '') if self.current_marker else ''
                best_frame_time = self.extract_time_from_mask_path(mask_path)
                if best_frame_time == 0:
                    # Fallback to start_time if extraction fails
                    start_time_val = self.current_marker.get('start_time', 0) if self.current_marker else 0
                    try:
                        best_frame_time = float(start_time_val)
                    except Exception:
                        best_frame_time = 0
                self.current_frame = int(best_frame_time * self.fps)
                self.time_sec = best_frame_time
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                print(f"DEBUG: Jumped to best frame for mask: {best_frame_time}s (frame {self.current_frame})")
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
                            self.show_score_popup("+1 Point! Accuracy", (0,200,255))
                            print(f"DEBUG: Accuracy point awarded! Total correct: {self.correct}")
                        else:
                            self.incorrect += 1
                            self.feedback = "Accuracy missed - click was outside polyp area"
                            self.show_score_popup("Missed!", (0,0,255))
                            print(f"DEBUG: Accuracy point missed")
                    else:
                        self.incorrect += 1
                        self.feedback = "Click outside valid area"
                        self.show_score_popup("Missed!", (0,0,255))
                else:
                    # No mask available - just award point for completing the process
                    self.polyp_accuracy_point_awarded = True
                    self.correct += 1
                    self.polyps_detected += 1
                    self.feedback = "Accuracy point awarded (no mask validation)"
                    self.show_score_popup("+1 Point! Accuracy", (0,200,255))
                    print(f"DEBUG: Accuracy point awarded (no mask)")
                
                # End polyp detection and resume video from where user left off
                self.feedback_timer = 60
                self.polyp_detection_active = False
                self.waiting_for_polyp_accuracy_click = False
                self.polyp_timing_point_awarded = False
                self.polyp_accuracy_point_awarded = False
                self.advance_to_next_marker()  # Fix: advance marker after accuracy click
                # Resume from stored frame/time
                if self.resume_frame is not None and self.resume_time is not None:
                    self.current_frame = self.resume_frame
                    self.time_sec = self.resume_time
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                    print(f"DEBUG: Resuming video from {self.resume_time}s (frame {self.resume_frame})")
                self.is_playing = True
                self.status = "Playing"
                self.resume_frame = None
                self.resume_time = None
        else:
            print(f"DEBUG: Click outside time window ({self.polyp_window_start}-{self.polyp_window_end})")

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            x_adj = x  # Do not subtract sidebar width; sidebar is just an overlay
            y_adj = y
            self.last_click_coords = (x_adj, y_adj)
            
            if self.waiting_for_click and self.mask is not None:
                # Handle lumen click
                print(f"DEBUG: Lumen click at x: {x_adj}, y: {y_adj}")
                is_correct = False
                if 0 <= x_adj < self.mask.shape[1] and 0 <= y_adj < self.mask.shape[0]:
                    if self.mask[y_adj, x_adj] == 255:
                        self.correct += 1
                        self.feedback = "Correct!"
                        print(f"DEBUG: Correct lumen click! Total correct: {self.correct}")
                        is_correct = True
                        self.show_score_popup("+1 Point! Lumen", (0,255,0))
                    else:
                        self.incorrect += 1
                        self.feedback = "Incorrect!"
                        print(f"DEBUG: Incorrect lumen click! Total incorrect: {self.incorrect}")
                        self.show_score_popup("Missed!", (0,0,255))
                    self.feedback_timer = 60
                    # Log to CSV
                    row = {
                        'type': 'lumen',
                        'video_time': self.format_time(self.time_sec),
                        'question': self.current_marker['question_text'] if self.current_marker else '',
                        'click_x': x_adj,
                        'click_y': y_adj,
                        'is_correct': is_correct
                    }
                    self.log_result(row)
                    self.advance_to_next_marker()
                    
            elif self.polyp_detection_active:
                # Handle polyp detection click (2-point system)
                self.handle_polyp_click(x_adj, y_adj)
            
            # --- In mouse_callback, handle clicks on options and submit button ---
            elif self.waiting_for_polyp_report:
                # Check for field label click (expand/collapse)
                for (i, idx), (x1, y1, x2, y2) in self.polyp_report_option_boxes.items():
                    if idx == -1 and x1 <= x < x2 and y1 <= y < y2:
                        # Toggle expand/collapse
                        if self.polyp_report_expanded_field == i:
                            self.polyp_report_expanded_field = None
                        else:
                            self.polyp_report_expanded_field = i
                        return
                # If a dropdown is expanded, check for option click
                if self.polyp_report_expanded_field is not None:
                    expanded_idx = self.polyp_report_expanded_field
                    for (i, idx), (x1, y1, x2, y2) in self.polyp_report_option_boxes.items():
                        if i == expanded_idx and idx >= 0 and x1 <= x < x2 and y1 <= y < y2:
                            field = self.polyp_report_fields[i]
                            options = self.polyp_report_dropdown_options.get(field)
                            if options:
                                idx_to_use = idx if idx is not None and isinstance(idx, int) else 0
                                if 0 <= idx_to_use < len(options):
                                    self.polyp_report_dropdown_indices[field] = idx_to_use
                                    self.polyp_report_data[field] = options[idx_to_use]
                                self.polyp_report_expanded_field = None
                                return
                # Check for submit button click
                if self.polyp_report_submit_box:
                    x1, y1, x2, y2 = self.polyp_report_submit_box
                    if x1 <= x < x2 and y1 <= y < y2:
                        # Save all dropdowns, free text
                        for i, field in enumerate(self.polyp_report_fields):
                            options = self.polyp_report_dropdown_options.get(field)
                            if options:
                                idx_to_use = self.polyp_report_dropdown_indices.get(field, 0)
                                if idx_to_use is None or not isinstance(idx_to_use, int):
                                    idx_to_use = 0
                                self.polyp_report_data[field] = options[idx_to_use]
                            else:
                                self.polyp_report_data[field] = self.polyp_report_input if i == self.polyp_report_field_index else self.polyp_report_data[field]
                        self.complete_polyp_report()
                        return

    def log_result(self, row_dict):
        write_header = not self.results_csv_path.exists() or not self.results_csv_header_written
        with open(self.results_csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=row_dict.keys())
            if write_header:
                writer.writeheader()
                self.results_csv_header_written = True
            writer.writerow(row_dict)
        print(f"[RESULT LOGGED] {row_dict}")

    # --- Add a helper to trigger the popup ---
    def show_score_popup(self, message, color=(0,255,0)):
        self.score_popup_message = message
        self.score_popup_color = color
        self.score_popup_timer = self.score_popup_max_timer
        self.score_popup_scale = 1.0

    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.original_width, self.original_height)
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
            
            full_frame = frame.copy()
            # Show mask overlay for lumen questions (not for polyp detection)
            if self.mask is not None and self.mask_overlay_on and self.waiting_for_click:
                mask_rgb = np.zeros((self.display_video_height, self.display_video_width, 3), dtype=np.uint8)
                mask_rgb[self.mask == 255] = [0, 255, 255]  # Yellow overlay for mask areas
                full_frame = cv2.addWeighted(full_frame, 0.7, mask_rgb, 0.3, 0)
            # Show mask overlay for polyp detection (ADDED!)
            elif self.mask is not None and self.mask_overlay_on and self.polyp_detection_active:
                mask_rgb = np.zeros((self.display_video_height, self.display_video_width, 3), dtype=np.uint8)
                mask_rgb[self.mask == 255] = [0, 255, 255]  # Yellow overlay for mask areas
                full_frame = cv2.addWeighted(full_frame, 0.7, mask_rgb, 0.3, 0)
            # Show mask overlay for polyp accuracy phase (2-point system)
            elif self.mask is not None and self.waiting_for_polyp_accuracy_click:
                mask_rgb = np.zeros((self.display_video_height, self.display_video_width, 3), dtype=np.uint8)
                mask_rgb[self.mask == 255] = [0, 255, 255]  # Yellow overlay for mask areas
                full_frame = cv2.addWeighted(full_frame, 0.7, mask_rgb, 0.3, 0)
            # Always draw the sidebar last
            full_frame = self.draw_sidebar(full_frame)

            # --- Draw score popup if active ---
            if self.score_popup_timer > 0 and self.score_popup_message:
                alpha = min(1.0, self.score_popup_timer / self.score_popup_max_timer)
                scale = 1.0 + 0.5 * (1 - alpha)  # Pop effect: grows then shrinks
                font_scale = 2.5 * scale
                thickness = int(6 * scale)
                (text_w, text_h), _ = cv2.getTextSize(self.score_popup_message, cv2.FONT_HERSHEY_DUPLEX, font_scale, thickness)
                center_x = self.display_video_width // 2 - text_w // 2
                center_y = self.display_video_height // 2 + text_h // 2
                overlay = full_frame.copy()
                cv2.putText(overlay, self.score_popup_message, (center_x, center_y), cv2.FONT_HERSHEY_DUPLEX, font_scale, self.score_popup_color, thickness, cv2.LINE_AA)
                # Blend with alpha for fade out
                cv2.addWeighted(overlay, alpha, full_frame, 1 - alpha, 0, full_frame)
                self.score_popup_timer -= 1
                if self.score_popup_timer == 0:
                    self.score_popup_message = None
            # Only show feedback in sidebar if popup is not active
            if self.score_popup_timer == 0:
                if self.feedback_timer > 0:
                    self.feedback_timer -= 1
                    if self.feedback_timer == 0:
                        self.feedback = None
            cv2.imshow(self.window_name, full_frame)
            key = cv2.waitKey(wait_time) & 0xFF
            
            # Handle jump mode input
            if self.jump_mode:
                if key == 27:  # Escape - cancel jump mode
                    self.jump_mode = False
                    self.jump_input = ""
                    self.jump_timer = 0
                elif key == 13:  # Enter - execute jump
                    try:
                        marker_idx = int(self.jump_input)
                        if 0 <= marker_idx < len(self.markers):
                            self.jump_to_marker(marker_idx)
                            print(f"DEBUG: Jumped to marker {marker_idx}")
                        else:
                            print(f"DEBUG: Invalid marker index: {marker_idx}")
                    except ValueError:
                        print(f"DEBUG: Invalid input: {self.jump_input}")
                    self.jump_mode = False
                    self.jump_input = ""
                    self.jump_timer = 0
                elif key == 8:  # Backspace
                    if self.jump_input:
                        self.jump_input = self.jump_input[:-1]
                elif 48 <= key <= 57:  # Number keys 0-9
                    if len(self.jump_input) < 3:  # Limit to 3 digits
                        self.jump_input += chr(key)
                self.jump_timer = self.jump_max_timer
                continue  # Skip other key processing in jump mode
            
            if key == ord('q'):
                break
            elif key == ord(' '):
                if not (self.waiting_for_click or self.waiting_for_mcq):
                    self.is_playing = not self.is_playing
                    self.status = "Playing" if self.is_playing else "Paused"
                    print(f"DEBUG: Video {'resumed' if self.is_playing else 'paused'}")
            elif key == ord('j'):
                if not self.jump_mode:
                    self.jump_mode = True
                    self.jump_input = ""
                    self.jump_timer = self.jump_max_timer
                    print("DEBUG: Entered jump mode - type marker number and press Enter")
            elif key in [ord('+'), ord('=')]:
                self.speed = min(self.speed + 0.5, 10.0)
            elif key in [ord('-'), ord('_')]:
                self.speed = max(self.speed - 0.5, 0.5)
            elif key == ord('f'):
                self.fullscreen = not self.fullscreen
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if self.fullscreen else cv2.WINDOW_NORMAL)
            elif key == ord('m'):
                self.marker_display = not self.marker_display
            elif key == ord('n'):
                if self.testing_mode:
                    # In testing mode, always allow next marker
                    if self.next_marker_idx < len(self.markers):
                        self.jump_to_marker(self.next_marker_idx)
                elif self.next_marker_idx < len(self.markers) and not (self.waiting_for_click or self.waiting_for_mcq or self.polyp_detection_active):
                    self.jump_to_marker(self.next_marker_idx)
            elif key == ord('p'):
                if self.testing_mode:
                    # In testing mode, always allow previous marker
                    if self.next_marker_idx > 0:
                        self.jump_to_marker(self.next_marker_idx - 1)
                elif self.next_marker_idx > 0 and not (self.waiting_for_click or self.waiting_for_mcq or self.polyp_detection_active):
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
            
            # Polyp report controls
            elif self.waiting_for_polyp_report:
                if key == ord('w'):
                    self.polyp_report_field_index = max(0, self.polyp_report_field_index - 1)
                    field = self.polyp_report_fields[self.polyp_report_field_index]
                    self.polyp_report_input = self.polyp_report_data[field]
                elif key == ord('s'):
                    self.polyp_report_field_index = min(len(self.polyp_report_fields) - 1, self.polyp_report_field_index + 1)
                    field = self.polyp_report_fields[self.polyp_report_field_index]
                    self.polyp_report_input = self.polyp_report_data[self.polyp_report_fields[self.polyp_report_field_index]]
                elif key == ord('a'):
                    field = self.polyp_report_fields[self.polyp_report_field_index]
                    options = self.polyp_report_dropdown_options.get(field)
                    if options:
                        self.polyp_report_dropdown_indices[field] = (self.polyp_report_dropdown_indices.get(field, 0) - 1) % len(options)
                elif key == ord('d'):
                    field = self.polyp_report_fields[self.polyp_report_field_index]
                    options = self.polyp_report_dropdown_options.get(field)
                    if options:
                        self.polyp_report_dropdown_indices[field] = (self.polyp_report_dropdown_indices.get(field, 0) + 1) % len(options)
                elif key == 13:
                    field = self.polyp_report_fields[self.polyp_report_field_index]
                    options = self.polyp_report_dropdown_options.get(field)
                    if options:
                        idx_to_use = self.polyp_report_dropdown_indices.get(field, 0)
                        if idx_to_use is None or not isinstance(idx_to_use, int):
                            idx_to_use = 0
                        self.polyp_report_data[field] = options[idx_to_use]
                    else:
                        self.polyp_report_data[field] = self.polyp_report_input
                    if self.polyp_report_field_index < len(self.polyp_report_fields) - 1:
                        self.polyp_report_field_index += 1
                        field = self.polyp_report_fields[self.polyp_report_field_index]
                        self.polyp_report_input = self.polyp_report_data[field]
                elif key == 9:
                    field = self.polyp_report_fields[self.polyp_report_field_index]
                    options = self.polyp_report_dropdown_options.get(field)
                    if options:
                        idx_to_use = self.polyp_report_dropdown_indices.get(field, 0)
                        if idx_to_use is None or not isinstance(idx_to_use, int):
                            idx_to_use = 0
                        self.polyp_report_data[field] = options[idx_to_use]
                    else:
                        self.polyp_report_data[field] = self.polyp_report_input
                    self.complete_polyp_report()
                elif key == 27:
                    self.polyp_report_input = ""
                elif key == 8:
                    if self.polyp_report_input:
                        self.polyp_report_input = self.polyp_report_input[:-1]
                elif 32 <= key <= 126:
                    field = self.polyp_report_fields[self.polyp_report_field_index]
                    options = self.polyp_report_dropdown_options.get(field)
                    if not options and self.polyp_report_expanded_field is None:
                        self.polyp_report_input += chr(key)
        
            # Update jump timer
            if self.jump_timer > 0:
                self.jump_timer -= 1
                if self.jump_timer == 0:
                    self.jump_mode = False
                    self.jump_input = ""
        
        self.cap.release()
        cv2.destroyAllWindows()
        print(f"DEBUG: Test completed. Final scores - Correct: {self.correct}, Incorrect: {self.incorrect}")
        print(f"DEBUG: Polyp detection - Detected: {self.polyps_detected}, Missed: {self.polyps_missed}")

def run_perception_test():
    PerceptionTestV2().run()

if __name__ == "__main__":
    run_perception_test() 