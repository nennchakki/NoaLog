# NoaLog

Cross-platform OCR Conversation Log Tool

## Overview

NoaLog is a desktop application that captures text from any running application (games, visual novels, streams, etc.) using OCR, and saves structured conversation logs.

## Features

- **Profile-based capture**: Define header and body regions for different applications
- **Hotkey trigger**: Register custom hotkey combinations (2+ keys) to capture text
- **OCR processing**: Uses PaddleOCR for Japanese text recognition
- **Structured logs**: Automatically parse speaker name/organization and body text
- **Log management**: View, edit, copy, and export conversation logs
- **Cross-platform**: Supports macOS and Windows

## Requirements

- Python 3.10+
- macOS 11+ or Windows 10+

### macOS Permissions

NoaLog requires the following permissions on macOS:
- **Screen Recording**: To capture screen content
- **Accessibility**: To detect global hotkeys

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/noalog/noalog.git
cd noalog

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Run the application
noalog
```

### Development Setup

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
isort src tests

# Type checking
mypy src
```

## Quick Start

### Key Bindings

| Key | Function |
|-----|----------|
| `Cmd+Shift+R` | Start region selection mode |
| `Cmd+Shift+L` | Execute OCR capture |
| `Enter` | Confirm selection / Confirm edit |
| `ESC` | Cancel |

### Basic Workflow

1. **Launch**: `cd ~/NoaLog && source venv/bin/activate && noalog`

2. **Set capture regions** (first time):
   - Press `Cmd+Shift+R`
   - Drag to select header region (speaker name) → `Enter`
   - Drag to select body region (dialogue text) → `Enter`

3. **Capture text**:
   - Display target application
   - Press `Cmd+Shift+L` to capture

4. **Edit logs**:
   - Double-click on log entries to edit
   - `Enter` to confirm, `ESC` to cancel

See [docs/USAGE.md](docs/USAGE.md) for detailed usage instructions.

## Project Structure

```
NoaLog/
├── src/
│   ├── core/
│   │   ├── capture/    # Screen capture
│   │   ├── ocr/        # OCR processing
│   │   ├── hotkey/     # Hotkey management
│   │   └── storage/    # Data persistence
│   ├── ui/
│   │   ├── views/      # Main views
│   │   ├── widgets/    # Custom widgets
│   │   └── styles/     # Themes
│   └── utils/          # Utilities
├── tests/              # Test code
├── docs/               # Documentation
├── profiles/           # User profiles
└── logs/               # Conversation logs
```

## Technology Stack

- **Language**: Python 3.10+
- **UI**: PySide6 (Qt6)
- **Image Processing**: OpenCV
- **OCR**: PaddleOCR
- **Screen Capture**: mss
- **Hotkey**: pynput

## Contact
For licensing inquiries, please open an issue on this repository.

## License

See [LICENSE](LICENSE).

## Contributing

Contributions are welcome! Please see the development documentation for guidelines.
