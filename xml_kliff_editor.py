import os
import sys
import string
import re
import shutil
from datetime import datetime
import tempfile
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Add the 'python' directory to sys.path so it can find the modules inside the 'python' folder
sys.path.append(os.path.join(os.path.dirname(__file__), 'python'))

from paz_parse import parse_pamt, PazEntry
from paz_unpack import extract_entry
from paz_repack import repack_entry

TARGET_FILE = "phm_description_player_kliff.xml"

# All PartInOutSocket items grouped by category
SOCKET_CATEGORIES = [
    ("Shield", [
        "CD_MainWeapon_Shield_L",
        "CD_MainWeapon_TowerShield_L",
    ]),
    ("Bow / Arrow", [
        "CD_MainWeapon_Bow",
        "CD_MainWeapon_Quiver",
        "CD_MainWeapon_Arw",
        "CD_MainWeapon_Arw_IN",
    ]),
    ("Misc", [
        "CD_HyperspacePlug",
    ]),
    ("Sword (1H)", [
        "CD_MainWeapon_Sword_R",
        "CD_MainWeapon_Sword_IN_R",
        "CD_MainWeapon_Sword_L",
        "CD_MainWeapon_Sword_IN_L",
        "CD_MainWeapon_Sword_R_Aux",
        "CD_MainWeapon_Sword_IN_R_Aux",
    ]),
    ("Dagger", [
        "CD_MainWeapon_Dagger_R",
        "CD_MainWeapon_Dagger_IN_R",
        "CD_MainWeapon_Dagger_L",
        "CD_MainWeapon_Dagger_IN_L",
    ]),
    ("Axe (1H)", [
        "CD_MainWeapon_Axe_R",
        "CD_MainWeapon_Axe_L",
    ]),
    ("Mace (1H)", [
        "CD_MainWeapon_Mace_R",
        "CD_MainWeapon_Mace_L",
    ]),
    ("Wand", [
        "CD_MainWeapon_Wand_R",
    ]),
    ("Fist / Hand Cannon / Gauntlet", [
        "CD_MainWeapon_Fist_R",
        "CD_MainWeapon_Fist_L",
        "CD_MainWeapon_HandCannon",
        "CD_MainWeapon_Gauntlet",
    ]),
    ("Two-Hand Sword", [
        "CD_TwoHandWeapon_Sword",
    ]),
    ("Two-Hand Axe", [
        "CD_TwoHandWeapon_Axe",
    ]),
    ("Two-Hand Mace / Hammer", [
        "CD_TwoHandWeapon_Mace",
        "CD_TwoHandWeapon_WarHammer",
        "CD_TwoHandWeapon_Hammer",
    ]),
    ("Cannon / Thrower", [
        "CD_TwoHandWeapon_Cannon",
        "CD_TwoHandWeapon_Thrower",
    ]),
    ("Spear / Pike / Halberd", [
        "CD_TwoHandWeapon_Spear",
        "CD_MainWeapon_Pike",
        "CD_TwoHandWeapon_Alebard",
    ]),
    ("Fan / Rod / Scythe", [
        "CD_MainWeapon_Fan",
        "CD_TwoHandWeapon_Rod",
        "CD_TwoHandWeapon_Scythe",
    ]),
    ("Bomb", [
        "CD_MainWeapon_Bomb",
    ]),
    ("Tools", [
        "CD_Tool_Torch",
        "CD_Lantern",
        "CD_Tool_Flute",
        "CD_Tool_Pipe",
        "CD_Tool_FishingRod",
        "CD_Tool_Axe",
        "CD_Tool_Pan",
        "CD_Tool_Hammer",
        "CD_Tool_Shovel",
        "CD_Tool_Pickaxe",
        "CD_Tool_Saw",
        "CD_Tool_Broom",
        "CD_Tool_Hayfork",
        "CD_Tool_FarmScythe",
        "CD_Tool_Rake",
        "CD_Tool_Hoe",
        "CD_Tool_Sprayer",
        "CD_Tool_Shooter",
    ]),
    ("Accessories", [
        "CD_Ring_R",
        "CD_Ring_L",
        "CD_Earring_R",
        "CD_Earring_L",
    ]),
    ("Abyss", [
        "CD_Abyss_Gauntlet_02",
    ]),
]


class KliffEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kliff Weapon Visibility Editor")
        self.geometry("620x820")
        self.resizable(True, True)

        self.base_dir = r"C:\Program Files (x86)\Steam\steamapps\common\Crimson Desert"
        self.pamt_path = os.path.join(self.base_dir, "0009", "0.pamt")
        self.kliff_entry = None
        self._current_content = None

        self.temp_dir = tempfile.mkdtemp(prefix="kliff_edit_")

        # Checkbox variables: {part_name: BooleanVar}
        self.check_vars = {}

        self._build_ui()
        self.after(100, self._auto_load_pamt)

    def _build_ui(self):
        # --- Top info ---
        top_frame = tk.Frame(self, padx=10, pady=5)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="Crimson Desert Game Directory:", anchor="w", font=("Arial", 9, "bold")).pack(fill=tk.X)

        path_row = tk.Frame(top_frame)
        path_row.pack(fill=tk.X, pady=(2, 5))

        self.lbl_path = tk.Label(path_row, text=self.pamt_path, fg="#555", font=("Arial", 8),
                                 wraplength=500, justify=tk.LEFT, anchor="w")
        self.lbl_path.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_browse = tk.Button(path_row, text="Browse...", command=self._browse_base_dir)
        btn_browse.pack(side=tk.RIGHT, padx=5)

        status_row = tk.Frame(top_frame)
        status_row.pack(fill=tk.X)
        tk.Label(status_row, text="Status:", font=("Arial", 8, "bold")).pack(side=tk.LEFT)
        self.lbl_status = tk.Label(status_row, text="Initializing...", fg="blue", font=("Arial", 8))
        self.lbl_status.pack(side=tk.LEFT, padx=5)

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=10)

        # --- Button bar ---
        btn_frame = tk.Frame(self, padx=10, pady=5)
        btn_frame.pack(fill=tk.X)

        self.btn_restore = tk.Button(btn_frame, text="Restore Backup", command=self._restore_backup, state=tk.DISABLED)
        self.btn_restore.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_apply = tk.Button(btn_frame, text="Apply Changes", command=self._apply,
                                   state=tk.DISABLED, font=("Arial", 10, "bold"))
        self.btn_apply.pack(side=tk.RIGHT)

        # --- Scrollable checkbox area ---
        container = tk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind("<Configure>",
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # Build checkboxes per category
        for cat_name, parts in SOCKET_CATEGORIES:
            lbl = tk.Label(self.scroll_frame, text=cat_name, font=("Arial", 10, "bold"), anchor="w")
            lbl.pack(fill=tk.X, padx=5, pady=(8, 2))

            for part in parts:
                var = tk.BooleanVar(value=False)
                self.check_vars[part] = var
                display = part.replace("CD_", "").replace("_", " ")
                
                row = tk.Frame(self.scroll_frame)
                row.pack(fill=tk.X, padx=20)
                
                status_var = tk.StringVar(value="Visible")
                lbl_status = tk.Label(row, textvariable=status_var, fg="#228b22", font=("Arial", 9, "bold"), width=7, anchor="w")
                lbl_status.pack(side=tk.LEFT)
                
                def update_status(*args, v=var, s=status_var, l=lbl_status):
                    if v.get():
                        s.set("Hidden")
                        l.config(fg="#b22222")
                    else:
                        s.set("Visible")
                        l.config(fg="#228b22")
                        
                var.trace_add("write", update_status)
                
                cb = tk.Checkbutton(row, text=display, variable=var, anchor="w")
                cb.pack(side=tk.LEFT, fill=tk.X)

        # --- Bottom help ---
        help_text = "Check items to enable Visible=\"Out\" (which hides them).\nUncheck to remove it (which shows them).\nClick Apply Changes to write edits into the PAZ archive."
        tk.Label(self, text=help_text, justify=tk.LEFT, fg="#555555", padx=10).pack(side=tk.BOTTOM, anchor="w", pady=(0, 5))

    # ------------------------------------------------------------------
    def _restore_backup(self):
        if not self.kliff_entry:
            return
            
        paz_file = self.kliff_entry.paz_file
        backup_path = paz_file + ".bak"
        
        if not os.path.exists(backup_path):
            messagebox.showinfo("Restore", "No backup found. Original archive is unchanged.")
            return
            
        if messagebox.askyesno("Confirm Restore", "This will restore the PAZ archive to its original, unmodded state.\nAll your changes will be lost.\n\nContinue?"):
            try:
                shutil.copy2(backup_path, paz_file)
                self._read_current_states()
                messagebox.showinfo("Success", "Archive restored from backup successfully!")
            except Exception as e:
                traceback.print_exc()
                messagebox.showerror("Error", f"Failed to restore backup:\n{e}")

    def _browse_base_dir(self):
        new_dir = filedialog.askdirectory(initialdir=self.base_dir, title="Select Crimson Desert Directory")
        if new_dir:
            self.base_dir = new_dir
            self.pamt_path = os.path.join(self.base_dir, "0009", "0.pamt")
            self.lbl_path.config(text=self.pamt_path)
            self._auto_load_pamt()

    # ------------------------------------------------------------------
    def _auto_load_pamt(self):
        # 1. First check if current/default path exists
        if not os.path.exists(self.pamt_path):
            # 2. Try to find it automatically across all drives
            self.lbl_status.config(text="Searching game...", fg="blue")
            self.update()
            
            found_dir = self._find_game_dir_automatically()
            if found_dir:
                self.base_dir = found_dir
                self.pamt_path = os.path.join(self.base_dir, "0009", "0.pamt")
                self.lbl_path.config(text=self.pamt_path)
            else:
                # 3. Fallback: Ask the user to point to the directory
                # We don't use error anymore, just an info message followed by browse
                messagebox.showinfo("Game Not Found", 
                                     "Crimson Desert was not found in the default location.\n\n"
                                     "Please select the game installation folder (containing '0009').")
                self._browse_base_dir()
                return

        # Double check after potential browse/discovery
        if not os.path.exists(self.pamt_path):
            self.lbl_status.config(text="File not found", fg="red")
            return

        try:
            self.lbl_status.config(text="Parsing...", fg="blue")
            self.update()

            paz_dir = os.path.dirname(self.pamt_path)
            entries = parse_pamt(self.pamt_path, paz_dir=paz_dir)

            self.kliff_entry = next((e for e in entries if TARGET_FILE in e.path.lower()), None)

            if not self.kliff_entry:
                messagebox.showerror("Error", f"Could not find {TARGET_FILE} in the archive.")
                self.lbl_status.config(text="File not found", fg="red")
                return

            self.lbl_status.config(text="Loaded successfully", fg="green")
            self._read_current_states()

            # Check for backup
            backup_path = self.kliff_entry.paz_file + ".bak"
            if os.path.exists(backup_path):
                self.btn_restore.config(state=tk.NORMAL)
            else:
                self.btn_restore.config(state=tk.DISABLED)

            self.btn_apply.config(state=tk.NORMAL)

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load PAMT:\n{e}")
            self.lbl_status.config(text="Error loading", fg="red")

    def _read_current_states(self):
        """Extract the file and set checkbox states from current XML content."""
        try:
            res = extract_entry(self.kliff_entry, self.temp_dir)
            with open(res["path"], 'rb') as f:
                self._current_content = f.read()

            for part_name, var in self.check_vars.items():
                marker = b'PartName="' + part_name.encode('utf-8') + b'"'
                has_visible = False
                for line in self._current_content.split(b'\n'):
                    if marker in line:
                        has_visible = b'Visible="Out"' in line
                        break
                var.set(has_visible)

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to read file states:\n{e}")

    @staticmethod
    def _find_game_dir_automatically():
        """Look for Crimson Desert in various common Steam/standalone paths across all drives."""
        common_subs = [
            r"Program Files (x86)\Steam\steamapps\common\Crimson Desert",
            r"Program Files\Steam\steamapps\common\Crimson Desert",
            r"SteamLibrary\steamapps\common\Crimson Desert",
            r"Steam\steamapps\common\Crimson Desert",
            r"Games\Crimson Desert",
            r"Crimson Desert",
        ]
        
        # Check all possible drives A-Z currently present in the system
        # Use string.ascii_uppercase to get A-Z
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        
        for drive in drives:
            for sub in common_subs:
                candidate = os.path.join(drive, sub)
                target = os.path.join(candidate, "0009", "0.pamt")
                if os.path.exists(target):
                    return candidate
        return None

    # ------------------------------------------------------------------
    def _apply(self):
        if not self.kliff_entry:
            return

        try:
            # Re-extract fresh content
            res = extract_entry(self.kliff_entry, self.temp_dir)
            extracted_path = res["path"]
            with open(extracted_path, 'rb') as f:
                content = f.read()

            # Build desired states from checkboxes
            changes = {name: var.get() for name, var in self.check_vars.items()}
            content = self._apply_visible_changes(content, changes)

            with open(extracted_path, 'wb') as f:
                f.write(content)

            # Backup before repacking (keep only the first pristine backup)
            paz_file = self.kliff_entry.paz_file
            backup_path = paz_file + ".bak"
            if not os.path.exists(backup_path):
                shutil.copy2(paz_file, backup_path)
                self.btn_restore.config(state=tk.NORMAL)

            repack_entry(extracted_path, self.kliff_entry, output_path=None)

            messagebox.showinfo("Success", "Changes applied and repacked!")

            self._read_current_states()

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to apply changes:\n{e}")

    @staticmethod
    def _apply_visible_changes(content, changes):
        """Add or remove Visible='Out' for each PartName in *changes*."""
        sep = b'\r\n' if b'\r\n' in content else b'\n'
        lines = content.split(sep)

        for part_name, should_be_visible in changes.items():
            marker = b'PartName="' + part_name.encode('utf-8') + b'"'

            for i, line in enumerate(lines):
                if marker not in line:
                    continue

                has_visible = b'Visible="Out"' in line

                if should_be_visible and not has_visible:
                    # Insert Visible="Out" before the closing />
                    idx = line.rfind(b'/>')
                    if idx >= 0:
                        before = line[:idx].rstrip()
                        after = line[idx + 2:]
                        lines[i] = before + b' Visible="Out"/>' + after

                elif not should_be_visible and has_visible:
                    # Remove Visible="Out" and any preceding whitespace
                    lines[i] = re.sub(rb'[\t ]+Visible="Out"', b'', line)

                break

        return sep.join(lines)


if __name__ == "__main__":
    app = KliffEditor()
    app.mainloop()
