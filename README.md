# `🗺️'d`&nbsp;[![CI](https://github.com/vetall812/cdda_maped/workflows/CI/badge.svg)](https://github.com/vetall812/cdda_maped/actions/workflows/ci.yml) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Cataclysm: Dark Days Ahead - Map Editor

cdda_maped is an experimental graphical editor designed for creating and editing [Cataclysm: Dark Days Ahead (CDDA)](https://github.com/CleverRaven/Cataclysm-DDA) maps without the need to manually write JSON. The project's goal is to provide authors with a convenient visual tool, comparable in feel to familiar graphical editors, while leveraging the rich capabilities of CDDA mapgen.

### Project Goals

- Simplify the map creation process for CDDA
- Provide a visual interface for preview in any tileset
- Create plausible maps with proper object scaling without introducing unnecessary changes to the game's graphics engine, but only using the existing rich capabilities

### Planned Features

- Drawing primitives
- Area fills, gradients, patterned placement (e.g., windows in walls, pillars along fences)
- Layer management
- Map preview in different tilesets, seasons, times of day, and weather conditions
- Testing nested mapgen templates with selection of specific random variants

- No built-in graphics editor — only visualization of existing resources

- Vehicle editor
- Character overlay editor

### Current Status

The project is preparing internal mechanisms—working with graphics, objects, and data structures.
CDDA map parsing is not yet implemented.

### Requirements

- Python 3.10+
- Use of standard cross-platform libraries

### Target Audience

The tool is aimed at CDDA contributors and mod authors who need a convenient way to work with maps.

### Architecture (high-level)

Users will need:

- cdda_maped repository
- Installed CDDA game
- Python 3.10+
- Dependencies from requirements.txt

### Modules and Components

- game_data — working with game JSON
- tilesets — working with tilesets
- maps — map model
- gui — interface (PySide6/Qt)
- main_window — main window
- settings — configuration
- resources — application resources
- utils — utility modules

### Further Reading

- [How to Use](docs/how_to_use/index.md) — usage guide and project interface overview
