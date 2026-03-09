# Sprocket Tools for Blender

Blender plugin for importing and exporting Sprocket tank blueprint files.

This project used https://github.com/ArgoreOfficial/SPETS as a reference to understand the blueprint format.

The Blender extension page is https://extensions.blender.org/add-ons/sprocket-tools/

## Installation through Blender

1. In the Blender interface, go to Edit > Preferences > Extensions
2. Allow Blender to go online to look to extensions in the official repositories
3. Search for "Sprocket Tools"
4. Click the "Install" button

## Manual Installation

1. Download latest `sprocket_tools-x.x.x.zip` release
2. Open Blender
3. Go to Edit > Preferences > Add-ons
4. Click the down arrow in the top-right-hand corner
5. Click "Install from disk..." and select the zip file
6. You may need to enable the addon by checking the box next to "Sprocket Tools"

## Configuration

### Sprocket Path setup

The addon automatically fills in the Sprocket data directory with the defaults for your platform:

- **Windows**: `%USERPROFILE%\Documents\My Games\Sprocket`
- **Linux (Proton)**: `~/.steam/steam/steamapps/compatdata/1674170/pfx/drive_c/users/steamuser/My Documents/My Games/Sprocket`

### Manual Path Configuration

If the default fails:

1. Go to Edit > Preferences > Add-ons
2. Find "Sprocket Tools" and expand it
3. Set "Sprocket Data Path" manually

## Usage

### Importing Blueprints

1. Open the Sprocket sidebar in the 3D Viewport (press N if hidden)
2. Select the "Sprocket Import" tab
3. Choose a faction from the dropdown
4. Click "Load Faction Blueprints" to refresh the list
5. Select a blueprint from the list
6. Click "Import Blueprint"

The imported mesh will appear in your scene with thickness data stored in the `sprocket_thickness` face attribute.

### Exporting Compartments

1. Select your mesh object in Object Mode
2. Open the "Sprocket Export" tab
3. Select the target faction
4. Enter a name for the compartment
5. Set default thickness if needed
6. Click "Export Compartment"

The exported `.blueprint` file will be saved to:
`Factions/[Faction]/Blueprints/Plate Structures/[Name].blueprint`
The part name within Sprocket will be the object name within Blender

## Thickness Data

- Imported blueprints store original thickness in the `sprocket_thickness` face attribute
- View and edit this in Mesh Properties > Attributes
- Exported compartments use default thickness if no attribute is present

## File Format Support

- **Import**: `.blueprint` files (Plate Structures and Vehicles)
- **Export**: `.blueprint` files (Plate Structures only)

## Troubleshooting

### No factions found

Verify your Sprocket data path is correct in the addon preferences. The path should contain a `Factions` directory.

### Mesh has holes or missing faces

Ensure your mesh is manifold (watertight) with no duplicate vertices before exporting. Use Blender's Mesh > Clean Up > Merge by Distance if needed.

### Known Issues

The exported files are larger than they should be. I'm trying to clean things up so redundant geometry isn't produced on export.
