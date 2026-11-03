# Muse App

## Overview
The Muse App is a Python application designed to interface with the Muse headset, providing functionalities for data visualization and interactive gaming. It utilizes PyQt6 for the main GUI and Tkinter for game rendering.

## Project Structure
```
muse-app
├── src
│   ├── main.py                # Entry point of the application
│   ├── gui
│   │   ├── pyqt_interface.py   # PyQt6 interface for the application
│   │   └── tkinter_game.py     # Game window using Tkinter
│   ├── muse
│   │   ├── muse_data.py        # Handles data from the Muse headset
│   │   └── muselsl_interface.py # Interfaces with the muselsl library
│   └── utils
│       └── helpers.py          # Utility functions for the application
├── requirements.txt            # Project dependencies
└── README.md                   # Project documentation
```

## Requirements
To run this project, you need to install the following dependencies:

- Python 3.12
- muselsl
- PyQt6
- Tkinter

You can install the required packages by running:

```
pip install -r requirements.txt
```

## Usage
1. Connect your Muse headset.
2. Run the application using the command:
   ```
   python src/main.py
   ```
3. Follow the on-screen instructions to visualize data or play the game.

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.