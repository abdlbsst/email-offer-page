#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Belkorchi LP Editor
- Deep purple/gold color scheme
- Modern typography
- Animated UI elements
- Card-based layout
"""

import re
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter.font import Font
import webbrowser
import threading
import time

INDEX_FILE = "index.html"

# ------------- Theme Constants -----------------
COLORS = {
    "bg": "#f5f9ff",          
    "card": "#ffffff",        
    "accent": "#4e9af1",      
    "accent_light": "#a9d6ff",
    "gold": "#ffda77",        
    "gold_dark": "#f4a261",   
    "text": "#2d3142",        
    "text_light": "#4f5d75",  
    "success": "#43aa8b",     
    "danger": "#ef476f",      
    "warning": "#faae3d"      
}

# ------------- Animation Helpers -----------------

class HoverButton(ttk.Button):
    def __init__(self, *args, **kwargs):
        self.hover_color = kwargs.pop('hover_color', COLORS['accent_light'])
        self.default_color = kwargs.pop('default_color', COLORS['accent'])
        self.animation_speed = kwargs.pop('animation_speed', 10)
        
        super().__init__(*args, **kwargs)
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
    def on_enter(self, e):
        self.config(style='Hover.TButton')
        
    def on_leave(self, e):
        self.config(style='TButton')

class AnimatedLabel(tk.Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flash_colors = [COLORS['success'], COLORS['bg']]
        self.flash_index = 0
        
    def flash(self, duration=500):
        self.flash_index = 0
        self._flash_step(duration)
        
    def _flash_step(self, duration):
        if self.flash_index < len(self.flash_colors):
            self.config(fg=self.flash_colors[self.flash_index])
            self.flash_index += 1
            self.after(duration//len(self.flash_colors), lambda: self._flash_step(duration))

# ------------- Small helpers -----------------

def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def regex_search(pattern, text, flags=re.DOTALL):
    m = re.search(pattern, text, flags)
    return m

def js_apps_to_python(js_array_str):
    """Convert JS array to Python list[dict]"""
    try:
        import json5
        return json5.loads(js_array_str)
    except Exception:
        pass

    s = js_array_str.strip()
    s = re.sub(r'\btrue\b', 'True', s)
    s = re.sub(r'\bfalse\b', 'False', s)
    s = re.sub(r'\bnull\b', 'None', s)

    def quote_keys(match):
        return f'"{match.group(1)}":'

    s = re.sub(r'(\b[a-zA-Z_][a-zA-Z0-9_]*\b)\s*:', quote_keys, s)

    try:
        return eval(s, {"__builtins__": {}})
    except Exception as e:
        raise ValueError("Could not parse APPS array. Please install `json5`. Error: " + str(e))

def python_apps_to_js(apps):
    """Convert Python list[dict] back to JS array"""
    def py_bool(v):
        return 'true' if v else 'false'

    def py_list(lst):
        return "[" + ", ".join(f'"{x}"' for x in lst) + "]"

    lines = ["const APPS = ["]
    for app in apps:
        lines.append("  {")
        lines.append(f'    name: "{app.get("name","")}",')
        lines.append(f'    icon: "{app.get("icon","")}",')
        lines.append(f'    locker_id: "{app.get("locker_id","")}",')
        platforms = app.get("platforms", [])
        lines.append(f'    platforms: {py_list(platforms)},')
        trending = py_bool(bool(app.get("trending", False)))
        featured = py_bool(bool(app.get("featured", False)))
        lines.append(f'    trending: {trending},')
        lines.append(f'    featured: {featured}')
        lines.append("  },")
    lines.append("];")
    return "\n".join(lines)

# ------------- Parsing / Writing index.html -----------------

class LPData:
    def __init__(self):
        self.html = ""
        self.logo_src = ""
        self.h1_title = ""
        self.tagline = ""
        self.meta_title = ""
        self.meta_desc = ""
        self.meta_keywords = ""
        self.og_image = ""
        self.twitter_image = ""
        self.cpab_it = ""
        self.cpab_key = ""
        self.apps = []

    def load(self, path=INDEX_FILE):
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found in current folder.")

        self.html = read_file(path)

        # Extract all fields
        m = regex_search(r'<img\s+class="logo"\s+src="([^"]+)"', self.html)
        if m: self.logo_src = m.group(1)

        m = regex_search(r'<h1>(.*?)</h1>', self.html)
        if m: self.h1_title = m.group(1)
        
        m = regex_search(r'<p class="tagline">(.*?)</p>', self.html)
        if m: self.tagline = m.group(1)

        m = regex_search(r'<title>(.*?)</title>', self.html)
        if m: self.meta_title = m.group(1)

        m = regex_search(r'<meta\s+name="description"\s+content="(.*?)"', self.html)
        if m: self.meta_desc = m.group(1)

        m = regex_search(r'<meta\s+name="keywords"\s+content="(.*?)"', self.html)
        if m: self.meta_keywords = m.group(1)

        m = regex_search(r'<meta\s+property="og:image"\s+content="(.*?)"', self.html)
        if m: self.og_image = m.group(1)
        
        m = regex_search(r'<meta\s+name="twitter:image"\s+content="(.*?)"', self.html)
        if m: self.twitter_image = m.group(1)

        m = regex_search(r'var\s+CPABUILDSETTINGS\s*=\s*({.*?});', self.html)
        if m:
            try:
                obj = json.loads(m.group(1))
                self.cpab_it = str(obj.get("it", ""))
                self.cpab_key = str(obj.get("key", ""))
            except Exception:
                it_m = re.search(r'"?it"?\s*:\s*([0-9]+)', m.group(1))
                key_m = re.search(r'"?key"?\s*:\s*"([^"]+)"', m.group(1))
                if it_m: self.cpab_it = it_m.group(1)
                if key_m: self.cpab_key = key_m.group(1)

        m = regex_search(r'const\s+APPS\s*=\s*\[(.*?)\];', self.html)
        if m:
            apps_array_str = "[" + m.group(1) + "]"
            self.apps = js_apps_to_python(apps_array_str)
        else:
            self.apps = []

    def save(self, path=INDEX_FILE):
        html = self.html

        # Update all fields
        html = re.sub(r'(<img\s+class="logo"\s+src=")([^"]+)(")', rf'\1{self.logo_src}\3', html)
        html = re.sub(r'(<h1>)(.*?)(</h1>)', rf'\1{self.h1_title}\3', html, flags=re.DOTALL)
        html = re.sub(r'(<p\s+class="tagline">)(.*?)(</p>)', rf'\1{self.tagline}\3', html, flags=re.DOTALL)
        html = re.sub(r'(<title>)(.*?)(</title>)', rf'\1{self.meta_title}\3', html, flags=re.DOTALL)

        if self.meta_desc:
            html = re.sub(r'(<meta\s+name="description"\s+content=")(.*?)(")', rf'\1{self.meta_desc}\3', html)
        if self.meta_keywords:
            html = re.sub(r'(<meta\s+name="keywords"\s+content=")(.*?)(")', rf'\1{self.meta_keywords}\3', html)
        if self.og_image:
            html = re.sub(r'(<meta\s+property="og:image"\s+content=")(.*?)(")', rf'\1{self.og_image}\3', html)
        if self.twitter_image:
            html = re.sub(r'(<meta\s+name="twitter:image"\s+content=")(.*?)(")', rf'\1{self.twitter_image}\3', html)

        cpab_json = json.dumps({"it": int(self.cpab_it or 0), "key": self.cpab_key or ""})
        html = re.sub(r'(var\s+CPABUILDSETTINGS\s*=\s*)({.*?})(\s*;)', rf'\1{cpab_json}\3', html, flags=re.DOTALL)

        new_apps_js = python_apps_to_js(self.apps)
        html = re.sub(r'const\s+APPS\s*=\s*\[(.*?)\];', new_apps_js, html, flags=re.DOTALL)

        write_file(path, html)
        self.html = html

# ------------- Modern GUI -----------------

class AppGUI(tk.Tk):
    def __init__(self, lpdata):
        super().__init__()
        self.title("Belkorchi LP Editor")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.lp = lpdata
        
        # Configure theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Initialize fonts
        self.title_font = ("Arial", 16, "bold")
        self.subtitle_font = ("Arial", 12, "bold")
        self.body_font = ("Arial", 10)
        self.button_font = ("Arial", 10, "bold")
        
        self._configure_styles()
        self.make_widgets()
        
        # Animation thread for background effects
        self.animation_active = True
        threading.Thread(target=self._animate_background, daemon=True).start()

    def _configure_styles(self):
        """Configure luxury dark theme styles"""
        # Main styles
        self.style.configure('.', 
                           background=COLORS['bg'], 
                           foreground=COLORS['text'],
                           font=self.body_font)
        
        self.style.configure('TFrame', background=COLORS['bg'])
        self.style.configure('Card.TFrame', background=COLORS['card'], 
                           borderwidth=2, relief='raised', 
                           bordercolor=COLORS['accent'])
        
        # Labels
        self.style.configure('Title.TLabel', 
                           font=self.title_font,
                           foreground=COLORS['gold'],
                           background=COLORS['bg'])
        
        self.style.configure('Subtitle.TLabel',
                           font=self.subtitle_font,
                           foreground=COLORS['text_light'],
                           background=COLORS['bg'])
        
        # Buttons
        self.style.configure('TButton',
                           background=COLORS['accent'],
                           foreground=COLORS['text_light'],
                           font=self.button_font,
                           borderwidth=0,
                           padding=8,
                           focuscolor=COLORS['bg'])
        
        self.style.map('TButton',
                      background=[('active', COLORS['accent_light']), 
                                ('pressed', COLORS['accent']),
                                ('disabled', '#555555')])
        
        self.style.configure('Accent.TButton',
                           background=COLORS['gold'],
                           foreground='black',
                           font=self.button_font)
        
        self.style.map('Accent.TButton',
                      background=[('active', COLORS['gold_dark']),
                                ('pressed', COLORS['gold']),
                                ('disabled', '#555555')])
        
        self.style.configure('Hover.TButton',
                           background=COLORS['accent_light'])
        
        # Notebook styles
        self.style.configure('TNotebook', background=COLORS['bg'], borderwidth=0)
        self.style.configure('TNotebook.Tab', 
                           background=COLORS['bg'],
                           foreground=COLORS['text'],
                           padding=[15, 5],
                           font=self.subtitle_font)
        
        self.style.map('TNotebook.Tab',
                      background=[('selected', COLORS['accent']),
                                 ('active', COLORS['card'])],
                      foreground=[('selected', COLORS['text_light']),
                                 ('active', COLORS['text_light'])])
        
        # Treeview styles
        self.style.configure('Treeview',
                           background=COLORS['card'],
                           fieldbackground=COLORS['card'],
                           foreground=COLORS['text'],
                           rowheight=28,
                           borderwidth=0)
        
        self.style.configure('Treeview.Heading',
                           background=COLORS['accent'],
                           foreground=COLORS['text_light'],
                           font=self.subtitle_font,
                           padding=8,
                           relief='flat')
        
        self.style.map('Treeview',
                      background=[('selected', COLORS['accent_light'])])
        
        # Scrollbar styles
        self.style.configure('Vertical.TScrollbar',
                           background=COLORS['card'],
                           arrowcolor=COLORS['text'],
                           bordercolor=COLORS['card'])
        
        self.style.configure('Horizontal.TScrollbar',
                           background=COLORS['card'],
                           arrowcolor=COLORS['text'],
                           bordercolor=COLORS['card'])
        
        # Entry styles
        self.style.configure('TEntry',
                           fieldbackground=COLORS['card'],
                           foreground=COLORS['text_light'],
                           insertcolor=COLORS['text_light'],
                           bordercolor=COLORS['accent'],
                           lightcolor=COLORS['accent'],
                           padding=5)
        
        # Checkbutton styles
        self.style.configure('TCheckbutton',
                           background=COLORS['bg'],
                           foreground=COLORS['text'],
                           indicatorbackground=COLORS['card'],
                           indicatorcolor=COLORS['accent'])
        
        self.style.map('TCheckbutton',
                      indicatorbackground=[('active', COLORS['accent_light']),
                                        ('selected', COLORS['gold'])])

    def _animate_background(self):
        """Background animation thread"""
        colors = [COLORS['bg'], "#1e1e3a", "#222242"]
        i = 0
        while self.animation_active:
            self.configure(background=colors[i % len(colors)])
            i += 1
            time.sleep(3)

    def make_widgets(self):
        # Main container
        main_frame = ttk.Frame(self, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Header with logo and title
        header = ttk.Frame(main_frame)
        header.pack(fill='x', pady=(0, 15))
        
        # Title with gold accent
        title_frame = ttk.Frame(header)
        title_frame.pack(side='left', padx=10)
        
        ttk.Label(title_frame, text="🦇", font=("", 24)).pack(side='left')
        ttk.Label(title_frame, text="Belkorchi LP Editor", 
                 style='Title.TLabel').pack(side='left', padx=10)
        
        # Help button
        help_btn = HoverButton(header, text="❔ Help", 
                              command=self.show_help,
                              default_color=COLORS['gold'],
                              hover_color=COLORS['gold_dark'])
        help_btn.pack(side='right', padx=10)
        
        # Notebook (tabs)
        nb = ttk.Notebook(main_frame)
        nb.pack(fill='both', expand=True)
        
        # Create tabs
        self.tab_general = ttk.Frame(nb, style='Card.TFrame')
        self.tab_seo = ttk.Frame(nb, style='Card.TFrame')
        self.tab_cpab = ttk.Frame(nb, style='Card.TFrame')
        self.tab_apps = ttk.Frame(nb, style='Card.TFrame')
        
        nb.add(self.tab_general, text="General Settings")
        nb.add(self.tab_seo, text="SEO & Social")
        nb.add(self.tab_cpab, text="CPA Config")
        nb.add(self.tab_apps, text="App Manager")
        
        # Initialize tabs
        self.init_general_tab()
        self.init_seo_tab()
        self.init_cpab_tab()
        self.init_apps_tab()
        
        # Status bar with animated effects
        self.status_bar = AnimatedLabel(main_frame, text="Ready", 
                                      relief='sunken', anchor='w',
                                      font=self.body_font,
                                      background=COLORS['card'],
                                      foreground=COLORS['text_light'])
        self.status_bar.pack(fill='x', pady=(10, 0))
        
        # Save button with animation
        save_frame = ttk.Frame(main_frame)
        save_frame.pack(fill='x', pady=(10, 0))
        
        save_btn = HoverButton(save_frame, text="💾 Save Changes", 
                              command=self.save_changes, 
                              style='Accent.TButton',
                              default_color=COLORS['gold'],
                              hover_color=COLORS['gold_dark'])
        save_btn.pack(pady=5, ipadx=20, ipady=5)
        
        # Preview button
        preview_btn = HoverButton(save_frame, text="👁️ Preview", 
                                command=self.preview_changes,
                                default_color=COLORS['accent'],
                                hover_color=COLORS['accent_light'])
        preview_btn.pack(pady=5, ipadx=20, ipady=5)

    def init_general_tab(self):
        f = self.tab_general
        
        # Container with scroll
        container = ttk.Frame(f)
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(container, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style='Card.TFrame')
        
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Section title
        ttk.Label(scroll_frame, text="General Settings", style='Subtitle.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')
        
        # Variables
        self.logo_var = tk.StringVar(value=self.lp.logo_src)
        self.h1_var = tk.StringVar(value=self.lp.h1_title)
        self.tagline_var = tk.StringVar(value=self.lp.tagline)
        
        # Form fields with modern styling
        ttk.Label(scroll_frame, text="Logo URL:", style='Subtitle.TLabel').grid(row=1, column=0, sticky='w', padx=10, pady=8)
        logo_entry = ttk.Entry(scroll_frame, textvariable=self.logo_var, width=80)
        logo_entry.grid(row=1, column=1, sticky='we', padx=10, pady=8)
        
        ttk.Label(scroll_frame, text="Main Title:", style='Subtitle.TLabel').grid(row=2, column=0, sticky='w', padx=10, pady=8)
        ttk.Entry(scroll_frame, textvariable=self.h1_var, width=80).grid(row=2, column=1, sticky='we', padx=10, pady=8)
        
        ttk.Label(scroll_frame, text="Tagline:", style='Subtitle.TLabel').grid(row=3, column=0, sticky='w', padx=10, pady=8)
        ttk.Entry(scroll_frame, textvariable=self.tagline_var, width=80).grid(row=3, column=1, sticky='we', padx=10, pady=8)
        
        scroll_frame.grid_columnconfigure(1, weight=1)

    def init_seo_tab(self):
        f = self.tab_seo
        
        container = ttk.Frame(f, style='Card.TFrame')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Section title
        ttk.Label(container, text="SEO & Social Media", style='Subtitle.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')
        
        # Variables
        self.meta_title_var = tk.StringVar(value=self.lp.meta_title)
        self.meta_desc_var = tk.StringVar(value=self.lp.meta_desc)
        self.meta_keywords_var = tk.StringVar(value=self.lp.meta_keywords)
        self.og_image_var = tk.StringVar(value=self.lp.og_image)
        self.twitter_image_var = tk.StringVar(value=self.lp.twitter_image)
        
        # Form fields
        fields = [
            ("Page Title (<title>)", self.meta_title_var),
            ("Meta Description", self.meta_desc_var),
            ("Meta Keywords", self.meta_keywords_var),
            ("OG Image URL", self.og_image_var),
            ("Twitter Image URL", self.twitter_image_var)
        ]
        
        for idx, (label, var) in enumerate(fields, start=1):
            ttk.Label(container, text=label + ":", style='Subtitle.TLabel').grid(row=idx, column=0, sticky='w', padx=10, pady=8)
            ttk.Entry(container, textvariable=var, width=90).grid(row=idx, column=1, sticky='we', padx=10, pady=8)
        
        container.grid_columnconfigure(1, weight=1)

    def init_cpab_tab(self):
        f = self.tab_cpab
        
        container = ttk.Frame(f, style='Card.TFrame')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Section title
        ttk.Label(container, text="CPA Build Settings", style='Subtitle.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')
        
        # Variables
        self.cpab_it_var = tk.StringVar(value=self.lp.cpab_it)
        self.cpab_key_var = tk.StringVar(value=self.lp.cpab_key)
        
        # Form fields
        ttk.Label(container, text="CPA IT Value:", style='Subtitle.TLabel').grid(row=1, column=0, sticky='w', padx=10, pady=12)
        ttk.Entry(container, textvariable=self.cpab_it_var, width=30).grid(row=1, column=1, sticky='w', padx=10, pady=12)
        
        ttk.Label(container, text="CPA Key:", style='Subtitle.TLabel').grid(row=2, column=0, sticky='w', padx=10, pady=12)
        ttk.Entry(container, textvariable=self.cpab_key_var, width=60).grid(row=2, column=1, sticky='w', padx=10, pady=12)
        
        container.grid_columnconfigure(1, weight=1)

    def init_apps_tab(self):
        f = self.tab_apps
        
        # Main container
        container = ttk.Frame(f, style='Card.TFrame')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Section title
        ttk.Label(container, text="App Management", style='Subtitle.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky='w')
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(container)
        tree_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(0, 10))
        
        cols = ("name", "icon", "locker_id", "platforms", "trending", "featured")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=15)
        
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Configure columns
        for c in cols:
            self.tree.heading(c, text=c.title(), anchor='w')
            self.tree.column(c, width=160 if c=="name" else 120, anchor='w')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Button frame
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(5, 0))
        
        # Action buttons with hover effects
        actions = [
            ("➕ Add App", self.add_app, COLORS['success']),
            ("✏️ Edit App", self.edit_selected_app, COLORS['accent']),
            ("🗑️ Delete App", self.delete_selected_app, COLORS['danger']),
            ("⬆️ Move Up", self.move_up, COLORS['accent']),
            ("⬇️ Move Down", self.move_down, COLORS['accent'])
        ]
        
        for i, (text, cmd, color) in enumerate(actions):
            btn = HoverButton(btn_frame, text=text, command=cmd,
                            default_color=color,
                            hover_color=self._lighten_color(color, 20))
            btn.grid(row=0, column=i, padx=5, sticky='ew')
            btn_frame.grid_columnconfigure(i, weight=1)
        
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        
        self.refresh_tree()

    def _lighten_color(self, hex_color, amount):
        """Lighten a hex color by a percentage amount"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        lighter = tuple(min(255, int(c + (255 - c) * amount / 100)) for c in rgb)
        return f'#{lighter[0]:02x}{lighter[1]:02x}{lighter[2]:02x}'

    def refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, app in enumerate(self.lp.apps):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    app.get("name",""),
                    app.get("icon",""),
                    app.get("locker_id",""),
                    ", ".join(app.get("platforms",[])),
                    "✔️" if app.get("trending", False) else "❌",
                    "✔️" if app.get("featured", False) else "❌",
                )
            )

    def add_app(self):
        data = self.prompt_app_data()
        if not data:
            return
        self.lp.apps.append(data)
        self.refresh_tree()
        self.status_bar.config(text=f"Added app: {data['name']}")
        self.status_bar.flash()

    def edit_selected_app(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Edit", "Select an app first.")
            return
        idx = int(sel[0])
        old = self.lp.apps[idx]
        data = self.prompt_app_data(old)
        if not data:
            return
        self.lp.apps[idx] = data
        self.refresh_tree()
        self.status_bar.config(text=f"Updated app: {data['name']}")
        self.status_bar.flash()

    def delete_selected_app(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select an app first.")
            return
        idx = int(sel[0])
        app_name = self.lp.apps[idx].get('name','')
        if messagebox.askyesno("Delete", f"Delete '{app_name}'?"):
            self.lp.apps.pop(idx)
            self.refresh_tree()
            self.status_bar.config(text=f"Deleted app: {app_name}")
            self.status_bar.flash()

    def move_up(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx <= 0:
            return
        self.lp.apps[idx-1], self.lp.apps[idx] = self.lp.apps[idx], self.lp.apps[idx-1]
        self.refresh_tree()
        self.tree.selection_set(str(idx-1))
        self.status_bar.config(text=f"Moved app up: {self.lp.apps[idx-1].get('name','')}")
        self.status_bar.flash()

    def move_down(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx >= len(self.lp.apps) - 1:
            return
        self.lp.apps[idx+1], self.lp.apps[idx] = self.lp.apps[idx], self.lp.apps[idx+1]
        self.refresh_tree()
        self.tree.selection_set(str(idx+1))
        self.status_bar.config(text=f"Moved app down: {self.lp.apps[idx+1].get('name','')}")
        self.status_bar.flash()

    def prompt_app_data(self, initial=None):
        d = AppDialog(self, initial)
        self.wait_window(d)
        return d.result

    def save_changes(self):
        # Pull back vars
        self.lp.logo_src = self.logo_var.get().strip()
        self.lp.h1_title = self.h1_var.get().strip()
        self.lp.tagline = self.tagline_var.get().strip()

        self.lp.meta_title = self.meta_title_var.get().strip()
        self.lp.meta_desc = self.meta_desc_var.get().strip()
        self.lp.meta_keywords = self.meta_keywords_var.get().strip()
        self.lp.og_image = self.og_image_var.get().strip()
        self.lp.twitter_image = self.twitter_image_var.get().strip()

        self.lp.cpab_it = self.cpab_it_var.get().strip() or "0"
        self.lp.cpab_key = self.cpab_key_var.get().strip()

        try:
            self.lp.save(INDEX_FILE)
            messagebox.showinfo("Saved", "index.html updated successfully!")
            self.status_bar.config(text="Changes saved successfully", fg=COLORS['success'])
            self.status_bar.flash()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save: {e}")
            self.status_bar.config(text=f"Error saving: {str(e)}", fg=COLORS['danger'])
            self.status_bar.flash()

    def preview_changes(self):
        try:
            # Save to a temp file
            temp_file = "preview.html"
            self.lp.save(temp_file)
            
            # Open in default browser
            webbrowser.open(f"file://{os.path.abspath(temp_file)}")
            self.status_bar.config(text="Preview opened in browser", fg=COLORS['success'])
            self.status_bar.flash()
        except Exception as e:
            messagebox.showerror("Preview Error", f"Could not open preview: {e}")
            self.status_bar.config(text=f"Preview error: {str(e)}", fg=COLORS['danger'])
            self.status_bar.flash()

    def show_help(self):
        help_text = """Belkorchi LP Editor Help:

1. General Settings: Edit logo, title and tagline
2. SEO & Social: Configure meta tags for search engines
3. CPA Config: Set up CPA Build settings
4. App Manager: Add/edit/delete apps in your locker

Use the 'Preview' button to see changes in your browser before saving.
"""
        messagebox.showinfo("Help", help_text)

    def __del__(self):
        self.animation_active = False

# --------- App Dialog ----------

class AppDialog(tk.Toplevel):
    def __init__(self, master, initial=None):
        super().__init__(master)
        self.title("App Editor")
        self.result = None
        self.initial = initial or {}
        
        # Set theme
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('.', background=COLORS['bg'], foreground=COLORS['text'])
        self.style.configure('TLabel', background=COLORS['bg'], foreground=COLORS['text'])
        self.style.configure('TEntry', fieldbackground=COLORS['card'], foreground=COLORS['text_light'])
        self.style.configure('TButton', background=COLORS['accent'], foreground=COLORS['text_light'])
        self.style.map('TButton', background=[('active', COLORS['accent_light']), ('pressed', COLORS['accent'])])
        self.style.configure('TCheckbutton', background=COLORS['bg'], foreground=COLORS['text'])
        
        self.name_var = tk.StringVar(value=self.initial.get("name",""))
        self.icon_var = tk.StringVar(value=self.initial.get("icon",""))
        self.locker_var = tk.StringVar(value=self.initial.get("locker_id",""))
        self.platforms_var = tk.StringVar(value=",".join(self.initial.get("platforms",["android","ios"])))
        self.trending_var = tk.BooleanVar(value=bool(self.initial.get("trending", False)))
        self.featured_var = tk.BooleanVar(value=bool(self.initial.get("featured", False)))

        self.make_widgets()
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

    def make_widgets(self):
        # Main container
        container = ttk.Frame(self, style='Card.TFrame')
        container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Title
        ttk.Label(container, text="App Details", style='Subtitle.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        row = 1
        ttk.Label(container, text="Name:", style='Subtitle.TLabel').grid(row=row, column=0, sticky="w", padx=10, pady=8)
        name_entry = ttk.Entry(container, textvariable=self.name_var, width=50)
        name_entry.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        ttk.Label(container, text="Icon URL:", style='Subtitle.TLabel').grid(row=row, column=0, sticky="w", padx=10, pady=8)
        icon_entry = ttk.Entry(container, textvariable=self.icon_var, width=50)
        icon_entry.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        ttk.Label(container, text="Locker ID:", style='Subtitle.TLabel').grid(row=row, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(container, textvariable=self.locker_var, width=50).grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        ttk.Label(container, text="Platforms (comma separated):", style='Subtitle.TLabel').grid(row=row, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(container, textvariable=self.platforms_var, width=50).grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        # Checkboxes in a frame
        check_frame = ttk.Frame(container)
        check_frame.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        
        ttk.Checkbutton(check_frame, text="Trending", variable=self.trending_var, 
                       style='TCheckbutton').pack(side="left", padx=15)
        ttk.Checkbutton(check_frame, text="Featured", variable=self.featured_var,
                       style='TCheckbutton').pack(side="left", padx=15)
        row += 1

        # Button frame
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)
        
        cancel_btn = HoverButton(btn_frame, text="Cancel", command=self.destroy,
                               default_color=COLORS['danger'],
                               hover_color=self._lighten_color(COLORS['danger'], 20))
        cancel_btn.pack(side="left", padx=15)
        
        save_btn = HoverButton(btn_frame, text="Save", command=self.ok,
                             default_color=COLORS['success'],
                             hover_color=self._lighten_color(COLORS['success'], 20))
        save_btn.pack(side="left", padx=15)

    def _lighten_color(self, hex_color, amount):
        """Lighten a hex color by a percentage amount"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        lighter = tuple(min(255, int(c + (255 - c) * amount / 100)) for c in rgb)
        return f'#{lighter[0]:02x}{lighter[1]:02x}{lighter[2]:02x}'

    def ok(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required.")
            return
        icon = self.icon_var.get().strip()
        locker = self.locker_var.get().strip()
        plats = [p.strip().lower() for p in self.platforms_var.get().split(",") if p.strip()]

        self.result = {
            "name": name,
            "icon": icon,
            "locker_id": locker,
            "platforms": plats,
            "trending": self.trending_var.get(),
            "featured": self.featured_var.get()
        }
        self.destroy()

# ------------- main -----------------

def main():
    try:
        lp = LPData()
        lp.load(INDEX_FILE)
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return

    app = AppGUI(lp)
    try:
        app.mainloop()
    finally:
        app.animation_active = False

if __name__ == "__main__":
    main()