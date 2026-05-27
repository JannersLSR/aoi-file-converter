# All-in-One Media Converter

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
[![Download](https://img.shields.io/badge/Download-v1.0.0-6366F1?style=flat)](https://github.com/JannersLSR/aoi-file-converter/releases/download/v1.0.0/MediaConverter.exe)

> **[⬇ Download MediaConverter.exe (v1.0.0)](https://github.com/JannersLSR/aoi-file-converter/releases/download/v1.0.0/MediaConverter.exe)** — Windows 10/11 x64 · No install required

A high-performance, premium desktop application for batch cross-converting media files. Built with a refined dark mode user interface inspired by modern design systems, the application integrates a robust multi-threaded transcode engine capable of seamless, non-blocking 5x5 cross-conversions.

---

## Features

- **Multithreaded Batch Pipeline**: Queue multiple media files and convert them sequentially in the background. The Tkinter GUI remains fully interactive and fluid throughout.
- **Dynamic Progress Parsing**: Reads FFmpeg standard error outputs in real-time using asynchronous background daemon threads, calculating exact transcoding percentages without freezing.
- **Simplified Layout and Auto-Detect**: Standardized source format auto-detection with the target format selector expanded across the entire selection row for a spacious and balanced interface.
- **Process Safety and Exit Guard**: Terminates and waits on underlying transcode operations if cancelled or if the window is closed, preventing orphan FFmpeg background processes.
- **Premium Visual Aesthetics**:
  - Dark Mode Default (#0B0F19 deep slate blue background) with harmonious neon indigo (#6366F1) accents.
  - Standardized modern typography using clean Windows-native font-family systems.
  - Minimalist, distraction-free typography for action links (clean "Cancel" and "Remove" buttons without visual character noise).
- **Advanced Custom Settings**:
  - Global default output directory selectors.
  - Video CRF (Constant Rate Factor) scale settings.
  - GIF export optimization (custom FPS and target scale width).
- **Recent Transcodes Log**: Persistence of completed jobs allowing quick-launch actions ("Folder" and "Play") directly from the history view.
- **True OS-Level Drag and Drop**: Native drag-and-drop file additions powered by `tkinterdnd2`.

---

## Tech Stack and Modular Architecture

The application is decomposed into three high-integrity Python modules:

1. **`app.py`**: The visual presentation and interface layer. Handles responsive widgets, scrolling boundaries, dialog geometry centering, and hover/click event bindings.
2. **`engine.py`**: The core transcoding pipeline. Spawns, controls, and polls asynchronous OS subprocesses (FFmpeg via `imageio-ffmpeg`) on dedicated worker threads. Uses `Pillow` for animated WebP/GIF conversions that do not require a video pipeline.
3. **`config.py`**: System settings and transcode history serialization layer mapping inputs into persistent JSON files.

---

## Prerequisites and System Dependencies

No external tools required. All dependencies are bundled as Python packages:

- **`imageio-ffmpeg`** — ships a pre-built static FFmpeg binary. No separate FFmpeg installation needed.
- **`Pillow`** — handles animated WebP and GIF conversions natively.
- **`tkinterdnd2`** — provides OS-level drag-and-drop support.

---

## How to Run Locally

### 1. Install Python Dependencies
```bash
pip install tkinterdnd2 imageio-ffmpeg Pillow
```

### 2. Launch the Application
```bash
python app.py
```

---

## Compiling to a Standalone Executable

You can compile the application into a single-file executable using **PyInstaller**. This allows users to run the All-in-One Media Converter instantly with zero Python installation required.

### 1. Install PyInstaller
```bash
pip install pyinstaller
```

### 2. Run the Build Script
The `--add-data` flag requires the path to `tkinterdnd2`'s native binaries. Resolve it automatically with the two-step PowerShell command below:

```powershell
$tkdnd = python -c "import tkinterdnd2, os; print(os.path.join(os.path.dirname(tkinterdnd2.__file__), 'tkdnd'))"
pyinstaller --onefile --noconsole --name "MediaConverter" --add-data "$tkdnd;tkinterdnd2/tkdnd" app.py
```

### 3. Retrieve the Compiled App
The resulting standalone executable will be generated inside the `dist/` directory as **`MediaConverter.exe`**. Since compiled executables are large binary files, the output folder is configured under `.gitignore` to maintain a clean and lightweight repository.