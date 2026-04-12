#!/usr/bin/env python3
"""
Test script for 2-point polyp detection system
"""

import cv2
import numpy as np
import csv
from pathlib import Path

# Use test CSV with only working polyp
BASE_DIR = Path(__file__).parent
VIDEO_PATH = BASE_DIR / "videos" / "Without annotations (edited).mp4"
MARKERS_PATH = BASE_DIR / "data" / "test_polyp_only.csv"

class TwoPointPolypTest:
    def __init__(self):
        self.window_name = "2-Point Polyp Test"
        self.sidebar_width = 400
        self.status = "Paused"
        self.time_sec = 0.0
        self.speed = 1.0
        self.is_playing = False
        self.show_sidebar = True
        self.correct = 0
        self.incorrect = 0
        self.current_marker = None
        self.markers = self.load_markers()
        self.current_marker_idx = 0  # Track current marker for navigation
        self.mask = None
        self.polyp_detection_active = False
        self.polyp_window_start = 0
        self.polyp_window_end = 0
        self.polyps_detected = 0
        self.polyps_missed = 0
        self.feedback = None
        self.feedback_timer = 0
        self.mask_overlay_on = True
        self.last_click_coords = None
        
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

        print(f"Loaded {len(self.markers)} markers")
        for i, marker in enumerate(self.markers):
            print(f"  Marker {i}: {marker['question_type']} at {marker['start_time']}s")

        self.resume_frame = None  # Store frame to resume after accuracy click
        self.resume_time = None   # Store time to resume after accuracy click

    def load_markers(self):
        markers = []
        with open(MARKERS_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                markers.append(row)
        return markers

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

    def trigger_marker(self, marker_idx):
        if marker_idx >= len(self.markers):
            return False
        
        marker = self.markers[marker_idx]
        marker_time = float(marker['start_time'])
        question_type = marker['question_type']
        
        print(f"DEBUG: Triggering marker {marker_idx}: {question_type}")
        
        if question_type == 'polyp_window':
            self.polyp_window_start = marker_time
            self.polyp_window_end = float(marker['end_time'])
            self.polyp_detection_active = True
            self.current_marker = marker
            self.mask = self.load_mask_for_marker(marker)
            print(f"DEBUG: Polyp detection window active: {self.polyp_window_start}s - {self.polyp_window_end}s")
            self.is_playing = True
            self.status = "Playing"
            return True
        
        return False

    def handle_polyp_click(self, x, y):
        """Handle polyp detection click - 2-point system with jump to best frame"""
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
                
                # Pause video and show mask overlay for accuracy click
                self.is_playing = False
                self.status = "Paused"
                self.waiting_for_polyp_accuracy_click = True
                self.mask_overlay_on = True  # Force mask overlay on
                self.feedback_timer = 120  # Show message longer
                # Store resume frame/time
                self.resume_frame = self.current_frame
                self.resume_time = self.time_sec
                # Jump to best frame (use start_time for now)
                best_frame_time = float(self.current_marker['start_time'])
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
                
                # End polyp detection and resume video from where user left off
                self.feedback_timer = 60
                self.polyp_detection_active = False
                self.waiting_for_polyp_accuracy_click = False
                self.polyp_timing_point_awarded = False
                self.polyp_accuracy_point_awarded = False
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

    def draw_sidebar(self, frame):
        sidebar = np.zeros((self.window_height, self.sidebar_width, 3), dtype=np.uint8)
        y = 30
        
        cv2.putText(sidebar, "2-POINT POLYP TEST", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        y += 40
        
        cv2.putText(sidebar, f"Time: {self.time_sec:.1f}s", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        y += 25
        
        cv2.putText(sidebar, f"Marker: {self.current_marker_idx + 1}/{len(self.markers)}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        y += 25
        
        cv2.putText(sidebar, f"Correct: {self.correct}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 1)
        y += 25
        
        cv2.putText(sidebar, f"Incorrect: {self.incorrect}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 1)
        y += 25
        
        cv2.putText(sidebar, f"Detected: {self.polyps_detected}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1)
        y += 30
        
        if self.polyp_detection_active:
            cv2.putText(sidebar, "POLYP DETECTION ACTIVE", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            y += 25
            
            # Show polyp information
            if self.current_marker:
                polyp_text = f"Polyp {self.current_marker_idx + 1}"
                cv2.putText(sidebar, polyp_text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
                y += 25
                
                # Show question text if available
                if 'question_text' in self.current_marker:
                    question = self.current_marker['question_text']
                    if len(question) > 30:
                        question = question[:27] + "..."
                    cv2.putText(sidebar, question, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
                    y += 20
            
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
            cv2.putText(sidebar, f"Window: {self.polyp_window_start:.1f}s - {self.polyp_window_end:.1f}s", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
            y += 20
            cv2.putText(sidebar, f"Time left: {max(0, self.polyp_window_end - self.time_sec):.1f}s", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
            y += 20
            cv2.putText(sidebar, f"Mask loaded: {self.mask is not None}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        
        y += 40
        cv2.putText(sidebar, "Controls:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        y += 25
        
        controls = [
            "Space: Play/Pause",
            "N/P: Next/Previous Marker",
            "O: Toggle Mask Overlay",
            "Click: Detect Polyp",
            "Q: Quit"
        ]
        for ctrl in controls:
            cv2.putText(sidebar, ctrl, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200,200,200), 1)
            y += 18
        
        if self.last_click_coords and self.polyp_detection_active:
            y += 15
            cv2.putText(sidebar, f"Click: {self.last_click_coords}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 1)
        
        if self.feedback and self.feedback_timer > 0:
            y += 20
            color = (0,255,0) if "Correct" in self.feedback or "point" in self.feedback else (0,0,255)
            cv2.putText(sidebar, self.feedback, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        frame[:, :self.sidebar_width] = sidebar
        return frame

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            x_adj = x - self.sidebar_width
            y_adj = y
            self.last_click_coords = (x_adj, y_adj)
            
            if self.polyp_detection_active:
                self.handle_polyp_click(x_adj, y_adj)

    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.window_width, self.window_height)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        # Jump to polyp time
        if self.markers:
            marker = self.markers[0]
            start_time = float(marker['start_time'])
            self.current_frame = int(start_time * self.fps)
            self.time_sec = start_time
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            self.trigger_marker(0)
        
        while True:
            if self.is_playing:
                ret, frame = self.cap.read()
                if not ret:
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
            
            # Check if polyp window has ended
            if self.polyp_detection_active and self.time_sec > self.polyp_window_end:
                self.polyps_missed += 1
                self.feedback = "Polyp window ended - polyp missed"
                self.feedback_timer = 60
                self.polyp_detection_active = False
                print(f"DEBUG: Polyp window ended, polyp missed")
            
            video_disp = frame.copy()
            full_frame = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
            full_frame[:, self.sidebar_width:] = video_disp
            
            if self.show_sidebar:
                full_frame = self.draw_sidebar(full_frame)
            
            # Show mask overlay for polyp accuracy phase (2-point system)
            if self.mask is not None and self.waiting_for_polyp_accuracy_click:
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
                if not self.polyp_detection_active:
                    self.is_playing = not self.is_playing
                    self.status = "Playing" if self.is_playing else "Paused"
            elif key == ord('n'):
                self.next_marker()
            elif key == ord('p'):
                self.previous_marker()
            elif key == ord('o'):
                self.mask_overlay_on = not self.mask_overlay_on
                print(f"DEBUG: Mask overlay {'on' if self.mask_overlay_on else 'off'}")
        
        self.cap.release()
        cv2.destroyAllWindows()
        print(f"DEBUG: Test completed. Final scores - Correct: {self.correct}, Incorrect: {self.incorrect}")
        print(f"DEBUG: Polyp detection - Detected: {self.polyps_detected}, Missed: {self.polyps_missed}")

    def jump_to_marker(self, marker_idx):
        """Jump to a specific marker"""
        if not (0 <= marker_idx < len(self.markers)):
            print(f"DEBUG: Invalid marker index: {marker_idx}")
            return False
            
        marker = self.markers[marker_idx]
        marker_time = float(marker['start_time'])
        print(f"DEBUG: Jumping to marker {marker_idx} at time {marker_time}s")
        
        # Reset polyp detection state
        self.polyp_detection_active = False
        self.waiting_for_polyp_accuracy_click = False
        self.polyp_timing_point_awarded = False
        self.polyp_accuracy_point_awarded = False
        
        # Jump to marker time
        self.current_frame = int(marker_time * self.fps)
        self.time_sec = marker_time
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        
        # Trigger the marker
        self.current_marker_idx = marker_idx
        return self.trigger_marker(marker_idx)

    def next_marker(self):
        """Jump to next marker"""
        if self.current_marker_idx < len(self.markers) - 1:
            return self.jump_to_marker(self.current_marker_idx + 1)
        else:
            print("DEBUG: Already at last marker")
            return False

    def previous_marker(self):
        """Jump to previous marker"""
        if self.current_marker_idx > 0:
            return self.jump_to_marker(self.current_marker_idx - 1)
        else:
            print("DEBUG: Already at first marker")
            return False

if __name__ == "__main__":
    TwoPointPolypTest().run() 