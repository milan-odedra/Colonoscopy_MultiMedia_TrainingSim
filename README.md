# Endoscopy Multimedia Test Suite

## Overview

A comprehensive endoscopy training and assessment platform designed for medical professionals to practice and evaluate their polyp detection, classification, and diagnostic skills. The application provides both practice and official test modes with interactive video-based questions, real-time scoring, and detailed performance analytics.

## 🏗️ System Architecture

### Core Components
- **Main Menu System** (`ColonscopyVideoSim_Demo_v0.py`) - Central launcher and navigation
- **Practice Mode** (`perception_test_v2.py`) - Flexible training environment with debugging features
- **Official Test Mode** (`perception_test_official.py`) - Strict assessment environment
- **Video Review Tool** (`video_review.py`) - Marker-based video analysis
- **Mask Creator** (`mask_creator.py`) - Interactive annotation tool for creating question masks

### Technology Stack
- **Python 3.x** - Core application logic
- **OpenCV** - Video processing and computer vision
- **Tkinter** - Dialog boxes and user interface elements
- **NumPy** - Numerical computations and array operations
- **CSV** - Data storage and marker management

## 🎯 Key Features

### 1. **Dual Mode System**
- **Practice Mode**: Flexible navigation, debug features, overlays, and skipping capabilities
- **Official Test Mode**: Strict linear progression, no practice features, formal assessment

### 2. **Interactive Question Types**
- **Click-based Questions**: Users click on specific areas (lumen, polyps) with mask validation
- **Multiple Choice Questions**: Location and positioning assessments
- **Polyp Reports**: Comprehensive classification forms with dropdown options
- **Time Window Detection**: Real-time polyp detection during video playback

### 3. **Advanced Video Navigation**
- Frame-by-frame navigation with arrow keys
- Time-based jumping with precise input
- Fullscreen toggle for immersive experience
- Variable playback speed control

### 4. **Comprehensive Scoring System**
- Real-time score tracking with visual feedback
- Separate polyp detection and accuracy scoring
- Detailed performance analytics
- CSV export for data analysis

### 5. **Professional UI/UX**
- Responsive sidebar with real-time information
- Visual progress indicators
- Animated score popups
- Intuitive keyboard and mouse controls

## 🚀 Getting Started

### Prerequisites
```bash
pip install opencv-python numpy
```

### Quick Start
1. **Launch the application**:
   ```bash
   python ColonscopyVideoSim_Demo_v0.py
   ```

2. **Choose your mode**:
   - **Video Review**: Analyze video with marker overlays
   - **Practice Mode**: Train with full feature set
   - **Official Test**: Take formal assessment
   - **Mask Creator**: Create new question masks

### Controls Reference

#### Main Menu
- **W/S**: Navigate options
- **Enter**: Select option
- **F**: Toggle fullscreen
- **Q**: Quit

#### Test Modes
- **Space**: Play/pause video
- **Arrow Keys**: Navigate frames
- **Mouse**: Click to answer questions
- **W/S**: Navigate MCQ options
- **F**: Toggle fullscreen
- **Q**: Quit

#### Practice Mode Only
- **N/P**: Next/previous marker
- **J**: Jump to specific marker
- **O**: Toggle mask overlays
- **D**: Toggle debug mode
- **R**: Show review screen

## 📁 Project Structure

```
Colonoscopy_VideoSim/
├── ColonscopyVideoSim_Demo_v0.py    # Main menu and launcher
├── perception_test_v2.py            # Practice mode test
├── perception_test_official.py      # Official test mode
├── video_review.py                  # Video review tool
├── mask_creator.py                  # Interactive mask creation
├── data/
│   ├── masks/                       # Question mask images
│   ├── results/                     # Test results and analytics
│   └── *.csv                        # Marker and question data
├── videos/                          # Video assets
└── scripts/                         # Utility and testing scripts
```

## 🔧 Configuration

### Video Setup
- Place video files in `videos/` directory
- Update `VIDEO_PATH` in relevant files
- Supported formats: MP4, AVI, MOV

### Marker Configuration
- CSV files contain question timing and content
- Format: `start_time, end_time, question_text, question_type, options, correct_answer`
- Time format: seconds (e.g., 396.167 for 06:36.167)

### Mask Creation
- Use `mask_creator.py` for interactive mask creation
- Supports multiple polyps per frame
- Automatic naming with video and timestamp
- PNG format for compatibility

## 📊 Data Management

### Results Export
- Automatic CSV export after test completion
- Detailed performance metrics
- Individual question responses
- Timing and accuracy data

### Marker Management
- Centralized CSV-based configuration
- Easy addition of new questions
- Support for multiple question types
- Flexible timing windows

## 🎨 User Interface Design

### Responsive Layout
- Adaptive window sizing based on screen resolution
- Centered positioning for optimal viewing
- Professional color scheme and typography

### Visual Feedback
- Real-time status indicators
- Animated score popups
- Progress bars and timers
- Clear instruction overlays

### Accessibility Features
- Keyboard navigation support
- High contrast text
- Clear visual hierarchy
- Intuitive control mapping

## 🔍 Technical Implementation

### Video Processing
- Native resolution preservation for accuracy
- Efficient frame-by-frame navigation
- Smooth playback with variable speed
- Memory-optimized video handling

### Question System
- Modular question type architecture
- Flexible scoring algorithms
- Real-time validation and feedback
- Comprehensive state management

### Data Persistence
- CSV-based configuration
- Automatic result logging
- Backup and recovery systems
- Cross-platform compatibility

## 🧪 Testing and Quality Assurance

### Automated Testing
- Unit tests for core functionality
- Integration tests for question flow
- Performance benchmarking
- Cross-platform compatibility testing

### Manual Testing
- User experience validation
- Performance optimization
- Bug tracking and resolution
- Feature regression testing

## 🔮 Future Enhancements

### Planned Features
- **3D Visualization**: Enhanced spatial understanding
- **AI Integration**: Automated polyp detection assistance
- **Multiplayer Mode**: Collaborative training sessions
- **Cloud Storage**: Remote result synchronization
- **Mobile Support**: Tablet and mobile device compatibility

### Technical Improvements
- **OOP Refactoring**: Enhanced code organization and maintainability
- **Database Integration**: Advanced data management
- **API Development**: External system integration
- **Performance Optimization**: Enhanced video processing

## 👨‍💻 Developer Information

### Primary Developer
- **Role**: Full-stack developer and system architect
- **Contributions**: Complete application design and implementation
- **Technologies**: Python, OpenCV, Computer Vision, UI/UX Design

### Key Achievements
- Designed and implemented complete endoscopy training platform
- Created dual-mode system for practice and assessment
- Developed interactive mask creation and annotation tools
- Implemented comprehensive scoring and analytics system
- Established professional documentation and code standards

### Technical Skills Demonstrated
- **System Architecture**: Modular, scalable design
- **User Interface Design**: Professional, intuitive UX
- **Video Processing**: Real-time video manipulation and analysis
- **Data Management**: CSV-based configuration and results export
- **Quality Assurance**: Comprehensive testing and documentation

## 📄 License and Usage

This application was developed as part of a research project. The codebase demonstrates advanced software engineering practices and can serve as a portfolio piece showcasing:

- Complex system design and implementation
- Professional software development practices
- Medical software development experience
- Computer vision and video processing expertise
- User interface and experience design

## 🤝 Contributing

For collaboration or enhancement requests, please contact the primary developer. The codebase is designed for extensibility and welcomes contributions that maintain the established quality standards.

---

**Note**: This application represents a significant achievement in medical training software development, combining advanced video processing, interactive assessment, and professional user experience design to create a comprehensive endoscopy training platform. 