import csv

def time_to_seconds(time_str):
    """Convert mm:ss format to seconds"""
    if not time_str or time_str.strip() == '':
        return 0
    
    print(f"Converting: '{time_str}'")
    parts = time_str.strip().split(':')
    print(f"Parts: {parts}")
    
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = int(parts[1])
        total_seconds = minutes * 60 + seconds
        print(f"Result: {minutes}m {seconds}s = {total_seconds}s")
        return total_seconds
    return 0

# Paul's actual timestamps from the file
polyp_timestamps = [
    # Polyp 1
    ("06:36", "06:39", "Polyp 1 - Initial detection window"),
    ("06:47", "06:47", "Polyp 1 - Best frame for mask creation"),
    ("06:50", "07:42", "Polyp 1 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 2
    ("08:06", "08:09", "Polyp 2 - Initial detection window"),
    ("08:23", "08:23", "Polyp 2 - Best frame for mask creation"),
    ("08:09", "08:23", "Polyp 2 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 3
    ("08:31", "08:35", "Polyp 3 - Initial detection window"),
    ("08:52", "08:52", "Polyp 3 - Best frame for mask creation"),
    ("08:38", "08:52", "Polyp 3 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 4
    ("09:18", "09:26", "Polyp 4 - Initial detection window"),
    ("09:36", "09:36", "Polyp 4 - Best frame for mask creation"),
    ("09:26", "09:36", "Polyp 4 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 5
    ("10:46", "10:56", "Polyp 5 - Initial detection window"),
    ("11:24", "11:24", "Polyp 5 - Best frame for mask creation"),
    ("10:59", "11:24", "Polyp 5 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 6
    ("12:28", "12:31", "Polyp 6 - Initial detection window"),
    ("12:42", "12:42", "Polyp 6 - Best frame for mask creation"),
    ("12:34", "12:42", "Polyp 6 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 7
    ("13:12", "13:18", "Polyp 7 - Initial detection window"),
    ("13:33", "13:33", "Polyp 7 - Best frame for mask creation"),
    ("13:21", "13:33", "Polyp 7 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 8
    ("13:34", "13:43", "Polyp 8 - Initial detection window"),
    ("13:55", "13:55", "Polyp 8 - Best frame for mask creation"),
    ("13:45", "13:55", "Polyp 8 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 9
    ("14:05", "14:08", "Polyp 9 - Initial detection window"),
    ("14:29", "14:29", "Polyp 9 - Best frame for mask creation"),
    ("14:09", "14:29", "Polyp 9 - Detailed review (Scope advanced to review polyp)"),
    
    # Polyp 10
    ("15:54", "15:55", "Polyp 10 - Initial detection window"),
    ("16:30", "16:30", "Polyp 10 - Best frame for mask creation"),
    ("16:17", "16:30", "Polyp 10 - Detailed review (Scope advanced to review polyp)"),
]

# Convert and create CSV
with open('data/polyp_markers_paul_timestamps.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile, delimiter=';')
    writer.writerow(['start', 'end', 'description'])
    
    for start_time, end_time, description in polyp_timestamps:
        start_seconds = time_to_seconds(start_time)
        end_seconds = time_to_seconds(end_time)
        
        # For single-frame markers, add a small window
        if start_seconds == end_seconds:
            end_seconds += 0.1
            
        print(f"{start_time} ({start_seconds}s) - {end_time} ({end_seconds}s): {description}")
        writer.writerow([start_seconds, end_seconds, description])

print("\nCreated data/polyp_markers_paul_timestamps.csv with correct timestamps!") 