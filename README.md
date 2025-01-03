# Gerber Solder Volume Analyzer

A desktop application for analyzing solder paste volumes from Gerber files. This tool helps PCB manufacturers and designers calculate and visualize solder paste volumes across their boards.

## Features

### Version 1.2 (Current)
- Interactive PCB view with:
  - Smooth zoom to cursor
  - Pan with left mouse button
  - Color-coded pads based on volume
  - Grid overlay for measurements
  - Colorbar showing volume scale
- Detailed pad information table showing:
  - Pad ID
  - Shape type
  - Length and width
  - Area
  - Thickness
  - Volume
- Load and parse Gerber files (solder paste layers)
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
git clone https://github.com/Shub223/SolderVolumeAnalyzer.git
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
3. Navigate the PCB view:
   - Zoom: Use mouse wheel
   - Pan: Click and drag with left mouse button
   - Reset view: Click "Fit View"
4. View pad information in the table
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
│   └── gerber_parser.py      # Gerber file parser
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Version History

### v1.2
- Improved PCB viewer with smooth zoom and pan
- Enhanced window layout and centering
- Fixed colorbar positioning
- Added pad length and width measurements
- Code cleanup and organization

### v1.1
- Added pad measurements (length and width)
- Improved table display with new measurements
- Enhanced code organization

### v1.0
- Initial release with basic functionality
- Gerber file parsing
- Volume calculation
- Interactive visualization
- Data export capabilities
