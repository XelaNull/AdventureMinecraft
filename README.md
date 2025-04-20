# Adventure Minecraft Modpack

A feature-rich Minecraft modpack for Fabric 1.21.5 with adventure, dungeons, quests, and more.

## Features

- Dungeon exploration and challenges
- Beautiful world generation with unique structures
- Quest and mission systems
- Epic boss battles and improved combat
- Unique animals and creatures
- Maps for navigation
- Performance improvements for smooth gameplay
- Quality of life features
- Furniture and decoration mods

## Getting Started

### Server Setup

1. Install Docker and Docker Compose
2. Clone this repository
3. Run `docker-compose up -d` to start the server
4. See the [Server Guide](SERVER_GUIDE.md) for details on configuration

### Client Setup

1. Install Minecraft 1.21.5
2. Install [Fabric Loader 0.16.13](https://fabricmc.net/use/installer/)
3. Download the client pack from the server admin
4. Extract the client pack and follow the README.txt instructions

### For Server Admins

#### Mod Management System

This modpack uses a sophisticated system to categorize mods:

- **[server]** - Server-only mods (administration utilities)
- **[client]** - Client-only mods (UI, graphics, visual enhancements)
- **[shared]** - Mods needed on both server and client

Each mod is tagged in the `scripts/modpack_profiles/enhanced_adventure_pack.txt` file to ensure proper distribution.

#### Creating Client Packs

To create a client pack for your players:

```bash
python3 scripts/download_mods.py --client --profile-name enhanced_adventure_pack.txt
```

This will generate `enhanced_adventure_pack-1.21.5-fabric.zip` in the project root.

#### Testing Mod Categorization

To validate that your mods are properly categorized:

```bash
bash scripts/test_mod_explorer.sh
```

This will check for incompatible mods and ensure proper distribution.

## Requirements

### Server

- 4GB+ RAM
- Docker and Docker Compose
- Python 3.6+ (with requests, tqdm, argparse, colorama)

### Client

- Minecraft 1.21.5
- Fabric Loader 0.16.13
- 4GB+ RAM allocated to Minecraft

## Performance Optimization

The modpack includes several performance-enhancing mods:

- Lithium
- Sodium (client-only)
- FerriteCore
- EntityCulling
- Krypton
- C2ME

## Contributing

Feel free to suggest additional mods or improvements by creating issues or pull requests.