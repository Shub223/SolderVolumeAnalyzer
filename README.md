# Gerber Solder Volume Analyzer

A desktop application for analyzing solder paste volumes from Gerber files. This tool helps PCB manufacturers and designers calculate and visualize solder paste volumes across their boards.

## Features

### Version 1.0
- Load and parse Gerber files (solder paste layers)
- Calculate solder volumes based on pad geometry
- Interactive 2D visualization with:
  - Color-coded pads based on volume
  - Zoom controls (Zoom In, Zoom Out, Fit View)
  - Grid overlay for measurements
- Detailed pad information table showing:
  - Pad ID
  - Shape type
  - Area
  - Thickness
  - Volume
- Status bar displaying:
  - Current file name
  - Total pad count
  - Total solder volume
- Export capabilities:
  - CSV format
  - Excel format
- Comprehensive logging for debugging

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd GerberSolderVolumeAnalyzer
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python run.py
```

2. Use the "Load Gerber File" button to open a Gerber file
3. View pad information in the table
4. Use zoom controls to navigate the PCB view
5. Export data using the "Export Data" button

## Requirements

- Python 3.12+
- PyQt6
- Matplotlib
- Shapely
- Pandas
- See requirements.txt for full dependency list

## Development

This project uses:
- PyQt6 for the GUI
- Matplotlib for visualization
- Shapely for geometric operations
- Pandas for data export

### Project Structure
```
GerberSolderVolumeAnalyzer/
├── src/
│   ├── gui/
│   │   ├── main_window.py    # Main application window
│   │   ├── pcb_view.py       # PCB visualization
│   │   └── volume_table.py   # Volume data table
│   ├── gerber_parser.py      # Gerber file parser
│   └── main.py              # Application entry point
├── run.py                   # Startup script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Version History

### v1.0 (Current)
- Initial release with basic functionality
- Gerber file parsing
- Volume calculation
- Interactive visualization
- Data export capabilities
