# MCUtil - Minecraft Server Manager

Simple yet powerful tool to manage your Minecraft server. Auto-restart, backups, and more!

## Commands at a Glance

```
SETUP        mcutil setup
SERVER       mcutil start | stop | restart | status
BACKUPS      mcutil backup | schedule-backups
MONITORING   mcutil logs | watch | stats | players
COMMANDS     mcutil cmd "command" | say "message"
```

## Initial Setup

```bash
mcutil setup
```

This creates a config file (`~/.mcserverconfig.json`) with:

| Setting              | Description                  | Default             |
|----------------------|------------------------------|---------------------|
| SERVER_JAR           | Server executable            | server.jar          |
| SERVER_DIR           | Server location              | ~/minecraft-server  |
| BACKUP_DIR           | Backup storage               | ~/minecraft-backups |
| JAVA_OPTIONS         | Java memory settings         | -Xmx2G -Xms1G       |
| SCREEN_NAME          | Screen session name          | minecraft           |
| MAX_BACKUPS          | Number to keep               | 5                   |
| WATCHDOG_INTERVAL    | Auto-restart check (seconds) | 60                  |
| AUTO_BACKUP_INTERVAL | Backup frequency (minutes)   | 720 (12h)           |

## Server Control

```bash
mcutil start     # Start the server
mcutil stop      # Stop the server
mcutil restart   # Restart the server
mcutil status    # Check if running
```

## Backup Management

```bash
mcutil backup             # Create backup now
mcutil schedule-backups   # Start auto-backup daemon (Ctrl+C to stop)
```

## Monitoring Tools

```bash
mcutil logs      # Show server log
mcutil watch     # Auto-restart if server crashes (Ctrl+C to stop)
mcutil stats     # Show CPU, memory, and world size
mcutil players   # List online players
```

## Server Commands

```bash
mcutil cmd "whitelist add PlayerName"   # Run any command
mcutil say "Server restarting in 5 min"  # Broadcast message
```

## Common Workflows

**Server Startup**
```bash
mcutil start
mcutil watch &  # Background auto-restart
```

**Server Maintenance**
```bash
mcutil say "Maintenance in 5 minutes!"
mcutil backup
mcutil stop
# Do maintenance
mcutil start
```

**Auto-Managed Server**
```bash
mcutil watch &
mcutil schedule-backups &
```

## Notes

- Uses `screen` for background operation
- Backups include worlds, config, and player data
- Old backups auto-deleted based on MAX_BACKUPS setting