# Adventure Minecraft Server Guide

This guide provides detailed instructions for setting up and administering an Adventure Minecraft server.

## Quick Start

1. Install Docker and Docker Compose
2. Clone the repository: `git clone https://github.com/username/AdventureMinecraft.git`
3. Start the server: `docker-compose up -d`
4. Check logs: `docker-compose logs -f`

## Server Features

The Adventure Minecraft server includes:
- Dungeon exploration with unique structures
- Quest and mission systems
- Custom items and weapons
- Pet and animal enhancements
- Enhanced villager behavior
- Performance optimizations

## Server Configuration

### docker-compose.yml

The server is configured via `docker-compose.yml`. Important settings:

```yaml
environment:
  MEMORY: "4G"         # Server memory allocation
  OPS: "username"      # Admin username(s)
  DIFFICULTY: "normal" # Game difficulty
  VIEW_DISTANCE: "12"  # View distance in chunks
```

### Known Issues and Fixes

#### BiomeSpreader Mod

This modpack includes a fix for the BiomeSpreader mod, which looks for a file with a space in the name. The fix is automatically applied on server startup via:

```yaml
PRE_INIT_SCRIPT: >
  mkdir -p /data/mods && 
  cp -f /data/mods/BiomeSpreader-1.5.0+mc1.21.5.jar "/data/mods/BiomeSpreader-1.5.0 mc1.21.5.jar" || true
```

#### Dependencies and Compatibility

The server automatically removes known problematic mods, but if you encounter issues, check:
- Incompatible Java versions (some mods require Java 22, server runs on Java 21)
- Missing dependencies
- Client-side mods accidentally included on the server

### Managing Mods

#### Adding Mods

1. Add the mod to `scripts/modpack_profiles/enhanced_adventure_pack.txt`
2. Tag it as `[server]`, `[client]`, or `[shared]`
3. Run the download script: `python scripts/download_mods.py --profile --profile-name enhanced_adventure_pack.txt`

#### Creating Client Packs

After updating mods, create a new client pack to distribute:

```bash
python scripts/download_mods.py --client --profile-name enhanced_adventure_pack.txt
```

Distribute `enhanced_adventure_pack-1.21.5-fabric.zip` to players.

## Backup and Management

### Backing Up World Data

To create a backup of the world:

```bash
docker-compose exec minecraft tar -czf /tmp/world_backup.tar.gz /data/adventure_world
docker cp adventure_minecraft:/tmp/world_backup.tar.gz ./backups/
```

### Server Commands

Connect to the server console:

```bash
docker-compose exec minecraft rcon-cli
```

Common commands:
- `/op username` - Make a player an operator
- `/gamerule keepInventory true` - Keep inventory on death
- `/gamerule doMobSpawning true` - Enable mob spawning
- `/kill @e[type=item]` - Remove dropped items
- `/time set day` - Set time to day

## Troubleshooting

### Server Won't Start

1. Check logs: `docker-compose logs`
2. Verify mod compatibility in logs
3. Check for missing dependencies
4. Ensure sufficient memory is allocated
5. Verify file permissions

### Performance Issues

1. Reduce VIEW_DISTANCE in docker-compose.yml
2. Remove resource-intensive mods
3. Allocate more memory to the server
4. Check for mod conflicts

### Client Connection Issues

1. Verify client has all required shared mods
2. Check server firewall settings
3. Verify port 25565 is forwarded if behind a router
4. Check for version mismatches

## Additional Resources

- [Fabric Mod Documentation](https://fabricmc.net/wiki/start)
- [Docker Minecraft Server Image](https://github.com/itzg/docker-minecraft-server)
- [Minecraft Server Properties](https://minecraft.fandom.com/wiki/Server.properties)
EOL < /dev/null
