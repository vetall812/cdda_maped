# Settings Package Structure

The settings package has been refactored into a modular, maintainable structure.

## Architecture

```txt
cdda_maped/settings/
├── __init__.py           # Public API exports
├── types.py              # Type definitions and enums
├── migration.py          # Version migration system
├── validation.py         # Settings validation
├── paths.py              # Path-related settings
├── ui.py                 # UI-related settings
├── editor.py             # Editor-related settings
├── logging.py            # Logging-related settings
└── core.py               # Main AppSettings class
```

## Design Principles

1. **Single Responsibility**: Each module handles one aspect of configuration
2. **Composition**: AppSettings composes specialized settings classes
3. **Type Safety**: Strong typing throughout with helper methods
4. **Cross-Platform**: Uses Qt's QSettings for platform-native storage
5. **Migration Support**: Versioned configuration with automatic migration

## Module Responsibilities

### `types.py`

- `ConfigVersion` enum for version management
- `ConfigError` exception class
- `ValidationResult` dataclass for validation results

### `migration.py`

- `SettingsMigrator` class handles version upgrades
- Automatic detection of version changes
- Migration logic between configuration versions

### `validation.py`

- `SettingsValidator` class validates configuration
- Path existence checking
- Recent files cleanup
- Comprehensive error and warning reporting

### `paths.py`

- `PathSettings` class manages all path-related configuration
- CDDA game path with derived data/tilesets paths
- Recent files management
- Type-safe path operations

### `ui.py`

- `UISettings` class manages UI configuration
- Window geometry save/restore
- Theme management
- Cross-platform window state handling

### `editor.py`

- `EditorSettings` class manages editor configuration
- Default tileset selection
- Grid visibility settings
- Zoom level management

### `logging.py`

- `LoggingSettings` class manages logging configuration
- Log level control with validation
- Console/file output toggles

### `core.py`

- `AppSettings` main class orchestrates all subsystems
- Delegates to specialized settings classes
- Maintains backward compatibility
- Provides unified API

## Usage

```python
from cdda_maped.settings import AppSettings, ValidationResult

# Create settings instance
settings = AppSettings()

# Access different setting categories
print(f"CDDA Path: {settings.cdda_path}")
print(f"Theme: {settings.theme}")
print(f"Log Level: {settings.log_level}")

# Validate configuration
result = settings.validate()
if not result.is_valid:
    print("Configuration errors:", result.errors)
```

## Benefits

1. **Maintainability**: 400+ line monolith split into focused modules
2. **Testability**: Each component can be tested independently
3. **Extensibility**: New setting categories easy to add
4. **Readability**: Clear separation of concerns
5. **Reusability**: Settings components can be reused elsewhere
