# Object Explorer Window overview

## Default layout

This window's default layout contains four areas. Everything except the two map views can be detached or rearranged. If you prefer to work with only one map view, you can adjust the slider to hide the unwanted one.

If you close any widget or change the layout, you can use the corresponding menu to restore it.

### Top side widget

Here you can see a set of selectors that allow you to change tilesets, the demo map, season, and zoom. Time of day and weather are stubs for now.

### Left side widget

This widget contains the default game object selector. After the first start, a random object will be selected and placed over the center of the demonstration map.

You can place one object per cell slot simultaneously.
> Example: select and place terrain, then furniture, then an item.

### Right side widget

Here you can see three tabs related to the selected object:

- Game data
- Ortho tileset data
- Iso tileset data

Keep in mind that JSON properties that start with an underscore relate to `CDDA-maped` internal algorithms.
> Examples:  `_original_id`, `_resolved_via`, `_actual_id`, `_mod_id` or `_source_file` that you can use in your work

### Central area

This area is divided into two parts:

- top - ortho view
- bottom - iso view

This view provides a single z-level by default (you can change this in the main window settings).

Over this view there is an overlay that contains:

- top left - animation button and framerate indicator
- top right - pattern UI that can place the same object in a 3x3 grid and control the `CONNECTS_TO` property and corresponding multitile sprites
- bottom left - transparency button (you can see this in the default demo map: tree in `Ultica_iso` will be hidden)
- bottom central (optional to ISO view) - can rotate view and reset rotation
- bottom right (not implemented yet) - current cell coordinates

## Keyboard actions

Most actions in this window are related to the Numpad keys:

| key | meaning |
| --- | :--- |
| `del .` | toggle animation |
| `ins 0` | toggle transparency |
| `/` `*` `-` | iso view rotation |
| `1` .. `9` | object pattern toggle |
| `+` | focus to ortho map view |
| `Enter` | focus to iso map view |
| `cursor` | pan selected view |
| `PgUp` | go one z-level up |
| `PgDown` | go one z-level down |
