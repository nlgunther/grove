"""
cli_maintenance.py — Maintenance commands for the Smart Scheduler CLI.

Commands: config, backup, restore, maintenance.

These commands touch the filesystem directly (shutil, os) and interact with
the manifest_manager config for backup purposes; those heavy imports are
deferred inside each function.
"""

from pathlib import Path


def cmd_config(cli, args):
    """Show or modify configuration.
    
    Usage:
        config                    Show current configuration
        config location <path>    Move data to new location
        config reset              Reset to default configuration
    """
    if not args:
        print(f"\n{'='*60}")
        print("CONFIGURATION")
        print(f"{'='*60}")
        print(f"Data Directory: {cli.cfg.data_dir}")
        print(f"Config File:    {cli.cfg.config_path}")
        print(f"\nPreferences:")
        for key, value in cli.cfg.preferences.items():
            print(f"  {key}: {value}")
        print(f"{'='*60}\n")
        return

    action = args[0].lower()
    
    if action == "reset":
        print("\n⚠️  WARNING: This will reset configuration to defaults.")
        print(f"Current data directory: {cli.cfg.data_dir}")
        print(f"Default data directory: ~/.scheduler/")
        print("\nThis will:")
        print("  • Reset data_dir to default (~/.scheduler/)")
        print("  • Reset all preferences to defaults")
        print("  • NOT move or delete any data files")
        print("\nYour data will remain at the current location.")
        print("You'll need to manually move it if desired.")
        
        response = input("\nReset configuration? (yes/no): ")
        if response.lower() != 'yes':
            return print("Reset cancelled.")
        
        # Delete the config file to force defaults
        if cli.cfg.config_path.exists():
            cli.cfg.config_path.unlink()
            print(f"\n✓ Deleted config file: {cli.cfg.config_path}")
        
        # Reload with defaults
        cli.cfg.load()
        
        print("✓ Configuration reset to defaults")
        print(f"  Data Directory: {cli.cfg.data_dir}")
        print(f"  Storage Engine: {cli.cfg.preferences.get('storage_engine', 'json')}")
        print("\nRestart the scheduler for changes to take full effect.")
        return
    
    if action == "location" and len(args) > 1:
        import shutil
        
        new_path = Path(args[1]).resolve()
        old_path = cli.cfg.data_dir
        
        if new_path == old_path:
            return print("New path is the same as current path.")
            
        print(f"\nMoving data...")
        print(f"  Source: {old_path}")
        print(f"  Dest:   {new_path}")
        
        new_path.mkdir(parents=True, exist_ok=True)
        items_to_move = ["scheduler.db", "projects", "exports"]
        moved_count = 0
        
        for item in items_to_move:
            src = old_path / item
            dst = new_path / item
            
            if src.exists():
                if dst.exists():
                    print(f"  Warning: '{item}' already exists in destination. Skipping.")
                else:
                    shutil.move(str(src), str(dst))
                    print(f"  Moved: {item}")
                    moved_count += 1
        
        cli.cfg.set_data_dir(str(new_path))
        print(f"\n✓ Moved {moved_count} items. Config updated.")

def cmd_backup(cli, args):
    """Create a backup of all data (read-only by default)."""
    import os
    import stat
    import shutil
    from manifest_manager.config import Config as ManifestConfig

    pos, opts = cli._opts(args)
    name = opts.get("name") or opts.get("bkup_name")
    compress = "compress" in opts
    allow_write = "writable" in opts  # Optional flag to keep writable
    
    path = cli.maint_service.backup(name, compress)

    # Copy global manifest config alongside the backup.
    # Restore ignores this file intentionally — it requires human review to install.
    global_config_path = Path(ManifestConfig._get_global_path())
    if global_config_path.exists():
        try:
            if path.is_dir():
                # Directory backup: place config inside it
                dest = path / "config.yaml"
            else:
                # Compressed backup: place config alongside as <backup>.config.yaml
                dest = path.parent / (path.name + ".config.yaml")
            shutil.copy2(global_config_path, dest)
            print(f"✓ Config backed up to {dest}")
        except Exception as e:
            print(f"⚠ Warning: Could not back up config: {e}")
    else:
        print(f"⚠ Warning: Global config not found at {global_config_path} — skipping")

    if not allow_write:
        # Make backup read-only
        if path.is_file():
            # Single file (compressed backup)
            current_mode = path.stat().st_mode
            # Remove write permissions for user, group, and others
            read_only_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            path.chmod(read_only_mode)
            print(f"✓ Backup created at: {path} (read-only)")
        elif path.is_dir():
            # Directory backup - make all files read-only
            for root, dirs, files in os.walk(path):
                # Make directory readable and executable but not writable
                for d in dirs:
                    dir_path = Path(root) / d
                    current_mode = dir_path.stat().st_mode
                    read_only_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
                    dir_path.chmod(read_only_mode)
                
                # Make files read-only
                for f in files:
                    file_path = Path(root) / f
                    current_mode = file_path.stat().st_mode
                    read_only_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
                    file_path.chmod(read_only_mode)
            
            print(f"✓ Backup created at: {path} (read-only)")
    else:
        print(f"✓ Backup created at: {path} (writable)")


def cmd_restore(cli, args):
    """Restore data from a backup."""
    if not args:
        return print("Usage: restore <path>")
    
    print("\n⚠️  WARNING: Restore will replace ALL current data")
    print("Current data will be backed up to a temporary location.")
    print("\nIMPORTANT: After restore completes, you MUST restart the scheduler!")
    print("DO NOT use any commands after restore - just quit and restart.\n")
    
    response = input("Continue with restore? (yes/no): ")
    if response.lower() != 'yes':
        return print("Restore cancelled.")
    
    try:
        cli.maint_service.restore(args[0])
        print("✓ Restore successful.")
        print("\n" + "="*60)
        print("CRITICAL: You MUST restart the scheduler NOW!")
        print("="*60)
        print("\nSteps:")
        print("  1. Type 'quit' to exit")
        print("  2. Restart the scheduler")
        print("  3. Verify your data with 'list'")
        print("\n⚠️  DO NOT run any other commands before restarting!")
        print("⚠️  Running commands now will overwrite the restored data!")
        print("="*60)
        
        # Mark CLI as needing restart
        cli._needs_restart = True
        
    except Exception as e:
        print(f"✗ Restore failed: {e}")

def cmd_maintenance(cli, args):
    """Perform database maintenance."""
    pos, opts = cli._opts(args)
    if "vacuum" in opts or "optimize" in opts:
        cli.maint_service.optimize_database()
        print("✓ Database optimized.")

