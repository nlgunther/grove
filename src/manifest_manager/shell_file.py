"""
shell_file.py — File management commands for ManifestShell.

Commands: load, save, backup, restore, merge.
"""

import shlex
import os
import shutil

from .shell_base import SafeParser, ParserControl, Config
from .shell_base import generate_bkp_name, generate_timestamped_name, backup_sidecar


class FileCommands:
    """Mixin providing file-management do_* methods."""

    def do_load(self, arg):
        """Load manifest: load <file> [--auto-sidecar] [--rebuild-sidecar]
        
        Examples:
            load myfile.xml
            load myfile.xml --autosc          # Create sidecar if missing
            load myfile.xml --rebuildsc       # Force rebuild sidecar
        """
        p = SafeParser(prog="load")
        p.add_argument("filename")
        p.add_argument("--auto-sidecar", "--autosc", action="store_true",
                       help="Auto-create sidecar if missing")
        p.add_argument("--rebuild-sidecar", "--rebuildsc", action="store_true",
                       help="Force rebuild sidecar")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            
            # Resolve named file aliases from config/integration.yaml
            # e.g. named_files: {basic: "G:/My Drive/manifests/todo2026.xml"}
            filename = args.filename
            from shared.integration_config import load_integration_config
            named = load_integration_config().get("named_files", {})
            if filename in named:
                resolved = named[filename]
                print(f"Loading '{filename}' → {resolved}")
                filename = resolved

            def on_success(result):
                self.prompt = f"({os.path.basename(self.repo.filepath)}) "
            
            # Call load with sidecar flags
            def load_with_flags(filepath, password):
                return self.repo.load(
                    filepath,
                    password,
                    auto_sidecar=args.auto_sidecar,
                    rebuild_sidecar=args.rebuild_sidecar
                )
            
            self._with_password_retry(load_with_flags, filename, on_success)
        
        self._exec(_run)

    def do_save(self, arg):
        """Save file: save [filename]"""
        pwd = self.repo.password
        if arg and arg.endswith(".7z") and not pwd:
             pwd = self._get_pass(f"Set password for {arg}: ")
        print(self.repo.save(arg, pwd).message)

    def do_backup(self, arg):
        """Create a backup of the current manifest.
        
        Usage:
            backup [filename] [options]
        
        Arguments:
            filename            Optional custom backup filename
        
        Options:
            --force, -f        Overwrite existing backup without prompting
            --timestamp, -t    Use timestamp instead of .bkp
            --no-sidecar       Skip sidecar backup
        
        Examples:
            backup                          # Create filename.bkp.xml
            backup mybackup.xml             # Custom name
            backup --timestamp              # filename.20260127_143022.xml
            backup --force                  # Overwrite without asking
            backup --timestamp --no-sidecar # Timestamped, no sidecar
        """
        p = SafeParser(prog="backup", description="Create manifest backup")
        p.add_argument("filename", nargs="?", help="Custom backup filename")
        p.add_argument("--force", "-f", action="store_true",
                       help="Overwrite without prompting")
        p.add_argument("--timestamp", "-t", action="store_true",
                       help="Use timestamp instead of .bkp")
        p.add_argument("--no-sidecar", action="store_true",
                       help="Skip sidecar backup")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            
            # 1. Validate preconditions
            if not self.repo.tree:
                print("Error: No file loaded. Use 'load <file>' first.")
                return
            
            if not self.repo.filepath:
                print("Error: No file path set.")
                return
            
            # 2. Generate backup filename
            if args.filename:
                backup_path = args.filename
                # Add .xml if no extension provided
                if "." not in os.path.basename(backup_path):
                    backup_path += ".xml"
            elif args.timestamp:
                backup_path = generate_timestamped_name(self.repo.filepath)
            else:
                backup_path = generate_bkp_name(self.repo.filepath)
            
            # 3. Check for overwrite
            if os.path.exists(backup_path) and not args.force:
                try:
                    response = input(f"File exists: {backup_path}\nOverwrite? [y/N]: ")
                    if response.strip().lower() not in ('y', 'yes'):
                        print("Cancelled.")
                        return
                except KeyboardInterrupt:
                    print("\nCancelled.")
                    return
            
            # 4. Show warning if unsaved changes
            if self.repo.modified:
                print("⚠ Warning: Backup includes unsaved changes")
            
            # 5. Save backup (current in-memory state)
            # Note: save() will change self.repo.filepath to backup_path
            original_filepath = self.repo.filepath
            original_password = self.repo.password

            try:
                result = self.repo.save(backup_path, self.repo.password)
                if not result.success:
                    print(f"Error: {result.message}")
                    return

                # Show success message
                if args.force and os.path.exists(backup_path):
                    print(f"✓ Backup saved to {backup_path} (overwritten)")
                else:
                    print(f"✓ Backup saved to {backup_path}")

                # 6. Backup sidecar if exists and not disabled
                if self.repo.id_sidecar and not args.no_sidecar:
                    if backup_sidecar(original_filepath, backup_path):
                        print(f"✓ Sidecar backed up to {backup_path}.ids")

                # 7. Backup global config if it exists
                global_config_path = Config._get_global_path()
                if os.path.exists(global_config_path):
                    config_backup_path = backup_path + ".config.yaml"
                    try:
                        shutil.copy2(global_config_path, config_backup_path)
                        print(f"✓ Config backed up to {config_backup_path}")
                    except Exception as e:
                        print(f"⚠ Warning: Could not back up config: {e}")
                else:
                    print(f"⚠ Warning: Global config not found at {global_config_path} — skipping")
            finally:
                # 7. Restore original filepath (save() changes it)
                # This ALWAYS runs, even if save() fails or we return early
                self.repo.filepath = original_filepath
                self.repo.password = original_password
            
            # Update prompt if needed
            if self.prompt.startswith("("):
                self.prompt = f"({os.path.basename(original_filepath)}) "
        
        self._exec(_run)


    def do_merge(self, arg):
        """Merge external file: merge <filename>"""
        if not arg: return print("Usage: merge <filename>")
        self._with_password_retry(self.repo.merge_from, arg)


    def do_restore(self, arg):
        """Restore manifest from a backup file: restore <backup_file>

        Loads the backup file into memory and marks the session as modified.
        Use 'save' (with your original filename) to persist the restoration.

        Examples:
            restore project.bkp.xml
            restore project.20260127_143022.xml
        """
        p = SafeParser(prog="restore", description="Restore from backup")
        p.add_argument("filename", help="Backup file to restore from")

        def _run():
            args = p.parse_args(shlex.split(arg))

            original_filepath = self.repo.filepath

            def do_load(filepath, password):
                return self.repo.load(filepath, password)

            result = self._with_password_retry(do_load, args.filename)
            if result and result.success:
                self.prompt = f"({os.path.basename(self.repo.filepath)}) "
                print(f"✓ Restored from {args.filename}")
                if original_filepath:
                    print(f"Tip: Use 'save {original_filepath}' to write back to original file.")

        self._exec(_run)

