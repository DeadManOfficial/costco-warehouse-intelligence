#!/usr/bin/env python3
"""
Costco Markdown Hunter - Main App
==================================
Single window app. Settings dialog for config.
"""

import customtkinter as ctk
import json
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Optional

# Config path
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """Load config from file."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_config(config: dict):
    """Save config to file."""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog for API key, warehouses, save dir."""

    STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

    CATEGORIES = ["All", "Electronics", "Home", "Kitchen", "Outdoor", "Auto", "Toys", "Clothing", "Health", "Cleaning", "Office", "Pet", "Plants"]

    def __init__(self, parent, config: dict, on_save):
        super().__init__(parent)

        self.config = config.copy()
        self.on_save = on_save
        self.warehouse_db = self._load_warehouse_db()
        self.selected_warehouses = set(config.get("warehouses", []))
        self.selected_category = config.get("category", "All")

        self.title("Settings")
        self.geometry("550x620")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 275
        y = (self.winfo_screenheight() // 2) - 275
        self.geometry(f"+{x}+{y}")

    def _load_warehouse_db(self) -> dict:
        """Load warehouse database."""
        import sys
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).parent
        db_path = base / "costco_warehouses_master.json"

        if db_path.exists():
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('warehouses', data)
            except:
                pass
        return {}

    def _setup_ui(self):
        # API Key
        ctk.CTkLabel(self, text="Groq API Key", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(15, 3))

        link_label = ctk.CTkLabel(self, text="Get FREE API key at console.groq.com", font=ctk.CTkFont(size=11, underline=True), text_color="#58a6ff", cursor="hand2")
        link_label.pack(anchor="w", padx=20)
        link_label.bind("<Button-1>", lambda e: __import__('webbrowser').open("https://console.groq.com"))

        self.api_entry = ctk.CTkEntry(self, width=450, placeholder_text="gsk_...")
        self.api_entry.pack(padx=20, pady=(5, 10))
        if self.config.get("groq_api_key"):
            self.api_entry.insert(0, self.config["groq_api_key"])

        # Warehouse Selection
        ctk.CTkLabel(self, text="Warehouses", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(10, 3))

        # State dropdown
        state_frame = ctk.CTkFrame(self, fg_color="transparent")
        state_frame.pack(fill="x", padx=20, pady=(0, 5))

        ctk.CTkLabel(state_frame, text="State:").pack(side="left")
        self.state_var = ctk.StringVar(value="Select State")
        self.state_dropdown = ctk.CTkComboBox(state_frame, values=["Select State"] + self.STATES, variable=self.state_var, width=120, command=self._on_state_change)
        self.state_dropdown.pack(side="left", padx=10)

        self.selected_label = ctk.CTkLabel(state_frame, text=f"{len(self.selected_warehouses)} selected", text_color="lightgreen" if self.selected_warehouses else "gray")
        self.selected_label.pack(side="right")

        # Category dropdown
        ctk.CTkLabel(self, text="Product Category", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(10, 3))

        cat_frame = ctk.CTkFrame(self, fg_color="transparent")
        cat_frame.pack(fill="x", padx=20, pady=(0, 5))

        ctk.CTkLabel(cat_frame, text="Category:").pack(side="left")
        self.category_var = ctk.StringVar(value=self.selected_category)
        self.category_dropdown = ctk.CTkComboBox(cat_frame, values=self.CATEGORIES, variable=self.category_var, width=150)
        self.category_dropdown.pack(side="left", padx=10)

        ctk.CTkLabel(cat_frame, text="(filters results by type)", text_color="gray").pack(side="left")

        # Warehouse list (scrollable checkboxes)
        list_frame = ctk.CTkFrame(self, fg_color="gray20")
        list_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.wh_scroll = ctk.CTkScrollableFrame(list_frame, height=150)
        self.wh_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.wh_checkboxes = {}
        self._show_message("Select a state to see warehouses")

        # Save Directory
        ctk.CTkLabel(self, text="Save Results To", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(10, 3))

        dir_frame = ctk.CTkFrame(self, fg_color="transparent")
        dir_frame.pack(fill="x", padx=20, pady=(0, 10))

        default_dir = self.config.get("save_directory", str(Path.home() / "Documents" / "CostcoHunter"))
        self.dir_var = ctk.StringVar(value=default_dir)

        self.dir_entry = ctk.CTkEntry(dir_frame, textvariable=self.dir_var, width=380)
        self.dir_entry.pack(side="left")

        ctk.CTkButton(dir_frame, text="Browse", width=60, command=self._browse).pack(side="left", padx=10)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="gray30", command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="Save", width=100, command=self._save).pack(side="right")

    def _show_message(self, msg: str):
        """Show message in warehouse list area."""
        for w in self.wh_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.wh_scroll, text=msg, text_color="gray").pack(pady=20)

    def _on_state_change(self, state: str):
        """Load warehouses for selected state."""
        if state == "Select State":
            return

        # Clear list
        for w in self.wh_scroll.winfo_children():
            w.destroy()
        self.wh_checkboxes = {}

        # Find warehouses in this state
        warehouses = []
        for wh_id, wh_data in self.warehouse_db.items():
            if wh_data.get("state") == state:
                warehouses.append((wh_id, wh_data))

        if not warehouses:
            self._show_message(f"No warehouses found in {state}")
            return

        # Create checkboxes
        for wh_id, wh_data in sorted(warehouses, key=lambda x: x[1].get("city", "")):
            var = ctk.BooleanVar(value=wh_id in self.selected_warehouses)
            city = wh_data.get("city", "Unknown")

            cb = ctk.CTkCheckBox(self.wh_scroll, text=f"#{wh_id} - {city}, {state}", variable=var, command=lambda wid=wh_id, v=var: self._on_checkbox(wid, v))
            cb.pack(anchor="w", pady=2)
            self.wh_checkboxes[wh_id] = var

    def _on_checkbox(self, wh_id: str, var: ctk.BooleanVar):
        """Handle warehouse checkbox change."""
        if var.get():
            self.selected_warehouses.add(wh_id)
        else:
            self.selected_warehouses.discard(wh_id)
        self.selected_label.configure(text=f"{len(self.selected_warehouses)} selected", text_color="lightgreen" if self.selected_warehouses else "gray")

    def _browse(self):
        dir_path = filedialog.askdirectory(initialdir=self.dir_var.get())
        if dir_path:
            self.dir_var.set(dir_path)

    def _save(self):
        api_key = self.api_entry.get().strip()
        save_dir = self.dir_var.get().strip()

        if not api_key:
            self.selected_label.configure(text="API key required!", text_color="red")
            return

        if not self.selected_warehouses:
            self.selected_label.configure(text="Select at least one warehouse!", text_color="red")
            return

        # Update config
        self.config["groq_api_key"] = api_key
        self.config["warehouses"] = list(self.selected_warehouses)
        self.config["save_directory"] = save_dir
        self.config["category"] = self.category_var.get()
        self.config["ai_enabled"] = True
        self.config["setup_complete"] = True

        # Save and close
        save_config(self.config)
        self.on_save(self.config)
        self.destroy()


class MainApp(ctk.CTk):
    """Main application window."""

    # Dark hacker theme colors
    BG_COLOR = "#000000"           # Pure black
    FRAME_COLOR = "#0a0a0a"        # Near black
    ACCENT_COLOR = "#1a1a1a"       # Dark gray
    TEXT_COLOR = "#ffffff"         # White
    TEXT_DIM = "#888888"           # Dim gray
    HIGHLIGHT = "#00ff00"          # Matrix green for highlights

    def __init__(self):
        super().__init__()

        self.config = load_config()
        self.scanning = False

        # Window
        self.title("DEADMAN // Costco Markdown Hunter")
        self.geometry("750x600")
        self.resizable(False, False)
        self.configure(fg_color=self.BG_COLOR)

        ctk.set_appearance_mode("dark")

        self._setup_ui()
        self._center()

        # If no API key, open settings
        if not self.config.get("groq_api_key"):
            self.after(100, self._open_settings)

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 350
        y = (self.winfo_screenheight() // 2) - 275
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        # Header with hacker branding
        header = ctk.CTkFrame(self, fg_color=self.BG_COLOR)
        header.pack(fill="x", padx=30, pady=(25, 10))

        title_frame = ctk.CTkFrame(header, fg_color=self.BG_COLOR)
        title_frame.pack(side="left")

        ctk.CTkLabel(title_frame, text="DEADMAN", font=ctk.CTkFont(size=28, weight="bold"),
                    text_color=self.HIGHLIGHT).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Costco Markdown Hunter v1.0", font=ctk.CTkFont(size=12),
                    text_color=self.TEXT_DIM).pack(anchor="w")

        ctk.CTkButton(header, text="SETTINGS", width=90, height=32,
                     fg_color=self.ACCENT_COLOR, hover_color="#2a2a2a",
                     border_width=1, border_color="#333333",
                     command=self._open_settings).pack(side="right")

        # Separator line
        ctk.CTkFrame(self, height=1, fg_color="#333333").pack(fill="x", padx=30, pady=10)

        # Controls
        ctrl = ctk.CTkFrame(self, fg_color=self.BG_COLOR)
        ctrl.pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(ctrl, text="TARGET:", font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=self.TEXT_DIM).pack(side="left")

        warehouses = self.config.get("warehouses", ["Not configured"])
        self.wh_var = ctk.StringVar(value=warehouses[0] if warehouses else "")
        self.wh_dropdown = ctk.CTkComboBox(ctrl, values=warehouses, variable=self.wh_var, width=130,
                                           fg_color=self.ACCENT_COLOR, border_color="#333333",
                                           button_color="#333333", button_hover_color="#444444",
                                           dropdown_fg_color=self.ACCENT_COLOR)
        self.wh_dropdown.pack(side="left", padx=5)

        # Category dropdown (uses shared CATEGORIES constant)
        ctk.CTkLabel(ctrl, text="CATEGORY:", font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=self.TEXT_DIM).pack(side="left", padx=(10, 0))

        self.cat_var = ctk.StringVar(value=self.config.get("category", "All"))
        self.cat_dropdown = ctk.CTkComboBox(ctrl, values=SettingsDialog.CATEGORIES, variable=self.cat_var, width=110,
                                            fg_color=self.ACCENT_COLOR, border_color="#333333",
                                            button_color="#333333", button_hover_color="#444444",
                                            dropdown_fg_color=self.ACCENT_COLOR)
        self.cat_dropdown.pack(side="left", padx=5)

        self.scan_btn = ctk.CTkButton(ctrl, text="LOAD DEALS", width=140, height=38,
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      fg_color=self.HIGHLIGHT, hover_color="#00cc00",
                                      text_color="#000000", command=self._run_scan)
        self.scan_btn.pack(side="left", padx=20)

        self.status = ctk.CTkLabel(ctrl, text="[ READY ]", text_color=self.HIGHLIGHT,
                                   font=ctk.CTkFont(family="Consolas", size=12))
        self.status.pack(side="left", padx=10)

        # Results panel
        results_frame = ctk.CTkFrame(self, fg_color=self.FRAME_COLOR, border_width=1, border_color="#333333")
        results_frame.pack(fill="both", expand=True, padx=30, pady=(10, 25))

        results_header = ctk.CTkFrame(results_frame, fg_color=self.ACCENT_COLOR)
        results_header.pack(fill="x")
        ctk.CTkLabel(results_header, text="// OUTPUT", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                    text_color=self.HIGHLIGHT).pack(anchor="w", padx=15, pady=8)

        self.results = ctk.CTkTextbox(results_frame, font=ctk.CTkFont(family="Consolas", size=11),
                                      fg_color=self.FRAME_COLOR, text_color=self.TEXT_COLOR,
                                      border_width=0)
        self.results.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.results.insert("1.0", "[ SYSTEM READY ]\n\nSelect warehouse target and execute scan.\n\n"
                           "PRICE CODE INTEL:\n"
                           "  .97 = Corporate clearance (HIGH VALUE)\n"
                           "  .00 = Manager special (NEGOTIABLE)\n"
                           "  .88 = Manager markdown\n"
                           "  *   = Death star (NO RESTOCK)")
        self.results.configure(state="disabled")

    def _open_settings(self):
        SettingsDialog(self, self.config, self._on_settings_saved)

    def _on_settings_saved(self, new_config: dict):
        self.config = new_config
        # Update warehouse dropdown
        warehouses = self.config.get("warehouses", [])
        self.wh_dropdown.configure(values=warehouses)
        if warehouses:
            self.wh_var.set(warehouses[0])
        # Update category dropdown
        category = self.config.get("category", "All")
        self.cat_var.set(category)
        self.status.configure(text="[ CONFIG SAVED ]", text_color=self.HIGHLIGHT)

    def _run_scan(self):
        if self.scanning:
            return

        warehouse = self.wh_var.get()
        if not warehouse or warehouse == "Not configured":
            self.status.configure(text="[ ERROR: NO TARGET ]", text_color="#ff0000")
            return

        if not self.config.get("groq_api_key"):
            self.status.configure(text="[ ERROR: NO API KEY ]", text_color="#ff0000")
            return

        # Validate category selection
        category = self.cat_var.get()
        if category not in SettingsDialog.CATEGORIES:
            category = "All"
            self.cat_var.set("All")

        self.scanning = True
        self.scan_btn.configure(state="disabled", text="SCANNING...")
        self.status.configure(text=f"[ SCANNING #{warehouse} | {category} ]", text_color="#ffff00")

        self.results.configure(state="normal")
        self.results.delete("1.0", "end")
        self.results.insert("1.0", f"Scanning warehouse #{warehouse} for {category}...\n")
        self.results.configure(state="disabled")

        selected_category = category  # Capture for thread

        def scan():
            try:
                from datetime import datetime
                import sys

                if getattr(sys, 'frozen', False):
                    base = Path(sys.executable).parent
                else:
                    base = Path(__file__).parent

                # Get warehouse info
                wh_db_path = base / "costco_warehouses_master.json"
                warehouse_state = "Unknown"
                warehouse_city = "Unknown"

                if wh_db_path.exists():
                    with open(wh_db_path, 'r', encoding='utf-8') as f:
                        wh_data = json.load(f)
                        wh_info = wh_data.get('warehouses', {}).get(warehouse, {})
                        warehouse_state = wh_info.get('state', 'Unknown')
                        warehouse_city = wh_info.get('city', 'Unknown')

                # Import and use the PRODUCTION scraper
                self.after(0, lambda: self.status.configure(text=f"[ SCRAPING WAREHOUSE RUNNER ]", text_color="#ffff00"))

                live_markdowns = []
                scrape_count = 0

                try:
                    # Add current dir to path for import
                    if str(base) not in sys.path:
                        sys.path.insert(0, str(base))

                    from warehouse_runner_PRODUCTION import extract_fast, scraper

                    # Load item IDs
                    items_file = base / "warehouse_runner_all_items.txt"
                    if items_file.exists():
                        with open(items_file) as f:
                            all_items = [line.strip() for line in f if line.strip()]

                        # Scrape a batch of items (50 for quick scan)
                        import random
                        sample_items = random.sample(all_items, min(50, len(all_items)))

                        for item_id in sample_items:
                            try:
                                result_data = extract_fast(item_id)
                                scrape_count += 1

                                if result_data and result_data.get('is_markdown'):
                                    # Check if this item has deals in the selected state
                                    states = result_data.get('states', [])
                                    in_state = any(s.get('state') == warehouse_state for s in states)

                                    # Categorize the product
                                    product_name = result_data.get('name', 'Unknown')
                                    product_category = self._categorize_product(product_name)

                                    # Filter by selected category
                                    if selected_category != "All" and product_category.lower() != selected_category.lower():
                                        continue  # Skip if doesn't match filter

                                    live_markdowns.append({
                                        'name': product_name,
                                        'brand': result_data.get('brand', ''),
                                        'low_price': result_data.get('low_price', 0),
                                        'high_price': result_data.get('high_price', 0),
                                        'discount_count': result_data.get('discount_count', 0),
                                        'markdown_type': result_data.get('markdown_type', []),
                                        'in_state': in_state,
                                        'url': result_data.get('url', ''),
                                        'category': product_category
                                    })
                            except:
                                continue

                except Exception as e:
                    self.after(0, lambda: self.status.configure(text=f"[ SCRAPER ERROR ]", text_color="#ff0000"))

                # Format results
                result = f"// LIVE WAREHOUSE RUNNER SCAN\n"
                result += f"// Target: #{warehouse} - {warehouse_city}, {warehouse_state}\n"
                result += f"// Category: {selected_category}\n"
                result += f"// Scanned: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                result += f"// Items Checked: {scrape_count}\n"
                result += "=" * 55 + "\n\n"

                if live_markdowns:
                    # Separate by state
                    in_state_deals = [m for m in live_markdowns if m.get('in_state')]
                    all_deals = sorted(live_markdowns, key=lambda x: x.get('low_price', 999))

                    result += f"LIVE MARKDOWNS FOUND: {len(live_markdowns)}\n"
                    if in_state_deals:
                        result += f"DEALS IN {warehouse_state}: {len(in_state_deals)}\n"
                    result += "\n"

                    if in_state_deals:
                        result += "-" * 55 + "\n"
                        result += f"MARKDOWNS IN {warehouse_state}:\n"
                        result += "-" * 55 + "\n\n"
                        for i, p in enumerate(sorted(in_state_deals, key=lambda x: x.get('low_price', 999))[:15], 1):
                            name = p.get('name', 'Unknown')[:42]
                            low = p.get('low_price', 0)
                            high = p.get('high_price', 0)
                            types = ', '.join(p.get('markdown_type', []))
                            result += f"{i:2}. {name}\n"
                            result += f"    ${low:.2f} - ${high:.2f}"
                            if high > 0 and low < high:
                                savings = ((high - low) / high) * 100
                                result += f" ({savings:.0f}% OFF)"
                            cat = p.get('category', 'other').upper()
                            result += f"\n    Type: {types} | Cat: {cat}\n\n"

                    result += "-" * 55 + "\n"
                    result += f"ALL LIVE MARKDOWNS:\n"
                    result += "-" * 55 + "\n\n"
                    for i, p in enumerate(all_deals[:20], 1):
                        name = p.get('name', 'Unknown')[:42]
                        low = p.get('low_price', 0)
                        high = p.get('high_price', 0)
                        stores = p.get('discount_count', '?')
                        cat = p.get('category', 'other').upper()
                        result += f"{i:2}. [{cat}] {name}\n"
                        result += f"    ${low:.2f} - ${high:.2f} | {stores} stores\n\n"
                else:
                    if selected_category != "All":
                        result += f"[ NO {selected_category.upper()} MARKDOWNS FOUND ]\n\n"
                        result += f"No products matching '{selected_category}' category were found.\n"
                        result += "Try selecting 'All' categories or a different filter.\n"
                    else:
                        result += "[ NO LIVE MARKDOWNS FOUND ]\n\n"
                        result += "The scraper checked items but found no current markdowns.\n"
                        result += "Try again later or check cached database.\n"

                # Save to file
                save_dir = self.config.get('save_directory')
                if save_dir:
                    try:
                        save_path = Path(save_dir)
                        save_path.mkdir(parents=True, exist_ok=True)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = save_path / f"live_scan_{warehouse}_{timestamp}.txt"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(result)
                        result += "\n" + "=" * 55 + "\n"
                        result += f"SAVED TO: {filename}\n"
                    except Exception as e:
                        result += f"\n[SAVE FAILED: {e}]\n"

                self.after(0, lambda: self._show_result(result))

            except Exception as e:
                import traceback
                error_msg = f"Error:\n{str(e)}\n\n{traceback.format_exc()}"
                self.after(0, lambda: self._show_error(error_msg))

        threading.Thread(target=scan, daemon=True).start()

    def _show_result(self, text: str):
        self.scanning = False
        self.scan_btn.configure(state="normal", text="EXECUTE SCAN")
        self.status.configure(text="[ SCAN COMPLETE ]", text_color=self.HIGHLIGHT)

        self.results.configure(state="normal")
        self.results.delete("1.0", "end")
        self.results.insert("1.0", text)
        self.results.configure(state="disabled")

    def _show_error(self, error: str):
        self.scanning = False
        self.scan_btn.configure(state="normal", text="EXECUTE SCAN")
        self.status.configure(text=f"[ ERROR ]", text_color="#ff0000")

    def _categorize_product(self, product_name: str) -> str:
        """Categorize product by keywords."""
        name_lower = product_name.lower()

        categories = {
            'electronics': ['tv', 'tablet', 'laptop', 'headphone', 'speaker', 'camera', 'phone', 'computer', 'monitor'],
            'home': ['furniture', 'mattress', 'bed', 'table', 'chair', 'sofa', 'desk', 'rug', 'pillow', 'blanket'],
            'kitchen': ['cookware', 'pan', 'pot', 'knife', 'blender', 'mixer', 'instant pot', 'air fryer'],
            'outdoor': ['grill', 'patio', 'lawn', 'garden', 'hose', 'mower', 'umbrella', 'gazebo'],
            'auto': ['tire', 'oil', 'car', 'auto', 'motor', 'synthetic', 'wiper', 'battery'],
            'toys': ['toy', 'game', 'puzzle', 'doll', 'lego', 'playstation', 'xbox', 'nintendo', 'nerf'],
            'clothing': ['shirt', 'pants', 'jacket', 'shoes', 'socks', 'dress', 'coat', 'sweater', 'jeans'],
            'health': ['vitamin', 'supplement', 'medicine', 'bandage', 'thermometer', 'protein', 'probiotic'],
            'cleaning': ['detergent', 'soap', 'cleaner', 'wipes', 'sanitizer', 'tide', 'dishwasher'],
            'office': ['paper', 'pen', 'printer', 'ink', 'stapler', 'binder', 'notebook'],
            'pet': ['dog', 'cat', 'pet', 'litter', 'leash', 'collar', 'aquarium'],
            'plants': ['plant', 'tree', 'flower', 'fern', 'orchid', 'foliage', 'juniper', 'maple'],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category

        return 'other'


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
