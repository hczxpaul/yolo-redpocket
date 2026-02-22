import sys
import os
import logging
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed

from config_utils import load_classes_from_config

logger = logging.getLogger(__name__)





def check_label_file(label_path):
    issues = []
    if not label_path.exists():
        return issues
    
    try:
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) != 5:
                issues.append({
                    'line': line_num,
                    'type': 'format_error',
                    'message': f'格式错误，期望5个值，实际{len(parts)}个',
                    'value': line
                })
                continue
            
            try:
                cls = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                box_w = float(parts[3])
                box_h = float(parts[4])
                
                if x_center < 0 or x_center > 1:
                    issues.append({
                        'line': line_num,
                        'type': 'x_out_of_range',
                        'message': f'x_center超出范围[0,1]',
                        'value': x_center
                    })
                
                if y_center < 0 or y_center > 1:
                    issues.append({
                        'line': line_num,
                        'type': 'y_out_of_range',
                        'message': f'y_center超出范围[0,1]',
                        'value': y_center
                    })
                
                if box_w < 0 or box_w > 1:
                    issues.append({
                        'line': line_num,
                        'type': 'w_out_of_range',
                        'message': f'width超出范围[0,1]',
                        'value': box_w
                    })
                
                if box_h < 0 or box_h > 1:
                    issues.append({
                        'line': line_num,
                        'type': 'h_out_of_range',
                        'message': f'height超出范围[0,1]',
                        'value': box_h
                    })
                
                if x_center < 0:
                    issues.append({
                        'line': line_num,
                        'type': 'negative_x',
                        'message': f'x_center为负数',
                        'value': x_center
                    })
                
                if y_center < 0:
                    issues.append({
                        'line': line_num,
                        'type': 'negative_y',
                        'message': f'y_center为负数',
                        'value': y_center
                    })
                
                if box_w < 0:
                    issues.append({
                        'line': line_num,
                        'type': 'negative_w',
                        'message': f'width为负数',
                        'value': box_w
                    })
                
                if box_h < 0:
                    issues.append({
                        'line': line_num,
                        'type': 'negative_h',
                        'message': f'height为负数',
                        'value': box_h
                    })
                
            except ValueError as e:
                issues.append({
                    'line': line_num,
                    'type': 'value_error',
                    'message': f'数值解析错误: {str(e)}',
                    'value': line
                })
    
    except Exception as e:
        issues.append({
            'line': 0,
            'type': 'file_error',
            'message': f'文件读取错误: {str(e)}',
            'value': str(label_path)
        })
    
    return issues


def fix_label_file(label_path, issues):
    if not label_path.exists():
        return False
    
    try:
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        fixed_lines = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                fixed_lines.append('')
                continue
            
            parts = line.split()
            if len(parts) != 5:
                fixed_lines.append(line)
                continue
            
            try:
                cls = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                box_w = float(parts[3])
                box_h = float(parts[4])
                
                x_center = max(0.001, min(0.999, abs(x_center)))
                y_center = max(0.001, min(0.999, abs(y_center)))
                box_w = max(0.001, min(0.999, abs(box_w)))
                box_h = max(0.001, min(0.999, abs(box_h)))
                
                fixed_lines.append(f"{cls} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}")
            
            except ValueError:
                fixed_lines.append(line)
        
        with open(label_path, 'w') as f:
            f.write('\n'.join(fixed_lines) + '\n')
        
        return True
    
    except Exception as e:
        logger.error(f"修复标注文件失败: {e}")
        return False


class ThumbnailBrowser:
    def __init__(self, parent, on_image_select, classes):
        self.parent = parent
        self.on_image_select = on_image_select
        self.classes = classes
        self.image_list = []
        self.current_index = -1
        self.thumbnails = {}
        self.thumbnail_photos = {}
        self.problem_images = set()
        self.class_filter = -1
        self.image_class_cache = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        self.scroll_frame = ttk.Frame(self.parent)
        self.scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.scroll_frame, bg='#1a1a1a', highlightthickness=0)
        self.scrollbar_y = ttk.Scrollbar(self.scroll_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(self.scroll_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor=tk.NW)
        
        self.inner_frame.bind('<Configure>', self.on_inner_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        self.canvas.bind_all('<MouseWheel>', self.on_mousewheel)
        
    def on_inner_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        
    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        
    def clear(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        self.thumbnail_photos.clear()
        self.image_list = []
        self.current_index = -1
        self.problem_images.clear()
        self.image_class_cache.clear()
    
    def get_image_classes(self, img_path):
        classes_in_image = set()
        label_path = None
        
        possible_paths = [
            img_path.parent.parent / 'labels' / 'train' / (img_path.stem + '.txt'),
            img_path.parent.parent / 'labels' / 'val' / (img_path.stem + '.txt'),
            img_path.parent.parent / 'labels' / (img_path.stem + '.txt'),
            Path('dataset/labels/train') / (img_path.stem + '.txt'),
            Path('dataset/labels/val') / (img_path.stem + '.txt'),
            Path('dataset/labels') / (img_path.stem + '.txt'),
        ]
        
        for p in possible_paths:
            if p.exists():
                label_path = p
                break
        
        if label_path and label_path.exists():
            try:
                with open(label_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 5:
                            cls = int(parts[0])
                            classes_in_image.add(cls)
            except Exception as e:
                logger.warning(f"读取标注文件失败: {label_path}, 错误: {e}")
        
        return classes_in_image
    
    def load_images(self, image_paths):
        self.clear()
        self.image_list = image_paths
        
        thumbnail_size = 150
        cols = 4
        
        def process_single_image(args):
            i, img_path = args
            try:
                img = cv2.imread(str(img_path))
                if img is not None:
                    h, w = img.shape[:2]
                    scale = min(thumbnail_size / w, thumbnail_size / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    
                    resized = cv2.resize(img, (new_w, new_h))
                    resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                    
                    img_pil = Image.fromarray(resized)
                    classes_in_image = self.get_image_classes(img_path)
                    return (i, img_pil, classes_in_image)
            except Exception as e:
                logger.error(f"无法加载缩略图: {img_path}, 错误: {e}")
            return None
        
        with ThreadPoolExecutor(max_workers=min(8, len(image_paths))) as executor:
            futures = [executor.submit(process_single_image, (i, path)) 
                      for i, path in enumerate(image_paths)]
            
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    i, img_pil, classes_in_image = result
                    self.thumbnails[i] = img_pil
                    self.thumbnail_photos[i] = ImageTk.PhotoImage(img_pil)
                    self.image_class_cache[i] = classes_in_image
        
        self.display_thumbnails(cols)
    
    def set_class_filter(self, class_id):
        self.class_filter = class_id
        self.display_thumbnails(4)
        
    def set_problem_images(self, problem_indices):
        self.problem_images = set(problem_indices)
        self.display_thumbnails(4)
        
    def display_thumbnails(self, cols=4):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        
        display_count = 0
        for i in range(len(self.image_list)):
            if self.class_filter >= 0:
                if i not in self.image_class_cache or self.class_filter not in self.image_class_cache[i]:
                    continue
            
            row = display_count // cols
            col = display_count % cols
            display_count += 1
            
            is_problem = i in self.problem_images
            bg_color = '#4a1a1a' if is_problem else '#2a2a2a'
            border_color = '#ff4444' if is_problem else '#2a2a2a'
            
            frame = ttk.Frame(self.inner_frame, padding=5)
            frame.grid(row=row, column=col, sticky=tk.NSEW)
            
            if i in self.thumbnail_photos:
                btn_frame = tk.Frame(frame, bg=border_color, padx=2, pady=2)
                btn_frame.pack()
                
                btn = tk.Button(
                    btn_frame,
                    image=self.thumbnail_photos[i],
                    command=lambda idx=i: self.select_image(idx),
                    relief=tk.FLAT,
                    bg=bg_color,
                    activebackground='#3a3a3a'
                )
                btn.pack()
                
                label_text = self.image_list[i].name[:15] + ('...' if len(self.image_list[i].name) > 15 else '')
                if is_problem:
                    label_text = '⚠ ' + label_text
                
                label = tk.Label(
                    frame,
                    text=label_text,
                    fg='white' if not is_problem else '#ff8888',
                    bg=bg_color,
                    anchor=tk.CENTER,
                    font=('Arial', 8, 'bold' if is_problem else 'normal')
                )
                label.pack(fill=tk.X, pady=(2, 0))
                
                btn.bind('<Button-1>', lambda e, idx=i: self.select_image(idx))
                
        for col in range(cols):
            self.inner_frame.grid_columnconfigure(col, weight=1)
            
    def select_image(self, index):
        self.current_index = index
        self.highlight_thumbnail(index)
        if self.on_image_select:
            self.on_image_select(self.image_list[index], index)
            
    def highlight_thumbnail(self, index):
        for widget in self.inner_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Frame):
                    for btn in child.winfo_children():
                        if isinstance(btn, tk.Button):
                            i = self.current_index
                            is_problem = i in self.problem_images if i >= 0 else False
                            btn.configure(bg='#4a1a1a' if is_problem else '#2a2a2a')
                elif isinstance(child, tk.Label):
                    i = self.current_index
                    is_problem = i in self.problem_images if i >= 0 else False
                    child.configure(bg='#4a1a1a' if is_problem else '#2a2a2a')
            
        if 0 <= index < len(self.image_list):
            cols = 4
            row = index // cols
            col = index % cols
            frame_widgets = self.inner_frame.grid_slaves(row=row, column=col)
            if frame_widgets:
                frame = frame_widgets[0]
                for child in frame.winfo_children():
                    if isinstance(child, tk.Frame):
                        for btn in child.winfo_children():
                            if isinstance(btn, tk.Button):
                                btn.configure(bg='#005599')
                    elif isinstance(child, tk.Label):
                        child.configure(bg='#005599')
                
    def go_to_previous(self):
        if self.current_index > 0:
            self.select_image(self.current_index - 1)
            
    def go_to_next(self):
        if self.current_index < len(self.image_list) - 1:
            self.select_image(self.current_index + 1)


class LabelingTool:
    """
    标注工具主类
    
    Attributes:
        BOX_COLORS: 检测框颜色常量字典，与main.py保持一致
    """
    
    BOX_COLORS = {
        'red_packet': (0, 255, 0),
        'open_button': (255, 0, 0),
        'amount_text': (0, 0, 255),
        'close_button': (255, 255, 0),
        'back_button': (255, 128, 0),
        'opened_red_packet': (128, 128, 128),
        'play_button': (0, 255, 255)
    }
    
    def __init__(self, root):
        self.root = root
        self.root.title("红包标注工具 - 增强版")
        self.root.geometry("1900x1050")
        self.root.minsize(1700, 950)
        
        self.current_image = None
        self.current_image_path = None
        self.current_boxes = []
        self.image_list = []
        self.current_index = 0
        
        self.drawing = False
        self.start_point = None
        self.temp_rect = None
        
        self.classes = load_classes_from_config()
        self.current_class = 0
        
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self.problem_images_info = {}
        self.current_issues = []
        
        self.setup_ui()
        
    def setup_ui(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开图片文件夹", command=self.open_folder)
        file_menu.add_command(label="打开单张图片", command=self.open_image)
        file_menu.add_separator()
        file_menu.add_command(label="保存标注", command=self.save_labels)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="检查所有标注", command=self.check_all_labels)
        tools_menu.add_command(label="修复所有问题标注", command=self.fix_all_problem_labels)
        tools_menu.add_separator()
        tools_menu.add_command(label="检查当前标注", command=self.check_current_label)
        tools_menu.add_command(label="修复当前标注", command=self.fix_current_label)
        
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        left_panel = ttk.Frame(main_frame, width=420)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        class_frame = ttk.LabelFrame(left_panel, text="目标类别", padding=10)
        class_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.class_var = tk.IntVar(value=0)
        for i, cls in enumerate(self.classes):
            rb = ttk.Radiobutton(class_frame, text=cls, value=i, 
                                variable=self.class_var, command=self.on_class_change)
            rb.pack(anchor=tk.W)
        
        filter_frame = ttk.LabelFrame(left_panel, text="类别筛选", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.filter_class_var = tk.IntVar(value=-1)
        
        ttk.Radiobutton(filter_frame, text="全部", value=-1,
                        variable=self.filter_class_var, command=self.on_filter_change).pack(anchor=tk.W)
        
        for i, cls in enumerate(self.classes):
            ttk.Radiobutton(filter_frame, text=cls, value=i,
                            variable=self.filter_class_var, command=self.on_filter_change).pack(anchor=tk.W)
        
        thumbnail_frame = ttk.LabelFrame(left_panel, text="缩略图浏览器", padding=5)
        thumbnail_frame.pack(fill=tk.BOTH, expand=True)
        
        self.thumbnail_browser = ThumbnailBrowser(thumbnail_frame, self.on_thumbnail_select, self.classes)
        
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="上一张", command=self.prev_image).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame, text="下一张", command=self.next_image).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        ttk.Button(left_panel, text="删除当前文件", command=self.delete_current_file).pack(fill=tk.X, pady=(10, 0))
        
        center_panel = ttk.Frame(main_frame)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas_frame = ttk.LabelFrame(center_panel, text="标注区域", padding=5)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#2b2b2b', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_move)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.canvas.bind('<Button-3>', self.on_right_click)
        
        right_panel = ttk.Frame(main_frame, width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_panel.pack_propagate(False)
        
        box_frame = ttk.LabelFrame(right_panel, text="标注框列表", padding=10)
        box_frame.pack(fill=tk.BOTH, expand=True)
        
        self.box_listbox = tk.Listbox(box_frame, selectmode=tk.SINGLE)
        self.box_listbox.pack(fill=tk.BOTH, expand=True)
        self.box_listbox.bind('<<ListboxSelect>>', self.on_box_select)
        
        ttk.Button(box_frame, text="删除选中", command=self.delete_box).pack(fill=tk.X, pady=(10, 0))
        ttk.Button(box_frame, text="清空全部", command=self.clear_boxes).pack(fill=tk.X, pady=(5, 0))
        
        issues_frame = ttk.LabelFrame(right_panel, text="⚠ 问题标注检测", padding=10)
        issues_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.issues_listbox = tk.Listbox(issues_frame, selectmode=tk.SINGLE, fg='#ff4444', height=6)
        self.issues_listbox.pack(fill=tk.X)
        self.issues_listbox.bind('<<ListboxSelect>>', self.on_issue_select)
        
        issues_btn_frame = ttk.Frame(issues_frame)
        issues_btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(issues_btn_frame, text="检查", command=self.check_current_label).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(issues_btn_frame, text="修复", command=self.fix_current_label).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        info_frame = ttk.LabelFrame(right_panel, text="信息", padding=10)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.info_label = ttk.Label(info_frame, text="请打开图片文件夹")
        self.info_label.pack(anchor=tk.W)
        
        self.stats_label = ttk.Label(info_frame, text="已标注: 0/0")
        self.stats_label.pack(anchor=tk.W)
        
        self.problem_stats_label = ttk.Label(info_frame, text="问题标注: 0", foreground='#ff4444')
        self.problem_stats_label.pack(anchor=tk.W)
        
        shortcut_frame = ttk.LabelFrame(right_panel, text="快捷键", padding=10)
        shortcut_frame.pack(fill=tk.X, pady=(10, 0))
        
        class_keys_text = f"1-{len(self.classes)}" if len(self.classes) > 1 else "1"
        shortcuts = [
            "左键拖动: 绘制框",
            "右键: 删除框",
            f"{class_keys_text}: 切换类别",
            "A/D: 上/下一张",
            "Delete: 删除当前文件",
            "Ctrl+S: 保存"
        ]
        for s in shortcuts:
            ttk.Label(shortcut_frame, text=s).pack(anchor=tk.W)
        
        self.root.bind('<Key>', self.on_key_press)
        self.root.bind('<Control-s>', lambda e: self.save_labels())
        
    def on_class_change(self):
        self.current_class = self.class_var.get()
    
    def on_filter_change(self):
        filter_class = self.filter_class_var.get()
        self.thumbnail_browser.set_class_filter(filter_class)
        
    def on_thumbnail_select(self, image_path, index):
        self.save_labels()
        self.current_index = index
        self.load_image(index)
        
    def open_folder(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if folder:
            self.image_list = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp']:
                self.image_list.extend(Path(folder).glob(ext))
            
            self.image_list.sort(key=lambda p: p.stat().st_mtime)
            self.thumbnail_browser.load_images(self.image_list)
            
            if self.image_list:
                self.current_index = 0
                self.thumbnail_browser.select_image(0)
                self.update_stats()
                
    def open_image(self):
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp")]
        )
        if file_path:
            self.image_list = [Path(file_path)]
            self.thumbnail_browser.load_images(self.image_list)
            self.current_index = 0
            self.thumbnail_browser.select_image(0)
            
    def load_image(self, index):
        if 0 <= index < len(self.image_list):
            self.current_index = index
            self.current_image_path = self.image_list[index]
            self.current_image = cv2.imread(str(self.current_image_path))
            
            if self.current_image is not None:
                self.current_boxes = []
                self.load_existing_labels()
                self.display_image()
                self.update_box_list()
                self.info_label.config(text=f"当前: {self.current_image_path.name}")
                self.check_current_label()
                
    def load_existing_labels(self):
        label_path = None
        
        possible_paths = [
            self.current_image_path.parent.parent / 'labels' / 'train' / (self.current_image_path.stem + '.txt'),
            self.current_image_path.parent.parent / 'labels' / 'val' / (self.current_image_path.stem + '.txt'),
            self.current_image_path.parent.parent / 'labels' / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels/train') / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels/val') / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels') / (self.current_image_path.stem + '.txt'),
        ]
        
        for p in possible_paths:
            if p.exists():
                label_path = p
                break
        
        if label_path and label_path.exists():
            h, w = self.current_image.shape[:2]
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        try:
                            cls = int(parts[0])
                            x_center = float(parts[1]) * w
                            y_center = float(parts[2]) * h
                            box_w = float(parts[3]) * w
                            box_h = float(parts[4]) * h
                            
                            x1 = int(x_center - box_w / 2)
                            y1 = int(y_center - box_h / 2)
                            x2 = int(x_center + box_w / 2)
                            y2 = int(y_center + box_h / 2)
                            
                            self.current_boxes.append({
                                'bbox': (x1, y1, x2, y2),
                                'class': cls
                            })
                        except ValueError:
                            pass
            logger.info(f"已加载标注: {label_path}")
                        
    def display_image(self):
        if self.current_image is None:
            return
            
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w < 10 or canvas_h < 10:
            self.root.after(100, self.display_image)
            return
            
        img_h, img_w = self.current_image.shape[:2]
        self.scale = min(canvas_w / img_w, canvas_h / img_h)
        
        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)
        
        self.offset_x = (canvas_w - new_w) // 2
        self.offset_y = (canvas_h - new_h) // 2
        
        display_img = self.current_image.copy()
        display_img = cv2.resize(display_img, (new_w, new_h))
        
        for box in self.current_boxes:
            x1, y1, x2, y2 = box['bbox']
            cls = box['class']
            
            scaled_x1 = int(x1 * self.scale)
            scaled_y1 = int(y1 * self.scale)
            scaled_x2 = int(x2 * self.scale)
            scaled_y2 = int(y2 * self.scale)
            
            class_name = self.classes[cls] if cls < len(self.classes) else f'class_{cls}'
            color = LabelingTool.BOX_COLORS.get(class_name, (128, 128, 128))
            cv2.rectangle(display_img, (scaled_x1, scaled_y1), (scaled_x2, scaled_y2), color, 2)
            
            label = self.classes[cls] if cls < len(self.classes) else f'class_{cls}'
            cv2.putText(display_img, label, (scaled_x1, scaled_y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        display_img = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        
        self.photo = ImageTk.PhotoImage(Image.fromarray(display_img))
        
        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.photo)
        
    def on_mouse_down(self, event):
        self.drawing = True
        self.start_point = (event.x, event.y)
        
    def on_mouse_move(self, event):
        if self.drawing and self.start_point:
            if self.temp_rect:
                self.canvas.delete(self.temp_rect)
            self.temp_rect = self.canvas.create_rectangle(
                self.start_point[0], self.start_point[1],
                event.x, event.y, outline='yellow', width=2
            )
            
    def on_mouse_up(self, event):
        if self.drawing and self.start_point:
            self.drawing = False
            
            if self.temp_rect:
                self.canvas.delete(self.temp_rect)
                self.temp_rect = None
                
            x1 = min(self.start_point[0], event.x)
            y1 = min(self.start_point[1], event.y)
            x2 = max(self.start_point[0], event.x)
            y2 = max(self.start_point[1], event.y)
            
            if x2 - x1 > 10 and y2 - y1 > 10:
                real_x1 = int((x1 - self.offset_x) / self.scale)
                real_y1 = int((y1 - self.offset_y) / self.scale)
                real_x2 = int((x2 - self.offset_x) / self.scale)
                real_y2 = int((y2 - self.offset_y) / self.scale)
                
                h, w = self.current_image.shape[:2]
                real_x1 = max(0, min(real_x1, w))
                real_y1 = max(0, min(real_y1, h))
                real_x2 = max(0, min(real_x2, w))
                real_y2 = max(0, min(real_y2, h))
                
                self.current_boxes.append({
                    'bbox': (real_x1, real_y1, real_x2, real_y2),
                    'class': self.current_class
                })
                
                self.display_image()
                self.update_box_list()
                
            self.start_point = None
            
    def on_right_click(self, event):
        canvas_x = event.x - self.offset_x
        canvas_y = event.y - self.offset_y
        
        real_x = canvas_x / self.scale
        real_y = canvas_y / self.scale
        
        for i, box in enumerate(self.current_boxes):
            x1, y1, x2, y2 = box['bbox']
            if x1 <= real_x <= x2 and y1 <= real_y <= y2:
                del self.current_boxes[i]
                self.display_image()
                self.update_box_list()
                break
                
    def on_box_select(self, event):
        selection = self.box_listbox.curselection()
        if selection:
            idx = selection[0]
            self.highlight_box(idx)
            
    def on_issue_select(self, event):
        pass
            
    def highlight_box(self, idx):
        self.display_image()
        
        if 0 <= idx < len(self.current_boxes):
            box = self.current_boxes[idx]
            x1, y1, x2, y2 = box['bbox']
            
            canvas_x1 = int(x1 * self.scale) + self.offset_x
            canvas_y1 = int(y1 * self.scale) + self.offset_y
            canvas_x2 = int(x2 * self.scale) + self.offset_x
            canvas_y2 = int(y2 * self.scale) + self.offset_y
            
            self.canvas.create_rectangle(
                canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                outline='cyan', width=3
            )
            
    def update_box_list(self):
        self.box_listbox.delete(0, tk.END)
        for i, box in enumerate(self.current_boxes):
            cls_name = self.classes[box['class']] if box['class'] < len(self.classes) else f'class_{box["class"]}'
            x1, y1, x2, y2 = box['bbox']
            self.box_listbox.insert(tk.END, f"{i+1}. {cls_name} ({x1},{y1})-({x2},{y2})")
            
    def update_issues_list(self):
        self.issues_listbox.delete(0, tk.END)
        if self.current_issues:
            for issue in self.current_issues:
                self.issues_listbox.insert(tk.END, f"行{issue['line']}: {issue['message']}")
        else:
            self.issues_listbox.insert(tk.END, "✓ 无问题")
            self.issues_listbox.config(fg='#44ff44')
            
    def delete_box(self):
        selection = self.box_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.current_boxes[idx]
            self.display_image()
            self.update_box_list()
            
    def clear_boxes(self):
        if messagebox.askyesno("确认", "确定要清空所有标注框吗?"):
            self.current_boxes = []
            self.display_image()
            self.update_box_list()
            
    def save_labels(self):
        if self.current_image is None or self.current_image_path is None:
            return
        
        existing_label_path = None
        possible_paths = [
            self.current_image_path.parent.parent / 'labels' / 'train' / (self.current_image_path.stem + '.txt'),
            self.current_image_path.parent.parent / 'labels' / 'val' / (self.current_image_path.stem + '.txt'),
            self.current_image_path.parent.parent / 'labels' / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels/train') / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels/val') / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels') / (self.current_image_path.stem + '.txt'),
        ]
        
        for p in possible_paths:
            if p.exists():
                existing_label_path = p
                break
        
        if existing_label_path:
            label_path = existing_label_path
        else:
            label_dir = Path('dataset/labels/train')
            label_dir.mkdir(parents=True, exist_ok=True)
            label_path = label_dir / (self.current_image_path.stem + '.txt')
        
        h, w = self.current_image.shape[:2]
        
        with open(label_path, 'w') as f:
            for box in self.current_boxes:
                x1, y1, x2, y2 = box['bbox']
                cls = box['class']
                
                x_center = ((x1 + x2) / 2) / w
                y_center = ((y1 + y2) / 2) / h
                box_w = (x2 - x1) / w
                box_h = (y2 - y1) / h
                
                f.write(f"{cls} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}\n")
        
        logger.info(f"标注已保存到: {label_path}")
        self.update_stats()
        
    def check_current_label(self):
        if self.current_image_path is None:
            return
        
        label_path = None
        possible_paths = [
            self.current_image_path.parent.parent / 'labels' / 'train' / (self.current_image_path.stem + '.txt'),
            self.current_image_path.parent.parent / 'labels' / 'val' / (self.current_image_path.stem + '.txt'),
            self.current_image_path.parent.parent / 'labels' / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels/train') / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels/val') / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels') / (self.current_image_path.stem + '.txt'),
        ]
        
        for p in possible_paths:
            if p.exists():
                label_path = p
                break
        
        if label_path:
            self.current_issues = check_label_file(label_path)
            self.update_issues_list()
        else:
            self.current_issues = []
            self.update_issues_list()
            
    def fix_current_label(self):
        if self.current_image_path is None:
            return
        
        if not self.current_issues:
            messagebox.showinfo("提示", "当前没有需要修复的问题")
            return
        
        label_path = None
        possible_paths = [
            self.current_image_path.parent.parent / 'labels' / 'train' / (self.current_image_path.stem + '.txt'),
            self.current_image_path.parent.parent / 'labels' / 'val' / (self.current_image_path.stem + '.txt'),
            self.current_image_path.parent.parent / 'labels' / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels/train') / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels/val') / (self.current_image_path.stem + '.txt'),
            Path('dataset/labels') / (self.current_image_path.stem + '.txt'),
        ]
        
        for p in possible_paths:
            if p.exists():
                label_path = p
                break
        
        if label_path:
            if fix_label_file(label_path, self.current_issues):
                messagebox.showinfo("成功", "标注修复成功！")
                self.load_existing_labels()
                self.display_image()
                self.update_box_list()
                self.check_current_label()
                
                if self.current_index in self.problem_images_info:
                    del self.problem_images_info[self.current_index]
                    self.update_problem_thumbnails()
            else:
                messagebox.showerror("错误", "标注修复失败")
                
    def check_all_labels(self):
        if not self.image_list:
            messagebox.showwarning("警告", "请先打开图片文件夹")
            return
        
        self.problem_images_info = {}
        problem_count = 0
        
        for i, img_path in enumerate(self.image_list):
            label_path = None
            possible_paths = [
                img_path.parent.parent / 'labels' / 'train' / (img_path.stem + '.txt'),
                img_path.parent.parent / 'labels' / 'val' / (img_path.stem + '.txt'),
                img_path.parent.parent / 'labels' / (img_path.stem + '.txt'),
                Path('dataset/labels/train') / (img_path.stem + '.txt'),
                Path('dataset/labels/val') / (img_path.stem + '.txt'),
                Path('dataset/labels') / (img_path.stem + '.txt'),
            ]
            
            for p in possible_paths:
                if p.exists():
                    label_path = p
                    break
            
            if label_path:
                issues = check_label_file(label_path)
                if issues:
                    self.problem_images_info[i] = {
                        'path': img_path,
                        'label_path': label_path,
                        'issues': issues
                    }
                    problem_count += 1
        
        self.update_problem_thumbnails()
        self.update_stats()
        
        if problem_count > 0:
            messagebox.showwarning("检查完成", f"发现 {problem_count} 个问题标注文件！\n问题图片已用红色高亮显示。")
        else:
            messagebox.showinfo("检查完成", "所有标注文件均正常，没有发现问题！")
            
    def fix_all_problem_labels(self):
        if not self.problem_images_info:
            messagebox.showinfo("提示", "没有需要修复的问题标注")
            return
        
        if not messagebox.askyesno("确认", f"确定要修复所有 {len(self.problem_images_info)} 个问题标注吗？"):
            return
        
        fixed_count = 0
        failed_count = 0
        
        for i, info in list(self.problem_images_info.items()):
            if fix_label_file(info['label_path'], info['issues']):
                fixed_count += 1
                del self.problem_images_info[i]
            else:
                failed_count += 1
        
        self.update_problem_thumbnails()
        self.update_stats()
        
        if self.current_image_path:
            self.load_image(self.current_index)
        
        messagebox.showinfo("修复完成", f"成功修复: {fixed_count}\n失败: {failed_count}")
        
    def update_problem_thumbnails(self):
        problem_indices = list(self.problem_images_info.keys())
        self.thumbnail_browser.set_problem_images(problem_indices)
        
    def prev_image(self):
        if self.current_index > 0:
            self.save_labels()
            self.thumbnail_browser.go_to_previous()
            
    def next_image(self):
        if self.current_index < len(self.image_list) - 1:
            self.save_labels()
            self.thumbnail_browser.go_to_next()
    
    def delete_current_file(self):
        if not self.current_image_path:
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除文件吗？\n{self.current_image_path.name}"):
            img_path = self.current_image_path
            
            img_dir = img_path.parent
            stem = img_path.stem
            
            possible_label_paths = [
                img_dir.parent / 'labels' / 'train' / f"{stem}.txt",
                img_dir.parent / 'labels' / 'val' / f"{stem}.txt",
                img_dir.parent / 'labels' / f"{stem}.txt",
            ]
            
            for label_path in possible_label_paths:
                if label_path.exists():
                    try:
                        label_path.unlink()
                        logger.info(f"已删除标注文件: {label_path}")
                    except Exception as e:
                        logger.error(f"删除标注文件失败: {e}")
            
            try:
                img_path.unlink()
                logger.info(f"已删除图片文件: {img_path}")
            except Exception as e:
                logger.error(f"删除图片文件失败: {e}")
                return
            
            if self.current_index in self.problem_images_info:
                del self.problem_images_info[self.current_index]
            
            self.image_list.pop(self.current_index)
            self.thumbnail_browser.load_images(self.image_list)
            self.update_problem_thumbnails()
            
            if self.image_list:
                if self.current_index >= len(self.image_list):
                    self.current_index = len(self.image_list) - 1
                self.thumbnail_browser.select_image(self.current_index)
            else:
                self.current_image = None
                self.current_image_path = None
                self.current_boxes = []
                self.canvas.delete('all')
                self.box_listbox.delete(0, tk.END)
                self.issues_listbox.delete(0, tk.END)
                self.info_label.config(text="请打开图片文件夹")
            
            self.update_stats()
            
    def on_key_press(self, event):
        if event.keysym == 'Delete':
            self.delete_current_file()
            return
        
        key = event.char
        if not key:
            return
        if key.isdigit() and 1 <= int(key) <= len(self.classes):
            self.class_var.set(int(key) - 1)
            self.current_class = int(key) - 1
        elif key.lower() == 'a':
            self.prev_image()
        elif key.lower() == 'd':
            self.next_image()
            
    def update_stats(self):
        total = len(self.image_list)
        labeled = 0
        
        label_dir = Path('dataset/labels')
        if label_dir.exists():
            for img_path in self.image_list:
                label_path = label_dir / (img_path.stem + '.txt')
                if label_path.exists():
                    labeled += 1
                    
        self.stats_label.config(text=f"已标注: {labeled}/{total}")
        self.problem_stats_label.config(text=f"问题标注: {len(self.problem_images_info)}")


def main():
    root = tk.Tk()
    app = LabelingTool(root)
    root.mainloop()


if __name__ == '__main__':
    main()
