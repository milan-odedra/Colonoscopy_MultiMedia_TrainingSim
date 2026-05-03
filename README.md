# Colonoscopy Media Training Sim

I built this project as a multimedia training simulator for colonoscopy video review and perception testing. I worked on it over a few months during my Multimedia Application Software Developer job at university.

The aim is simple: give medical trainees a controlled way to practise spotting pathology, recognising anatomy, and making decisions from colonoscopy footage without the pressure or risk of a live procedure. The sim lets a user review annotated video, answer timed questions, click on regions such as the lumen or polyps, complete polyp classification reports, and export results for later review.

## Why I Built It

Live procedures are not the right place to learn every basic perception skill. A trainee needs time to pause, replay, inspect frames, make mistakes, and understand what they missed.

I built this to support that kind of practice. The simulator uses pre-recorded colonoscopy footage and marker data so the user can train on specific moments in the video. That makes it useful for:

- practising polyp detection in timed windows
- checking whether the user can identify the lumen during navigation
- asking location questions during the withdrawal or insertion phase
- recording polyp details such as site, size, Paris classification, NICE classification, likely histology, and excision technique
- reviewing answers after a run and exporting the results to CSV

## What It Includes

- `ColonscopyVideoSim_Demo_v0.py` - the OpenCV menu that launches each mode
- `perception_test_practice_demo_v1.py` - practice mode with navigation, overlays, debug options, and review tools
- `perception_test_official_demo_v1.py` - official mode with stricter linear progression
- `video_review.py` - a marker-based video review tool
- `mask_creator.py` - a tool for drawing polygon masks on video frames
- `data/new_perception_markers.csv` - timed perception questions
- `data/masks/` - PNG masks used to validate click-based answers
- `data/results/` - exported test results
- `scripts/` - one-off helper scripts I used while building and testing features

## Main Modes

### Video Review

I built the review mode so I could step through colonoscopy footage with marker overlays. It helps inspect where important events happen in the video before turning them into questions or masks.

### Practice Mode

Practice mode is where most training happens. It includes extra controls that would be inappropriate in an assessment, but useful while learning:

- jump to markers
- move to the next or previous marker
- show or hide mask overlays
- use debug information
- review and export results

### Official Test Mode

Official mode uses the same general question flow but removes practice shortcuts. The user has to progress through the test in order, with no marker skipping, no overlay toggles, and no debug mode.

### Mask Creator

The mask creator lets me capture a video frame and draw polygon masks around target areas. Those masks are saved as PNG files and later used to check whether a click landed inside the expected region.

## Question Types

The simulator supports several question styles:

- lumen click questions
- polyp click questions
- timed polyp detection windows
- multiple choice location questions
- polyp report forms with dropdown-style choices

The marker CSV controls when each question appears. For example, `data/new_perception_markers.csv` stores the start time, optional end time, question type, question text, mask path, options, and correct answer.

## Setup

This is a Python project. I used OpenCV for video playback and drawing, NumPy for image and mask work, and Tkinter for small dialogs.

Install the main dependencies:

```bash
pip install opencv-python numpy
```

Tkinter usually comes with Python on Windows. On some Linux installs, it may need to be installed separately through the system package manager.

The scripts expect colonoscopy videos under:

```text
videos/
```

The main scripts currently look for:

```text
videos/Without annotations (edited).mp4
videos/With annotations (edited).mp4
```

Those files are large medical media assets, so they may not be committed with the code. If the video file names differ, update the `VIDEO_PATH` values in the relevant script.

## Running It

Start from the menu:

```bash
python ColonscopyVideoSim_Demo_v0.py
```

Or run a mode directly:

```bash
python perception_test_practice_demo_v1.py
python perception_test_official_demo_v1.py
python video_review.py
python mask_creator.py
```

## Controls

Main menu:

- `W` / `S` - move through menu options
- `Enter` - select a mode
- `F` - toggle fullscreen
- `Q` - quit

Practice and official test modes:

- `Space` - play or pause
- `Arrow keys` - move through frames where supported
- `Mouse click` - answer click-based questions
- `W` / `S` - move through multiple choice options
- `Q` - quit

Practice-only controls:

- `N` / `P` - next or previous marker
- `J` - jump to a marker
- `O` - toggle mask overlay
- `D` - toggle debug mode
- `R` - open the review screen

Mask creator:

- `Arrow keys` - move through frames
- `Space` - play or pause
- `C` - capture the current frame and draw a mask
- `G` - go to a specific timestamp
- `F` - toggle fullscreen
- `Q` - quit

## Technical Decisions

### I used OpenCV for the main interface

I chose OpenCV because the project is centred on video frames, timing, overlays, and pixel-level click validation. It gave me direct control over playback, frame stepping, drawing text, and checking masks.

The trade-off is that the UI code is lower-level than it would be in a desktop GUI framework. Buttons, sidebars, dropdown-like controls, and review screens are drawn manually on image frames. That made the interface more work to maintain, but it kept the video and annotation logic in one place.

### I used CSV files for marker data

I kept marker data in CSV because it was easy to edit, inspect, and share while the test content was changing. The marker file can define timings, question types, answer options, and mask paths without changing the Python code.

The trade-off is that CSV does not enforce much structure. A database or typed config format would catch more mistakes, but CSV was fast and practical for the prototype stage.

### I used PNG masks for click validation

For click-based questions, I used binary mask images. When the user clicks, the app checks whether that pixel falls inside the expected mask. This works well for lumen and polyp questions because the correct answer is spatial, not just textual.

The trade-off is that masks need careful alignment with the source video resolution. That is why the code tries to preserve the original frame dimensions and resizes masks with nearest-neighbour interpolation where needed.

### I split practice and official modes

Practice mode and official mode are separate files. This made it easier to lock down the official test while keeping practice features available.

The trade-off is duplication. A lot of the playback, question, scoring, and review logic exists in both files. I left a refactoring plan in `REFACTORING_TODO.md` because the better long-term design would be a shared core class with mode-specific feature flags.

### I kept results as CSV exports

Results are written under `data/results/`. This made it easy to open outputs in Excel or analyse them later without building an admin dashboard.

The trade-off is that there is no multi-user account system or central result store. For the project scope, flat files were enough.

## Current Limitations

- The code has duplicated logic between practice and official modes.
- Some paths still reflect the development machine or older file names.
- There is no requirements file yet.
- The UI is built with OpenCV drawing calls, so layout changes take more manual work.
- The app depends on local video assets being placed at the expected paths.

## What I Would Improve Next

If I returned to this project, I would first refactor the perception test into shared modules:

- video playback manager
- marker loader
- question handler
- results exporter
- UI drawing layer
- mode configuration for practice vs official testing

After that, I would add a `requirements.txt`, clean up old path references, and write tests around marker loading, question timing, mask validation, and result export.

## Project Status

This project is a working university/job project prototype. It shows how I approached a real multimedia training problem: using video, overlays, annotations, timed questions, and recorded results to help clinicians practise perception tasks away from live procedures.
