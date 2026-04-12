# Perception Test Refactoring TODO

## 🎯 **Goal: Clean, Maintainable Codebase for Future Development**

### **Current State**
- `perception_test_v2.py` = Practice Mode (all features)
- `perception_test_official.py` = Official Mode (strict, no cheats)
- **Problem:** Code duplication, hard to maintain, bugs can diverge

---

## 📋 **Phase 1: Core Architecture Refactor**

### **1.1 Create Shared Core Class**
- [ ] Create `perception_test_core.py`
- [ ] Move all shared logic:
  - [ ] Video playback and timing
  - [ ] Marker loading and processing
  - [ ] Question handling (MCQ, lumen, polyp detection, polyp report)
  - [ ] Results logging and CSV export
  - [ ] Review screen functionality
  - [ ] Mouse/keyboard input handling
  - [ ] UI drawing (sidebar, popups, etc.)

### **1.2 Mode Configuration System**
- [ ] Add `mode` parameter to core class (`'practice'` or `'official'`)
- [ ] Create feature flags:
  ```python
  self.features = {
      'debug_mode': mode == 'practice',
      'mask_overlay': mode == 'practice', 
      'skip_markers': mode == 'practice',
      'jump_to_marker': mode == 'practice',
      'speed_control': mode == 'practice',
      'show_debug_info': mode == 'practice'
  }
  ```

### **1.3 Refactor Mode-Specific Files**
- [ ] `perception_test_v2.py` → thin wrapper that enables all features
- [ ] `perception_test_official.py` → thin wrapper that disables practice features
- [ ] Both files import and configure the core class

---

## 📋 **Phase 2: Code Quality Improvements**

### **2.1 Configuration Management**
- [ ] Create `config.py` for all settings:
  ```python
  # config.py
  VIDEO_PATH = "videos/Without annotations (edited).mp4"
  MARKERS_PATH = "data/new_perception_markers.csv"
  SIDEBAR_WIDTH = 540
  WINDOW_TITLES = {
      'practice': "Perception Test - Practice Mode",
      'official': "Perception Test - Official Test Mode"
  }
  ```

### **2.2 Separate Concerns**
- [ ] Create `video_manager.py` - handle video playback
- [ ] Create `marker_manager.py` - handle marker loading/processing
- [ ] Create `question_handler.py` - handle different question types
- [ ] Create `results_manager.py` - handle logging and export
- [ ] Create `ui_manager.py` - handle all UI drawing

### **2.3 Error Handling**
- [ ] Add proper exception handling for:
  - [ ] Video file not found
  - [ ] Marker file not found
  - [ ] Mask file not found
  - [ ] Invalid marker data
- [ ] Add logging system for debugging

### **2.4 Type Hints and Documentation**
- [ ] Add type hints to all functions
- [ ] Add docstrings to all classes and methods
- [ ] Create README with setup and usage instructions

---

## 📋 **Phase 3: Testing and Validation**

### **3.1 Unit Tests**
- [ ] Test marker loading
- [ ] Test question processing
- [ ] Test results logging
- [ ] Test CSV export
- [ ] Test mode-specific features

### **3.2 Integration Tests**
- [ ] Test full practice mode workflow
- [ ] Test full official mode workflow
- [ ] Test review screen functionality

### **3.3 Validation**
- [ ] Ensure official mode has NO practice features
- [ ] Ensure practice mode has ALL features
- [ ] Test both modes with same video/markers

---

## 📋 **Phase 4: Future-Proofing**

### **4.1 Plugin System**
- [ ] Design system for adding new question types
- [ ] Design system for adding new UI themes
- [ ] Design system for adding new export formats

### **4.2 Database Integration**
- [ ] Plan for moving from CSV to proper database
- [ ] Design schema for storing results
- [ ] Plan for multi-user support

### **4.3 Web Interface**
- [ ] Plan for web-based version
- [ ] Design API endpoints
- [ ] Plan for remote administration

---

## 🚀 **Quick Start for Future Development**

### **When You Return:**
1. **Read this TODO list**
2. **Start with Phase 1.1** (Create shared core class)
3. **Test thoroughly** after each phase
4. **Keep both modes working** throughout refactor

### **File Structure After Refactor:**
```
perception_test/
├── core/
│   ├── __init__.py
│   ├── perception_test_core.py
│   ├── video_manager.py
│   ├── marker_manager.py
│   ├── question_handler.py
│   ├── results_manager.py
│   └── ui_manager.py
├── config.py
├── perception_test_v2.py          # Practice mode
├── perception_test_official.py    # Official mode
├── requirements.txt
├── README.md
└── tests/
    ├── test_core.py
    ├── test_practice.py
    └── test_official.py
```

### **Benefits After Refactor:**
- ✅ **One place** to add new features
- ✅ **Easy testing** of both modes
- ✅ **No code duplication**
- ✅ **Professional codebase**
- ✅ **Easy to extend** for new requirements
- ✅ **Easy for new developers** to understand

---

## 📝 **Notes for Sud (Your Boss)**

### **Why This Refactor is Important:**
1. **Maintainability:** Currently, any bug fix or new feature must be done twice
2. **Reliability:** Code divergence between modes can introduce bugs
3. **Scalability:** Adding new features becomes harder over time
4. **Professional Standards:** Clean, well-structured code is easier to fund and support

### **Time Investment:**
- **Phase 1:** 2-3 days (core refactor)
- **Phase 2:** 1-2 days (code quality)
- **Phase 3:** 1 day (testing)
- **Total:** 4-6 days for complete refactor

### **ROI:**
- **Immediate:** Easier to add features, fewer bugs
- **Long-term:** Professional codebase, easier to get funding
- **Team:** New developers can contribute more easily

---

**Last Updated:** [Current Date]
**Status:** Ready for implementation when funding is secured 