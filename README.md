# MCUtil - Enhanced Minecraft Server Manager

Powerful tool to manage your Minecraft server with intelligent multi-type backups, auto-restart, and monitoring!

## 🎯 Commands at a Glance

```
SETUP        mcutil setup
SERVER       mcutil start | stop | restart | status
BACKUPS      mcutil backup | schedule-backups | stop-backups | backup-status
MONITORING   mcutil watch
COMMANDS     mcutil cmd "command"
```

## 🚀 Initial Setup

```bash
mcutil setup
```

This creates a config file (`~/.mcserverconfig.json`) with these settings:

| Setting                      | Description                    | Default             |
|------------------------------|--------------------------------|---------------------|
| SERVER_JAR                   | Server executable              | server.jar          |
| SERVER_DIR                   | Server location                | ~/minecraft-server  |
| BACKUP_DIR                   | Backup storage                 | ~/minecraft-backups |
| JAVA_OPTIONS                 | Java memory settings           | -Xmx2G -Xms1G       |
| SCREEN_NAME                  | Server screen session          | minecraft           |
| **Enhanced Backup Settings** |                                |                     |
| AUTO_BACKUP_REGULAR_INTERVAL | Regular backup frequency (min) | 240 (4h)            |
| AUTO_BACKUP_MEDIUM_INTERVAL  | Medium backup frequency (min)  | 1440 (24h)          |
| AUTO_BACKUP_HARD_INTERVAL    | Hard backup frequency (min)    | 10080 (7d)          |
| BACKUP_SCHEDULER_SCREEN      | Backup scheduler session       | mcutil-backups      |
| MAX_REGULAR_BACKUPS          | Regular backups to keep        | 12 (2 days)         |
| MAX_MEDIUM_BACKUPS           | Medium backups to keep         | 7 (1 week)          |
| MAX_HARD_BACKUPS             | Hard backups to keep           | 4 (1 month)         |

## 🖥️ Server Control

```bash
mcutil start             # Start the server
mcutil start --gui       # Start with GUI
mcutil start --ram 4G    # Start with custom RAM
mcutil stop              # Stop the server
mcutil restart           # Restart the server
mcutil status            # Show live server status
mcutil cmd "say Hello!"  # Send command to server
```

## 💾 Enhanced Backup System

### Backup Types

| Type     | Description                                    | Contents                                    |
|----------|------------------------------------------------|---------------------------------------------|
| Regular  | Quick world saves and essential configs       | Worlds, server properties, player data     |
| Medium   | Comprehensive backup with mods and configs    | Regular + mods, configs, user data         |
| Hard     | Complete server backup (everything)           | All server files                           |

### Manual Backups
```bash
mcutil backup                      # Regular backup (default)
mcutil backup --type medium        # Medium backup
mcutil backup --type hard          # Hard/complete backup
mcutil backup --include "world,mods" --exclude "logs"  # Custom backup
mcutil backup-types               # List all backup types
```

### 🤖 Intelligent Auto-Backup Scheduler

The scheduler runs **all three backup types** automatically in the background:

```bash
mcutil schedule-backups    # Start intelligent multi-type scheduler
mcutil backup-status       # View scheduler status and backup stats
mcutil stop-backups        # Stop the scheduler
```

**Default Schedule:**
- **Regular backups**: Every 4 hours (quick protection)
- **Medium backups**: Every 24 hours (comprehensive daily backup)
- **Hard backups**: Every 7 days (complete weekly backup)

**Organized Storage:**
```
~/minecraft-backups/
├── regular/
│   ├── 2025-05-21/server_backup_regular_14-30-00.zip
│   └── 2025-05-21/server_backup_regular_18-30-00.zip
├── medium/
│   └── 2025-05-21/server_backup_medium_09-00-00.zip
└── hard/
    └── 2025-05-20/server_backup_hard_03-00-00.zip
```

**Smart Retention:**
- Automatically cleans up old backups based on type
- Keeps different amounts for each type (12 regular, 7 medium, 4 hard)
- Prevents storage from filling up

## 📊 Monitoring

```bash
mcutil watch          # Auto-restart if server crashes (Ctrl+C to stop)
mcutil status         # Live server stats (CPU, memory, uptime)
```

## 🎮 Common Workflows

**Quick Server Start**
```bash
mcutil start
mcutil schedule-backups  # Start intelligent backup system
```

**Server with Monitoring**
```bash
mcutil start
mcutil watch &           # Background auto-restart
mcutil schedule-backups  # Multi-type backups
```

**Server Maintenance**
```bash
mcutil cmd "say Maintenance in 5 minutes!"
mcutil backup --type medium  # Comprehensive backup before maintenance
mcutil stop
# Do maintenance work
mcutil start
```

**View Background Processes**
```bash
screen -ls                    # List all screen sessions
screen -r minecraft           # Attach to server console
screen -r mcutil-backups      # Attach to backup scheduler
```

## 🔧 Advanced Features

- **Screen Integration**: Server and backups run in detached screen sessions
- **Type-Specific Folders**: Organized backup storage by type and date
- **Smart Cleanup**: Automatic removal of old backups based on retention policies
- **Live Monitoring**: Real-time server stats and backup status
- **Flexible Scheduling**: Customizable intervals for each backup type
- **Error Handling**: Robust error handling and recovery

## 📝 Notes

- Uses `screen` for background operation and session management
- All backup types include automatic cleanup based on retention settings
- Scheduler survives server restarts and system reboots
- Backup integrity is verified after creation
- Missing files are logged but don't stop the backup process

## 🆘 Troubleshooting

**Check if services are running:**
```bash
mcutil status         # Server status
mcutil backup-status  # Backup scheduler status
screen -ls           # List all screen sessions
```

**Manually attach to processes:**
```bash
screen -r minecraft       # Attach to server console
screen -r mcutil-backups  # View backup scheduler logs
```

**Reset everything:**
```bash
mcutil stop
mcutil stop-backups
mcutil setup  # Reconfigure if needed
```