# Add these new variables to __init__ method after existing variables:
self.waiting_for_polyp_report = False
self.polyp_report_data = {}
self.current_polyp_number = 0
self.polyp_report_fields = [
    'site', 'size_estimate', 'paris_classification', 
    'nice_classification', 'likely_histology', 'excision_technique'
]
self.polyp_report_field_index = 0
self.polyp_report_input = ""

# Add this method to the PerceptionTestV2 class:
def setup_polyp_report(self, marker):
    """Setup polyp report form"""
    # Extract polyp number from question text
    import re
    match = re.search(r'Polyp (\d+)', marker['question_text'])
    if match:
        self.current_polyp_number = int(match.group(1))
    else:
        self.current_polyp_number = 0
    
    self.polyp_report_data = {
        'site': '',
        'size_estimate': '',
        'paris_classification': '',
        'nice_classification': '',
        'likely_histology': '',
        'excision_technique': ''
    }
    self.polyp_report_field_index = 0
    self.polyp_report_input = ""
    self.waiting_for_polyp_report = True
    return True

# Add this method to handle polyp report completion:
def complete_polyp_report(self):
    """Complete and save polyp report"""
    print(f"DEBUG: Polyp {self.current_polyp_number} Report Completed:")
    for field, value in self.polyp_report_data.items():
        print(f"  {field.replace('_', ' ').title()}: {value}")
    
    self.feedback = f"Polyp {self.current_polyp_number} Report Completed!"
    self.feedback_timer = 90
    self.waiting_for_polyp_report = False
    self.advance_to_next_marker()

# Add this method to get field display names:
def get_field_display_name(self, field):
    """Get user-friendly field names"""
    display_names = {
        'site': 'Site',
        'size_estimate': 'Size Estimate (mm)',
        'paris_classification': 'Paris Classification',
        'nice_classification': 'NICE Classification',
        'likely_histology': 'Likely Histology',
        'excision_technique': 'Excision Technique'
    }
    return display_names.get(field, field)

# Modify the trigger_marker method to include polyp_report case:
# Add this after the existing elif conditions in trigger_marker():
elif question_type == 'polyp_report':
    # Handle polyp report form
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

# Modify the draw_sidebar method to include polyp report display:
# Add this section after the MCQ display code in draw_sidebar():
# Display polyp report form if active
if self.waiting_for_polyp_report:
    y += 10
    cv2.putText(sidebar, f"Polyp {self.current_polyp_number} Report:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    y += 30
    
    # Display all fields with their current values
    for i, field in enumerate(self.polyp_report_fields):
        color = (0,255,0) if i == self.polyp_report_field_index else (200,200,200)
        if i == self.polyp_report_field_index:
            prefix = "> "
        else:
            prefix = "  "
        
        field_name = self.get_field_display_name(field)
        current_value = self.polyp_report_data[field]
        
        # Show current input if editing this field
        if i == self.polyp_report_field_index:
            display_value = self.polyp_report_input if self.polyp_report_input else current_value
            cv2.putText(sidebar, f"{prefix}{field_name}:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
            y += 20
            cv2.putText(sidebar, f"  {display_value}_", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
        else:
            cv2.putText(sidebar, f"{prefix}{field_name}: {current_value}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        y += 22
    
    y += 10
    cv2.putText(sidebar, "Controls:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
    y += 20
    cv2.putText(sidebar, "W/S: Navigate fields", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)
    y += 18
    cv2.putText(sidebar, "Type: Enter text", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)
    y += 18
    cv2.putText(sidebar, "Enter: Save field", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)
    y += 18
    cv2.putText(sidebar, "Tab: Complete report", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)
    y += 18
    cv2.putText(sidebar, "Esc: Clear field", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)
    y += 30

# Add keyboard handling for polyp reports in the main run() loop:
# Add this section in the keyboard handling part of run():
# Polyp report controls
elif self.waiting_for_polyp_report:
    if key == ord('w'):  # Move up in fields
        self.polyp_report_field_index = max(0, self.polyp_report_field_index - 1)
        self.polyp_report_input = self.polyp_report_data[self.polyp_report_fields[self.polyp_report_field_index]]
    elif key == ord('s'):  # Move down in fields
        self.polyp_report_field_index = min(len(self.polyp_report_fields) - 1, self.polyp_report_field_index + 1)
        self.polyp_report_input = self.polyp_report_data[self.polyp_report_fields[self.polyp_report_field_index]]
    elif key == 13:  # Enter - save current field
        current_field = self.polyp_report_fields[self.polyp_report_field_index]
        self.polyp_report_data[current_field] = self.polyp_report_input
        # Move to next field
        if self.polyp_report_field_index < len(self.polyp_report_fields) - 1:
            self.polyp_report_field_index += 1
            self.polyp_report_input = self.polyp_report_data[self.polyp_report_fields[self.polyp_report_field_index]]
    elif key == 9:  # Tab - complete report
        # Save current field first
        current_field = self.polyp_report_fields[self.polyp_report_field_index]
        self.polyp_report_data[current_field] = self.polyp_report_input
        self.complete_polyp_report()
    elif key == 27:  # Escape - clear current field
        self.polyp_report_input = ""
    elif key == 8:  # Backspace
        if self.polyp_report_input:
            self.polyp_report_input = self.polyp_report_input[:-1]
    elif 32 <= key <= 126:  # Printable characters
        self.polyp_report_input += chr(key)

# Also modify the advance_to_next_marker method to reset polyp report state:
# Add these lines to the advance_to_next_marker method:
self.waiting_for_polyp_report = False
self.polyp_report_data = {}
self.polyp_report_input = ""