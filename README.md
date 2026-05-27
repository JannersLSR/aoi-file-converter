# All-in-One Media Converter

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
2. **`engine.py`**: The core transcoding pipeline. Spawns, controls, and polls asynchronous OS subprocesses (FFmpeg and ImageMagick) on dedicated worker threads.
3. **`config.py`**: System settings and transcode history serialization layer mapping inputs into persistent JSON files.

---

## Prerequisites and System Dependencies

To run the source code or the compiled executable, ensure that **FFmpeg** and **ImageMagick** are installed on your machine and present in your system's `PATH`:

1. **FFmpeg**: Required for processing all video formats (.mp4, .webm, .mov, .gif).
   - Download from [ffmpeg.org](https://ffmpeg.org/), extract, and add the `bin` directory to your System Environment variables.
2. **ImageMagick**: Required for conversions where `.webp` is the **source** format, and for `gif → webp`. Conversions such as `mp4 → gif`, `gif → mp4`, and `mp4 → webp` use FFmpeg only and do not require ImageMagick.
   - Download from [imagemagick.org](https://imagemagick.org/) and verify the `magick` command is executable in your terminal.

---

## How to Run Locally

### 1. Install Python Dependencies
Install the required window manager drag-and-drop bindings:
```bash
pip install tkinterdnd2
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