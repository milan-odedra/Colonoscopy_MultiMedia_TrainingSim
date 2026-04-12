import cv2
import numpy as np
import os
from pathlib import Path
print("test")

VIDEO_PATH = r"videos/Without annotations (edited).mp4"  # Update as needed
MASKS_DIR = "data/masks/"

if not os.path.exists(MASKS_DIR):
    os.makedirs(MASKS_DIR)

class MaskCreator:
    def __init__(self):
        self.cap = cv2.VideoCapture(VIDEO_PATH)
        if not self.cap.isOpened():
            raise RuntimeError(f"Error opening video file: {VIDEO_PATH}")
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps
        self.current_frame = 0
        self.current_time = 0.0
        
        # Window setup
        self.window_name = "Mask Creator - Video Navigation"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1200, 800)
        
        # Control panel dimensions
        self.control_height = 200
        self.video_height = 600
        
        print(f"Video loaded: {VIDEO_PATH}")
        print(f"Duration: {self.duration:.2f}s, FPS: {self.fps}, Total frames: {self.total_frames}")
        print("\nControls:")
        print("  Arrow keys: Navigate frames")
        print("  Space: Play/Pause")
        print("  C: Capture current frame for masking")
        print("  G: Go to specific time")
        print("  Q: Quit")
    
    def format_time(self, seconds):
        """Format time as MM:SS.mmm"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{minutes:02d}:{secs:02d}.{ms:03d}"
    
    def parse_time_input(self, time_str):
        """Parse time input in format MM:SS.mmm or MM:SS"""
        try:
            if '.' in time_str:
                time_part, ms_part = time_str.split('.')
                minutes, seconds = map(int, time_part.split(':'))
                milliseconds = int(ms_part)
                return minutes * 60 + seconds + milliseconds / 1000.0
            else:
                minutes, seconds = map(int, time_str.split(':'))
                return minutes * 60 + seconds
        except:
            return None
    
    def go_to_time(self, time_sec):
        """Navigate to specific time in video"""
        if 0 <= time_sec <= self.duration:
            self.current_frame = int(time_sec * self.fps)
            self.current_time = time_sec
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            return True
        return False
    
    def draw_control_panel(self, frame):
        """Draw control panel with time display and navigation info"""
        height, width = frame.shape[:2]
        control_panel = np.zeros((self.control_height, width, 3), dtype=np.uint8)
        
        # Background
        control_panel[:] = (50, 50, 50)
        
        # Title
        cv2.putText(control_panel, "Mask Creator - Video Navigation", (20, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Current time and frame info
        time_str = self.format_time(self.current_time)
        cv2.putText(control_panel, f"Time: {time_str}", (20, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(control_panel, f"Frame: {self.current_frame}/{self.total_frames}", (20, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Progress bar
        progress = self.current_frame / self.total_frames
        bar_width = width - 40
        bar_height = 20
        bar_x, bar_y = 20, 130
        
        # Background bar
        cv2.rectangle(control_panel, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (100, 100, 100), -1)
        # Progress bar
        progress_width = int(bar_width * progress)
        cv2.rectangle(control_panel, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), 
                     (0, 255, 0), -1)
        
        # Controls info
        controls = [
            "Controls: Arrow keys (navigate) | Space (play/pause) | C (capture) | G (go to time) | Q (quit)"
        ]
        y_offset = 170
        for control in controls:
            cv2.putText(control_panel, control, (20, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_offset += 20
        
        return control_panel
    
    def draw_polygon_mask(self, image):
        """Interactive polygon drawing for mask creation"""
        clone = image.copy()
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        points = []
        window_name = "Draw Mask - Click to add points, Enter to finish, R to reset, Q to quit"

        def click_event(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)
        cv2.setMouseCallback(window_name, click_event)

        while True:
            temp = clone.copy()
            
            # Draw existing points and lines
            if points:
                for i, pt in enumerate(points):
                    cv2.circle(temp, pt, 5, (0, 255, 0), -1)
                    cv2.putText(temp, str(i+1), (pt[0]+10, pt[1]-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    if i > 0:
                        cv2.line(temp, points[i-1], pt, (0, 255, 0), 2)
                
                # Close polygon if we have enough points
                if len(points) > 2:
                    cv2.line(temp, points[-1], points[0], (0, 255, 0), 2)
            
            # Instructions overlay
            cv2.putText(temp, "Click to add points", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(temp, "Enter: Finish | R: Reset | Q: Cancel", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow(window_name, temp)
            key = cv2.waitKey(1) & 0xFF
            
            if key == 13 and len(points) > 2:  # Enter
                pts = np.array(points, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.fillPoly(mask, [pts], (255,))
                break
            elif key == ord('r'):  # Reset
                points.clear()
                mask[:] = 0
            elif key == ord('q'):  # Quit
                mask = None
                break
        
        cv2.destroyWindow(window_name)
        return mask
    
    def capture_and_mask(self):
        """Capture current frame and create mask"""
        # Get current frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if not ret:
            print("Error reading frame")
            return
        
        print(f"Creating mask for frame at {self.format_time(self.current_time)}")
        mask = self.draw_polygon_mask(frame)
        
        if mask is not None:
            # Save mask with timestamp filename
            mask_filename = f"frame_{int(self.current_time//60):02d}_{int(self.current_time%60):02d}_{int((self.current_time%1)*1000):03d}_mask.png"
            mask_path = os.path.join(MASKS_DIR, mask_filename)
            cv2.imwrite(mask_path, mask)
            print(f"Mask saved to: {mask_path}")
            
            # Show preview
            preview = np.zeros_like(frame)
            preview[mask == 255] = [0, 255, 0]  # Green overlay
            preview = cv2.addWeighted(frame, 0.7, preview, 0.3, 0)
            
            cv2.imshow("Mask Preview", preview)
            cv2.waitKey(2000)  # Show for 2 seconds
            cv2.destroyWindow("Mask Preview")
        else:
            print("Mask creation cancelled")
    
    def run(self):
        """Main application loop"""
        playing = False
        time_input_mode = False
        time_input_str = ""
        time_input_error = ""
        
        while True:
            # Get current frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Update current time
            self.current_time = self.current_frame / self.fps
            
            # Draw control panel
            control_panel = self.draw_control_panel(frame)
            
            # Combine video and control panel
            combined = np.vstack([frame, control_panel])
            
            # Overlay time input if in time input mode
            if time_input_mode:
                overlay = combined.copy()
                h, w = combined.shape[:2]
                box_w, box_h = 420, 80
                box_x, box_y = (w - box_w) // 2, (h - box_h) // 2
                cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (30, 30, 30), -1)
                cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 255, 255), 2)
                prompt = "Enter time (MM:SS.mmm):"
                cv2.putText(overlay, prompt, (box_x + 20, box_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(overlay, time_input_str + "_", (box_x + 20, box_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                if time_input_error:
                    cv2.putText(overlay, time_input_error, (box_x + 20, box_y + box_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                alpha = 0.92
                cv2.addWeighted(overlay, alpha, combined, 1 - alpha, 0, combined)
            
            cv2.imshow(self.window_name, combined)
            
            if time_input_mode:
                key = cv2.waitKey(0) & 0xFF
                if key in (13, 10):  # Enter
                    parsed_time = self.parse_time_input(time_input_str)
                    if parsed_time is not None and 0 <= parsed_time <= self.duration:
                        self.go_to_time(parsed_time)
                        time_input_mode = False
                        time_input_str = ""
                        time_input_error = ""
                    else:
                        time_input_error = "Invalid time. Use MM:SS.mmm or MM:SS"
                elif key == 27:  # Esc
                    time_input_mode = False
                    time_input_str = ""
                    time_input_error = ""
                elif key in (8, 127):  # Backspace
                    time_input_str = time_input_str[:-1]
                elif key == ord(':') or key == ord('.'):
                    time_input_str += chr(key)
                elif 48 <= key <= 57:  # 0-9
                    time_input_str += chr(key)
                # Ignore all other keys
                continue
            else:
                key = cv2.waitKey(30) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):  # Space - play/pause
                playing = not playing
            elif key == 81:  # Left arrow - previous frame
                self.current_frame = max(0, self.current_frame - 1)
                playing = False
            elif key == 83:  # Right arrow - next frame
                self.current_frame = min(self.total_frames - 1, self.current_frame + 1)
                playing = False
            elif key == 82:  # Up arrow - jump back 10 frames
                self.current_frame = max(0, self.current_frame - 10)
                playing = False
            elif key == 84:  # Down arrow - jump forward 10 frames
                self.current_frame = min(self.total_frames - 1, self.current_frame + 10)
                playing = False
            elif key == ord('c'):  # Capture frame for masking
                self.capture_and_mask()
            elif key == ord('g'):  # Go to specific time (in-window)
                time_input_mode = True
                time_input_str = ""
                time_input_error = ""
            
            # Auto-advance if playing
            if playing:
                self.current_frame = min(self.total_frames - 1, self.current_frame + 1)
        
        self.cap.release()
        cv2.destroyAllWindows()

def main():
    try:
        creator = MaskCreator()
        creator.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 