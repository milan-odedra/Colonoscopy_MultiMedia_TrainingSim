def advance_to_next_marker(self):
    """Advance to next marker and reset all states"""
    self.next_marker_idx += 1
    
    # Reset ALL states to ensure clean navigation
    self.current_marker = None
    self.mask = None
    self.waiting_for_click = False
    self.waiting_for_mcq = False
    self.mcq_options = []
    self.selected_mcq_option = 0
    self.correct_option = None
    self.polyp_detection_active = False
    self.waiting_for_polyp_accuracy_click = False
    self.polyp_timing_point_awarded = False
    self.polyp_accuracy_point_awarded = False
    self.resume_frame = None
    self.resume_time = None
    
    print(f"DEBUG: Advanced to next marker index: {self.next_marker_idx}")
    print(f"DEBUG: All states reset - ready for navigation")
    
    # Only resume playing if we're not immediately hitting another freeze-frame marker
    if self.next_marker_idx < len(self.markers):
        next_marker = self.markers[self.next_marker_idx]
        next_marker_type = next_marker['question_type']
        if next_marker_type not in ['lumen', 'location', 'position']:
            self.is_playing = True
            self.status = "Playing"
            print(f"DEBUG: Auto-resuming video for marker type: {next_marker_type}")
        else:
            print(f"DEBUG: Not auto-resuming - next marker is freeze-frame type: {next_marker_type}")
    else:
        print(f"DEBUG: Reached end of markers")

def reset_all_question_states(self):
    """Helper method to reset all question-related states"""
    self.waiting_for_click = False
    self.waiting_for_mcq = False
    self.mcq_options = []
    self.selected_mcq_option = 0
    self.correct_option = None
    self.polyp_detection_active = False
    self.waiting_for_polyp_accuracy_click = False
    self.polyp_timing_point_awarded = False
    self.polyp_accuracy_point_awarded = False
    self.mask = None
    self.current_marker = None
    self.feedback = None
    self.feedback_timer = 0
    print(f"DEBUG: All question states reset")