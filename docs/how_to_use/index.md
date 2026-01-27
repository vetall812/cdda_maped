# How to Use

## Quick Start

### Using Executables [To Be Done]

1. > TODO: Add CI/CD pipeline
2. > TODO: Add `Download` section

### Using Python Sources

1. Clone the repository
2. Install dependencies using the following command:

   ```sh
   pip install -r requirements.txt
   pip install -e .
   ```

3. Run the project:

   ```sh
   python -m cdda_maped
   ```

4. After start, you will be prompted for the CDDA game path

## Project Windows

### Common Concepts

- Window size and location are saved on close/exit and restored on load/open
- Selectors also save and restore their settings
- Widgets can be rearranged and their positions are saved
- Widget positions can be reset to defaults

### Main Window

Currently a stub. You can ignore it for now.
It also opens the Object Explorer window.

### Object Explorer

**Main widgets:**

- Ortho demo map view
- Iso demo map view

**JSON view widgets:**

- Game data JSON
- Ortho tileset JSON
- Iso tileset JSON

**Object browser selector:** Helper widget that receives objects from the main window.

**Additional selectors:** Some are still stubs.

[Detailed Object Explorer window overview.](object_explorer/oe_overview.md)

### Log (For Developers)

The logging system is primarily for developers.

**Logging targets:**

- Memory (when application runs with GUI)
- Log files (when GUI is unavailable, e.g., unit tests)
- Console (for quick reference, without function names or line numbers)
