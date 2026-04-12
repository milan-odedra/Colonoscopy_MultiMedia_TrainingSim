# Replace the key handling section for 'n' and 'p' keys with this improved version:

elif key == ord('n'):
    # Next marker
    if self.testing_mode:
        # In testing mode, allow navigation to any marker
        target_idx = self.next_marker_idx
        if target_idx >= len(self.markers):
            target_idx = len(self.markers) - 1  # Go to last marker if at end
        if target_idx < len(self.markers):
            print(f"DEBUG: Testing mode - jumping to marker {target_idx}")
            self.jump_to_marker(target_idx)
    else:
        # In normal mode, only allow if not actively waiting for input
        if not (self.waiting_for_click or self.waiting_for_mcq or self.polyp_detection_active):
            target_idx = self.next_marker_idx
            if target_idx >= len(self.markers):
                target_idx = len(self.markers) - 1
            if target_idx < len(self.markers):
                print(f"DEBUG: Normal mode - jumping to marker {target_idx}")
                self.jump_to_marker(target_idx)
        else:
            print(f"DEBUG: Cannot navigate - waiting for input (click: {self.waiting_for_click}, mcq: {self.waiting_for_mcq}, polyp: {self.polyp_detection_active})")

elif key == ord('p'):
    # Previous marker
    if self.testing_mode:
        # In testing mode, allow navigation to any previous marker
        target_idx = max(0, self.next_marker_idx - 1)
        if target_idx >= 0:
            print(f"DEBUG: Testing mode - jumping to previous marker {target_idx}")
            self.jump_to_marker(target_idx)
    else:
        # In normal mode, only allow if not actively waiting for input
        if not (self.waiting_for_click or self.waiting_for_mcq or self.polyp_detection_active):
            target_idx = max(0, self.next_marker_idx - 1)
            if target_idx >= 0:
                print(f"DEBUG: Normal mode - jumping to previous marker {target_idx}")
                self.jump_to_marker(target_idx)
        else:
            print(f"DEBUG: Cannot navigate - waiting for input (click: {self.waiting_for_click}, mcq: {self.waiting_for_mcq}, polyp: {self.polyp_detection_active})")

# Also add this new key for better testing navigation:
elif key == ord('1') and not self.waiting_for_mcq:  # Only if not in MCQ mode
    # Jump to marker 1 (for testing)
    if 0 < len(self.markers):
        self.jump_to_marker(0)
elif key == ord('2') and not self.waiting_for_mcq:
    # Jump to marker 2 (for testing)
    if 1 < len(self.markers):
        self.jump_to_marker(1)
elif key == ord('3') and not self.waiting_for_mcq:
    # Jump to marker 3 (for testing)
    if 2 < len(self.markers):
        self.jump_to_marker(2)
# Add more number keys as needed...