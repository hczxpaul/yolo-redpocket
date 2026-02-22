import sys
import time
import threading
import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pyautogui
import mss
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import yaml

from config_utils import load_classes_from_config
from platform_adapter import get_platform_adapter
from ultralytics import YOLO

try:
    from ctypes import wintypes, windll
    HAS_WINTYPES = True
except ImportError:
    HAS_WINTYPES = False

try:
    import win32api
    import win32con
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class LoggerHandler(logging.Handler):
    """
    自定义日志处理器，用于将日志输出到Tkinter的文本控件中
    
    该处理器继承自logging.Handler，将日志记录格式化后安全地
    添加到指定的Tkinter ScrolledText或Text控件中，支持线程安全操作。
    
    Attributes:
        text_widget: Tkinter文本控件对象，用于显示日志内容
    """
    
    def __init__(self, text_widget):
        """
        初始化日志处理器
        
        Args:
            text_widget: Tkinter文本控件对象，日志将显示在此控件中
        """
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        """
        处理日志记录，将其添加到文本控件中
        
        使用text_widget.after()确保在Tkinter主线程中更新UI，
        避免线程安全问题。
        
        Args:
            record: logging.LogRecord对象，包含日志信息
        """
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tk.END)
        self.text_widget.after(0, append)


class ScreenCapture:
    def __init__(self):
        self.platform_adapter = get_platform_adapter()
        self.window_info = None
        self.window_rect = None
        self.window_title = ""
        self._mss_instance = None
    
    def _get_mss(self):
        if self._mss_instance is None:
            self._mss_instance = mss.mss()
        return self._mss_instance
    
    def reset_mss(self):
        if self._mss_instance is not None:
            try:
                self._mss_instance.close()
            except:
                pass
            self._mss_instance = None
        
    def find_wechat_window(self):
        """查找微信窗口（跨平台）"""
        window_info = self.platform_adapter.find_target_window('微信')
        if window_info:
            self.window_info = window_info
            self.window_title = window_info.get('title', '')
            rect = self.platform_adapter.get_window_rect(window_info)
            if rect:
                self.window_rect = rect
            return True
        return False
    
    def set_window_by_point(self, x, y):
        """通过坐标设置窗口（目前仅 Windows 支持）"""
        if self.platform_adapter.platform.startswith('win'):
            try:
                import win32gui
                hwnd = win32gui.WindowFromPoint((x, y))
                while win32gui.GetParent(hwnd) != 0:
                    hwnd = win32gui.GetParent(hwnd)
                
                if hwnd and win32gui.IsWindowVisible(hwnd):
                    self.window_info = {'hwnd': hwnd}
                    self.window_title = win32gui.GetWindowText(hwnd)
                    self.window_rect = win32gui.GetWindowRect(hwnd)
                    return True
            except Exception as e:
                logging.warning(f"通过坐标选择窗口失败: {e}")
        return False
    
    def get_window_rect(self):
        """获取窗口位置（跨平台）"""
        if self.window_info:
            rect = self.platform_adapter.get_window_rect(self.window_info)
            if rect:
                self.window_rect = rect
                return rect
        return None
    
    def capture_window(self):
        """捕获窗口内容（跨平台）"""
        if not self.window_info:
            return None
            
        rect = self.get_window_rect()
        if not rect:
            return None
            
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        
        if width <= 0 or height <= 0:
            return None
        
        try:
            sct = self._get_mss()
            monitor = {"top": top, "left": left, "width": width, "height": height}
            screenshot = sct.grab(monitor)
            im = np.array(screenshot)
            im = cv2.cvtColor(im, cv2.COLOR_BGRA2BGR)
            return im, rect
        except Exception as e:
            return None
    
    def bring_window_to_front(self):
        """将窗口带到前台（跨平台）"""
        if self.window_info:
            self.platform_adapter.bring_window_to_front(self.window_info)
    
    def set_always_on_top(self, enable=True):
        """设置窗口置顶（目前仅 Windows 支持）"""
        if self.window_info and self.platform_adapter.platform.startswith('win'):
            try:
                import win32gui
                import win32con
                hwnd = self.window_info.get('hwnd')
                if hwnd:
                    if enable:
                        win32gui.SetWindowPos(
                            hwnd,
                            win32con.HWND_TOPMOST,
                            0, 0, 0, 0,
                            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                        )
                    else:
                        win32gui.SetWindowPos(
                            hwnd,
                            win32con.HWND_NOTOPMOST,
                            0, 0, 0, 0,
                            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                        )
            except Exception as e:
                pass


class RedPocketDetector:
    """
    红包检测器类，使用YOLO模型进行目标检测
    
    Attributes:
        model: YOLO模型实例
        model_path: 模型文件路径
        classes: 类别名称列表
        device: 运行设备（cpu或cuda）
        logger: 日志记录器
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
    
    def __init__(self, model_path=None, logger=None, config_path='dataset.yaml'):
        """
        初始化红包检测器
        
        Args:
            model_path: 模型文件路径，可选
            logger: 日志记录器，可选
            config_path: 数据集配置文件路径，默认为dataset.yaml
        """
        self.model = None
        self.model_path = model_path
        self.device = 'cpu'
        self.logger = logger or logging.getLogger('RedPocketDetector')
        self.classes = load_classes_from_config(config_path, self.logger)
        
    def _get_best_device(self):
        """
        自动检测并返回最佳可用设备
        优先级: CUDA > MPS > RKNPU > CPU
        """
        import torch
        
        # 1. 检查 NVIDIA CUDA
        if torch.cuda.is_available():
            self.logger.info(f"检测到 CUDA 设备: {torch.cuda.get_device_name(0)}")
            return 'cuda'
        
        # 2. 检查 Apple MPS (Apple Silicon)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.logger.info("检测到 Apple MPS 设备")
            return 'mps'
        
        # 3. 检查 Rockchip RKNPU (RK3588/RK3568 等)
        try:
            import rknnlite
            self.logger.info("检测到 Rockchip RKNPU 设备")
            return 'rknpu'
        except ImportError:
            pass
        
        # 4. 回退到 CPU
        self.logger.warning("未检测到可用的硬件加速设备，使用 CPU")
        return 'cpu'

    def load_model(self, model_path):
        try:
            import torch
            self.device = self._get_best_device()
            self.logger.info(f"使用设备: {self.device}")
            
            self.model = YOLO(model_path)
            self.model.to(self.device)
            self.model_path = model_path
            return True
        except ImportError as e:
            self.logger.error(f"导入依赖库失败: {e}，请确保已安装torch和ultralytics")
            return False
        except FileNotFoundError as e:
            self.logger.error(f"模型文件不存在: {model_path}")
            return False
        except RuntimeError as e:
            self.logger.error(f"模型加载或设备切换失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"加载模型失败: {e}")
            return False
    
    def detect(self, image, conf_threshold=0.5):
        if self.model is None:
            return []
        
        results = self.model(image, conf=conf_threshold, verbose=False, device=self.device)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()
                cls = int(box.cls[0].cpu().numpy())
                detections.append({
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'confidence': float(conf),
                    'class': cls,
                    'class_name': self.classes[cls] if cls < len(self.classes) else f'class_{cls}'
                })
        
        return detections
    
    def find_red_packets(self, detections):
        return [d for d in detections if d['class_name'] == 'red_packet']
    
    def find_open_button(self, detections):
        return [d for d in detections if d['class_name'] == 'open_button']
    
    def find_back_button(self, detections):
        return [d for d in detections if d['class_name'] == 'back_button']
    
    def find_close_button(self, detections):
        return [d for d in detections if d['class_name'] == 'close_button']
    
    def find_play_button(self, detections):
        return [d for d in detections if d['class_name'] == 'play_button']


class AutoClicker:
    def __init__(self, screen_capture):
        self.screen_capture = screen_capture
        self.click_delay = 0.02
        
    def click_at_position(self, x, y, relative_to_window=True):
        if relative_to_window and self.screen_capture.window_rect:
            window_x, window_y, _, _ = self.screen_capture.window_rect
            x += window_x
            y += window_y
        
        try:
            win32api.SetCursorPos((x, y))
            time.sleep(0.01)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            time.sleep(0.01)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            time.sleep(self.click_delay)
            return True
        except Exception as e:
            try:
                pyautogui.click(x, y)
                time.sleep(self.click_delay)
                return True
            except:
                return False
    
    def click_center(self, bbox, relative_to_window=True):
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        success = self.click_at_position(center_x, center_y, relative_to_window)
        return center_x, center_y, success


class DataLabeler:
    def __init__(self, data_dir='dataset'):
        self.data_dir = Path(data_dir)
        self.images_dir = self.data_dir / 'images'
        self.labels_dir = self.data_dir / 'labels'
        self.current_image = None
        self.current_boxes = []
        
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
    
    def save_image(self, image, prefix='capture'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{prefix}_{timestamp}.png'
        filepath = self.images_dir / filename
        cv2.imwrite(str(filepath), image)
        return filepath
    
    def save_label(self, image_path, boxes, image_shape):
        label_path = self.labels_dir / (image_path.stem + '.txt')
        h, w = image_shape[:2]
        
        with open(label_path, 'w') as f:
            for box in boxes:
                x1, y1, x2, y2 = box['bbox']
                class_id = box['class']
                
                x_center = ((x1 + x2) / 2) / w
                y_center = ((y1 + y2) / 2) / h
                width = (x2 - x1) / w
                height = (y2 - y1) / h
                
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
        
        return label_path


class RedPocketApp:
    def __init__(self, root):
        self.root = root
        self.root.title("微信红包自动抢夺器 - YOLO版")
        self.root.geometry("1600x1000")
        self.root.minsize(1400, 900)
        self.root.configure(bg='#f0f0f0')
        
        self.is_running = False
        self.auto_grab_enabled = False
        self.monitor_thread = None
        self.current_detections = []
        self.current_image = None
        self.preview_scale = 1.0
        self.preview_offset_x = 0
        self.preview_offset_y = 0
        self.is_handling_red_packet = False
        
        self.is_paused = False
        self.last_pause_time = 0
        self.pause_debounce_ms = 500
        self.hotkey_thread = None
        self.hotkey_id = None
        self.last_f9_state = False
        
        self.setup_logging()
        
        self.screen_capture = ScreenCapture()
        self.detector = RedPocketDetector(logger=self.logger)
        self.auto_clicker = AutoClicker(self.screen_capture)
        self.data_labeler = DataLabeler()
        
        self.setup_ui()
        self.load_default_model()
        self.setup_hotkeys()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_logging(self):
        self.logger = logging.getLogger('RedPocketApp')
        self.logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.Frame(main_frame, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_frame.pack_propagate(False)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_control_panel(left_frame)
        self.setup_preview_panel(right_frame)
        
    def setup_control_panel(self, parent):
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Microsoft YaHei', 12, 'bold'))
        style.configure('Status.TLabel', font=('Microsoft YaHei', 10))
        
        title_label = ttk.Label(parent, text="控制面板", style='Title.TLabel')
        title_label.pack(pady=(0, 10))
        
        status_frame = ttk.LabelFrame(parent, text="状态信息", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="状态: 未启动", style='Status.TLabel')
        self.status_label.pack(anchor=tk.W)
        
        self.model_label = ttk.Label(status_frame, text="模型: 未加载", style='Status.TLabel')
        self.model_label.pack(anchor=tk.W)
        
        control_frame = ttk.LabelFrame(parent, text="主控制", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        monitor_frame = ttk.Frame(control_frame)
        monitor_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.start_btn = ttk.Button(monitor_frame, text="开始监控", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        
        self.stop_btn = ttk.Button(monitor_frame, text="停止监控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        auto_frame = ttk.Frame(control_frame)
        auto_frame.pack(fill=tk.X)
        
        self.auto_btn = ttk.Button(auto_frame, text="开始抢红包", command=self.toggle_auto_grab, state=tk.DISABLED)
        self.auto_btn.pack(fill=tk.X)
        
        self.auto_status_label = ttk.Label(auto_frame, text="抢红包: 未启动", foreground='gray')
        self.auto_status_label.pack(fill=tk.X, pady=(5, 0))
        
        window_frame = ttk.LabelFrame(control_frame, text="窗口选择", padding="10")
        window_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.select_window_btn = ttk.Button(window_frame, text="点击选择窗口", command=self.start_window_selection)
        self.select_window_btn.pack(fill=tk.X)
        
        self.window_info_label = ttk.Label(window_frame, text="未选择窗口", wraplength=180)
        self.window_info_label.pack(fill=tk.X, pady=(5, 0))
        
        model_frame = ttk.LabelFrame(parent, text="模型管理", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        load_model_btn = ttk.Button(model_frame, text="加载模型", command=self.load_model)
        load_model_btn.pack(fill=tk.X)
        
        conf_frame = ttk.Frame(model_frame)
        conf_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(conf_frame, text="置信度阈值:").pack(side=tk.LEFT)
        self.conf_var = tk.DoubleVar(value=0.5)
        self.conf_scale = ttk.Scale(conf_frame, from_=0.1, to=1.0, variable=self.conf_var, orient=tk.HORIZONTAL)
        self.conf_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.conf_label = ttk.Label(conf_frame, text="0.50")
        self.conf_label.pack(side=tk.LEFT, padx=(5, 0))
        self.conf_scale.configure(command=self.update_conf_label)
        
        label_frame = ttk.LabelFrame(parent, text="数据标注", padding="10")
        label_frame.pack(fill=tk.X, pady=(0, 10))
        
        capture_btn = ttk.Button(label_frame, text="截图保存", command=self.capture_and_save)
        capture_btn.pack(fill=tk.X)
        
        self.label_mode_var = tk.BooleanVar(value=False)
        label_mode_cb = ttk.Checkbutton(label_frame, text="标注模式", variable=self.label_mode_var)
        label_mode_cb.pack(fill=tk.X, pady=(10, 0))
        
        train_frame = ttk.LabelFrame(parent, text="模型训练", padding="10")
        train_frame.pack(fill=tk.X, pady=(0, 10))
        
        train_btn = ttk.Button(train_frame, text="训练模型", command=self.train_model)
        train_btn.pack(fill=tk.X)
        
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        log_handler = LoggerHandler(self.log_text)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(log_handler)
        
        help_frame = ttk.LabelFrame(parent, text="快捷键说明", padding="10")
        help_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(help_frame, text="F9 - 暂停/恢复抢红包功能", font=('Microsoft YaHei', 9)).pack(anchor=tk.W)
        
    def setup_preview_panel(self, parent):
        preview_frame = ttk.LabelFrame(parent, text="实时预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg='black', highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        self.preview_canvas.bind('<Button-1>', self.on_canvas_click)
        self.preview_canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.preview_canvas.bind('<ButtonRelease-1>', self.on_canvas_release)
        
        self.drawing_box = False
        self.box_start = None
        self.temp_rect = None
        
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.detection_info_label = ttk.Label(info_frame, text="检测结果: 无")
        self.detection_info_label.pack(side=tk.LEFT)
        
    def update_conf_label(self, value):
        self.conf_label.configure(text=f"{float(value):.2f}")
        
    def load_default_model(self):
        default_model = Path('models/best.pt')
        if default_model.exists():
            if self.detector.load_model(str(default_model)):
                self.model_label.configure(text=f"模型: {default_model.name}")
                self.logger.info(f"已加载默认模型: {default_model}")
                
    def load_model(self):
        file_path = filedialog.askopenfilename(
            title="选择YOLO模型文件",
            filetypes=[("PyTorch模型", "*.pt"), ("所有文件", "*.*")]
        )
        if file_path:
            if self.detector.load_model(file_path):
                self.model_label.configure(text=f"模型: {Path(file_path).name}")
                self.logger.info(f"已加载模型: {file_path}")
            else:
                messagebox.showerror("错误", "模型加载失败")
                
    def start_window_selection(self):
        self.select_window_btn.configure(text="请点击目标窗口...", state=tk.DISABLED)
        self.root.config(cursor="crosshair")
        
        self.selection_window = tk.Toplevel(self.root)
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-topmost', True)
        self.selection_window.attributes('-alpha', 0.1)
        self.selection_window.config(bg='black')
        
        self.selection_window.bind('<Button-1>', self.on_selection_click)
        self.selection_window.bind('<Escape>', lambda e: self.cancel_selection())
        
        instruction_label = tk.Label(
            self.selection_window,
            text="请点击要监控的窗口\n按 ESC 取消",
            font=('Microsoft YaHei', 24, 'bold'),
            fg='white',
            bg='black'
        )
        instruction_label.place(relx=0.5, rely=0.5, anchor='center')
        
        self.logger.info("请点击要监控的窗口...")
    
    def on_selection_click(self, event):
        x = event.x_root
        y = event.y_root
        
        self.cancel_selection()
        
        if self.screen_capture.set_window_by_point(x, y):
            self.screen_capture.reset_mss()
            rect = self.screen_capture.get_window_rect()
            title = self.screen_capture.window_title
            self.window_info_label.configure(text=f"{title}\n{rect[2]-rect[0]}x{rect[3]-rect[1]}")
            self.logger.info(f"已选择窗口: {title} {rect}")
        else:
            self.window_info_label.configure(text="窗口选择失败")
            self.logger.warning("窗口选择失败")
    
    def cancel_selection(self):
        if hasattr(self, 'selection_window'):
            self.selection_window.destroy()
        self.select_window_btn.configure(text="点击选择窗口", state=tk.NORMAL)
        self.root.config(cursor="")
            
    def start_monitoring(self):
        if not self.screen_capture.window_info:
            messagebox.showwarning("警告", "请先选择要监控的窗口")
            return
                
        if self.detector.model is None:
            messagebox.showwarning("警告", "请先加载YOLO模型")
            return
            
        self.is_running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.auto_btn.configure(state=tk.NORMAL)
        self.status_label.configure(text="状态: 监控中...")
        
        self.logger.info("将微信窗口置顶...")
        self.screen_capture.bring_window_to_front()
        time.sleep(0.1)
        self.screen_capture.set_always_on_top(True)
        self.logger.info("微信窗口已设置为置顶")
        
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("开始监控...")
        
    def stop_monitoring(self):
        self.is_running = False
        self.auto_grab_enabled = False
        self.is_paused = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.auto_btn.configure(state=tk.DISABLED, text="开始抢红包")
        self.auto_status_label.configure(text="抢红包: 未启动", foreground='gray')
        self.status_label.configure(text="状态: 已停止")
        
        self.logger.info("取消微信窗口置顶...")
        self.screen_capture.set_always_on_top(False)
        self.logger.info("微信窗口已取消置顶")
        
        self.screen_capture.reset_mss()
        
        self.logger.info("停止监控")
    
    def toggle_auto_grab(self):
        if self.auto_grab_enabled:
            self.auto_grab_enabled = False
            self.is_paused = False
            self.auto_btn.configure(text="开始抢红包")
            self.auto_status_label.configure(text="抢红包: 已暂停", foreground='orange')
            self.logger.info("抢红包功能已暂停")
        else:
            self.auto_grab_enabled = True
            self.is_paused = False
            self.auto_btn.configure(text="暂停抢红包")
            self.auto_status_label.configure(text="抢红包: 运行中", foreground='green')
            self.logger.info("抢红包功能已启动")
    
    def setup_hotkeys(self):
        self.root.bind('<F9>', lambda e: self.toggle_pause())
        self.root.bind('<Key-F9>', lambda e: self.toggle_pause())
        self.logger.info("F9窗口内快捷键已绑定，用于暂停/恢复抢红包功能")
        
        try:
            import ctypes
            from ctypes import wintypes
            
            VK_F9 = 0x78
            MOD_NOREPEAT = 0x4000
            
            HOTKEY_ID = 1
            WM_HOTKEY = 0x0312
            
            if ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, 0, VK_F9):
                self.logger.info("F9全局快捷键已注册")
                
                def message_loop():
                    msg = wintypes.MSG()
                    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
                        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                            self.root.after(0, self.toggle_pause)
                        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
                
                self.hotkey_thread = threading.Thread(target=message_loop, daemon=True)
                self.hotkey_thread.start()
                self.logger.info("全局热键消息循环已启动")
            else:
                self.logger.warning("F9全局快捷键注册失败，尝试备用方案")
                self.setup_backup_hotkey()
        except Exception as e:
            self.logger.warning(f"设置全局快捷键失败: {e}，使用备用方案")
            self.setup_backup_hotkey()
    
    def setup_backup_hotkey(self):
        self.last_f9_state = False
        if HAS_WIN32:
            try:
                VK_F9 = 0x78
                
                def check_global_key():
                    if not self.root.winfo_exists():
                        return
                    
                    current_state = (win32api.GetAsyncKeyState(VK_F9) & 0x8000) != 0
                    
                    if current_state and not self.last_f9_state:
                        self.toggle_pause()
                    
                    self.last_f9_state = current_state
                    self.root.after(50, check_global_key)
                
                self.root.after(100, check_global_key)
                self.logger.info("F9备用全局快捷键检查已启动")
            except Exception as e:
                self.logger.warning(f"设置备用全局快捷键检查失败: {e}")
        else:
            self.logger.info("非Windows平台，备用全局快捷键不可用，仅支持窗口内快捷键")
    
    def on_closing(self):
        if HAS_WINTYPES:
            try:
                import ctypes
                HOTKEY_ID = 1
                ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
                self.logger.info("热键已注销")
            except:
                pass
        self.root.destroy()
    
    def toggle_pause(self):
        current_time = time.time() * 1000
        
        if current_time - self.last_pause_time < self.pause_debounce_ms:
            return
        
        self.last_pause_time = current_time
        
        if not self.auto_grab_enabled:
            self.logger.info("抢红包未启动，忽略快捷键")
            return
        
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.logger.info("抢红包功能已暂停 (按F9恢复)")
            self.root.after(0, lambda: self.auto_status_label.configure(text="抢红包: 已暂停 (F9)", foreground='orange'))
        else:
            self.logger.info("抢红包功能已恢复")
            self.root.after(0, lambda: self.auto_status_label.configure(text="抢红包: 运行中", foreground='green'))
    
    def recheck_and_verify_button(self, button_type, delay_seconds, find_method, current_target):
        self.logger.info(f"{button_type}检测到，先延时{delay_seconds}秒钟...")
        time.sleep(delay_seconds)
        
        self.logger.info(f"延时结束，重新检测是否还有{button_type}...")
        result = self.screen_capture.capture_window()
        if not result:
            self.logger.warning("屏幕捕获失败，继续使用原检测结果")
            return True, current_target
        
        image, _ = result
        new_detections = self.detector.detect(image, self.conf_var.get())
        new_buttons = find_method(new_detections)
        
        if not new_buttons:
            self.logger.info(f"重新检测未发现{button_type}，终止点击")
            return False, None
        else:
            self.logger.info(f"重新检测仍发现{button_type}，继续点击")
            return True, new_buttons[0]
        
    def monitor_loop(self):
        flash_state = False
        last_flash = time.time()
        last_fps_time = time.time()
        frame_count = 0
        fps = 0
        inference_time = 0
        
        while self.is_running:
            loop_start = time.time()
            
            try:
                capture_start = time.time()
                result = self.screen_capture.capture_window()
                capture_time = time.time() - capture_start
                
                if result is None:
                    self.logger.warning("无法捕获窗口")
                    time.sleep(0.3)
                    continue
                    
                image, rect = result
                self.current_image = image.copy()
                
                conf_threshold = self.conf_var.get()
                
                infer_start = time.time()
                detections = self.detector.detect(image, conf_threshold)
                inference_time = time.time() - infer_start
                
                self.current_detections = detections
                
                display_image = self.draw_monitoring_overlay(image, detections, flash_state, fps, inference_time, capture_time)
                self.update_preview(display_image, detections)
                
                frame_count += 1
                if time.time() - last_fps_time >= 1.0:
                    fps = frame_count / (time.time() - last_fps_time)
                    frame_count = 0
                    last_fps_time = time.time()
                
                if time.time() - last_flash > 0.5:
                    flash_state = not flash_state
                    last_flash = time.time()
                
                if self.auto_grab_enabled and not self.is_paused:
                    open_buttons = self.detector.find_open_button(detections)
                    
                    if open_buttons:
                        self.logger.info(f"[最高优先级] 检测到开红包按钮! 置信度: {open_buttons[0]['confidence']:.2f}")
                        self.screen_capture.bring_window_to_front()
                        time.sleep(0.01)
                        
                        self.screen_capture.get_window_rect()
                        
                        click_start = time.time()
                        click_count = 0
                        bbox = open_buttons[0]['bbox']
                        
                        while time.time() - click_start < 0.2:
                            _, _, success = self.auto_clicker.click_center(bbox)
                            if success:
                                click_count += 1
                            time.sleep(0.01)
                        
                        self.logger.info(f"开红包按钮连续点击 {click_count} 次!")
                        time.sleep(0.3)
                        
                        import threading
                        threading.Thread(
                            target=self.return_to_chat,
                            daemon=True
                        ).start()
                    elif not self.is_handling_red_packet:
                        red_packets = self.detector.find_red_packets(detections)
                        
                        if red_packets:
                            self.logger.info(f"[第二优先级] 检测到红包! 置信度: {red_packets[0]['confidence']:.2f}")
                            self.is_handling_red_packet = True
                            import threading
                            threading.Thread(
                                target=self.process_red_packet_simple,
                                args=(red_packets[0],),
                                daemon=True
                            ).start()
                        else:
                            back_buttons = self.detector.find_back_button(detections)
                            close_buttons = self.detector.find_close_button(detections)
                            
                            if back_buttons or close_buttons:
                                target_button = back_buttons[0] if back_buttons else close_buttons[0]
                                button_type = "返回按钮" if back_buttons else "关闭按钮"
                                self.logger.info(f"[第三优先级] 检测到{button_type}! 置信度: {target_button['confidence']:.2f}")
                                self.screen_capture.bring_window_to_front()
                                
                                if button_type == "关闭按钮":
                                    should_click, target_button = self.recheck_and_verify_button(
                                        button_type="关闭按钮",
                                        delay_seconds=2,
                                        find_method=self.detector.find_close_button,
                                        current_target=target_button
                                    )
                                elif button_type == "返回按钮":
                                    should_click, target_button = self.recheck_and_verify_button(
                                        button_type="返回按钮",
                                        delay_seconds=0.2,
                                        find_method=self.detector.find_back_button,
                                        current_target=target_button
                                    )
                                
                                if not should_click:
                                    continue
                                
                                time.sleep(0.01)
                                
                                self.screen_capture.get_window_rect()
                                
                                _, _, success = self.auto_clicker.click_center(target_button['bbox'])
                                if success:
                                    self.logger.info(f"已点击{button_type}")
                                time.sleep(0.1)
                
                loop_time = time.time() - loop_start
                sleep_time = max(0, 0.03 - loop_time)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(0.3)
    
    def draw_monitoring_overlay(self, image, detections, flash_state, fps=0, inference_time=0, capture_time=0):
        display = image.copy()
        h, w = display.shape[:2]
        
        ref_w, ref_h = 2560, 1440
        scale_factor = min(w / ref_w, h / ref_h)
        
        scale_boost = 2.0
        
        if self.auto_grab_enabled and not self.is_paused:
            overlay_color = (0, 255, 0)
            status_text = "AUTO GRAB"
        elif self.auto_grab_enabled and self.is_paused:
            overlay_color = (0, 165, 255)
            status_text = "PAUSED"
        else:
            overlay_color = (255, 200, 0)
            status_text = "MONITORING"
        
        cv2.rectangle(display, (0, 0), (w, max(3, int(3 * scale_boost))), overlay_color, -1)
        cv2.rectangle(display, (0, h - max(3, int(3 * scale_boost))), (w, h), overlay_color, -1)
        cv2.rectangle(display, (0, 0), (max(3, int(3 * scale_boost)), h), overlay_color, -1)
        cv2.rectangle(display, (w - max(3, int(3 * scale_boost)), 0), (w, h), overlay_color, -1)
        
        font_scale_status = 2.0 * scale_factor * scale_boost
        font_scale_timestamp = 1.8 * scale_factor * scale_boost
        font_scale_perf = 1.2 * scale_factor * scale_boost
        font_scale_label = 0.5 * scale_factor * scale_boost
        thickness_status = int(4 * scale_factor * scale_boost)
        thickness_timestamp = int(4 * scale_factor * scale_boost)
        thickness_perf = int(3 * scale_factor * scale_boost)
        thickness_label = int(2 * scale_factor * scale_boost)
        thickness_box = max(2, int(2 * scale_factor * scale_boost))
        
        y_offset_status = int(60 * scale_factor * scale_boost)
        y_offset_perf = int(30 * scale_factor * scale_boost)
        label_offset = int(10 * scale_factor * scale_boost)
        
        cv2.putText(display, status_text, (int(20 * scale_factor * scale_boost), y_offset_status), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale_status, overlay_color, thickness_status)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        (ts_w, ts_h), _ = cv2.getTextSize(timestamp, cv2.FONT_HERSHEY_SIMPLEX, font_scale_timestamp, thickness_timestamp)
        cv2.putText(display, timestamp, (int(w - ts_w - int(20 * scale_factor * scale_boost)), y_offset_status),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale_timestamp, overlay_color, thickness_timestamp)
        
        perf_text = f"FPS: {fps:.1f} | Capture: {capture_time*1000:.0f}ms | Inference: {inference_time*1000:.0f}ms"
        (pt_w, pt_h), _ = cv2.getTextSize(perf_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale_perf, thickness_perf)
        cv2.putText(display, perf_text, (int(20 * scale_factor * scale_boost), h - y_offset_perf),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale_perf, (255, 255, 255), thickness_perf)
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            class_name = det['class_name']
            
            color = RedPocketDetector.BOX_COLORS.get(class_name, (128, 128, 128))
            
            cv2.rectangle(display, (x1, y1), (x2, y2), color, thickness_box)
            
            label = f"{class_name}: {conf:.2f}"
            cv2.putText(display, label, (x1, y1 - label_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale_label, color, thickness_label)
        
        return display
                
    def process_red_packet_simple(self, red_packet):
        try:
            if not self.auto_grab_enabled:
                self.logger.info("抢红包已暂停，跳过此红包")
                return
            
            self.logger.info(f"检测到红包! 置信度: {red_packet['confidence']:.2f}")
            
            self.screen_capture.bring_window_to_front()
            time.sleep(0.03)
            
            self.screen_capture.get_window_rect()
            
            bbox = red_packet['bbox']
            center_x, center_y, success = self.auto_clicker.click_center(bbox)
            
            if success:
                self.logger.info(f"点击红包位置: ({center_x}, {center_y})")
            else:
                self.logger.error(f"点击红包失败: ({center_x}, {center_y})")
            
            time.sleep(0.1)
            self.logger.info("红包已点击，等待监控循环检测开红包按钮...")
        except Exception as e:
            self.logger.error(f"处理红包出错: {e}")
        finally:
            self.is_handling_red_packet = False
    

    
    def return_to_chat(self, max_attempts=10):
        """
        尝试返回群聊界面
        
        Args:
            max_attempts: 最大尝试次数，默认为10次
        """
        if not self.auto_grab_enabled:
            self.logger.info("抢红包已暂停，跳过返回群聊")
            return
        
        for attempt in range(max_attempts):
            if not self.auto_grab_enabled:
                self.logger.info("抢红包已暂停，停止返回")
                return
            result = self.screen_capture.capture_window()
            if not result:
                time.sleep(0.1)
                continue
                
            current_image, _ = result
            
            lower_conf = max(0.3, self.conf_var.get() - 0.2)
            current_detections = self.detector.detect(current_image, lower_conf)
            
            self.logger.info(f"检测到 {len(current_detections)} 个目标")
            for det in current_detections:
                self.logger.info(f"  - {det['class_name']}: {det['confidence']:.2f}")
            
            red_packets = self.detector.find_red_packets(current_detections)
            if red_packets:
                self.logger.info("已返回群聊")
                return
            
            back_buttons = self.detector.find_back_button(current_detections)
            if back_buttons:
                self.logger.info(f"检测到返回按钮，点击返回")
                self.screen_capture.bring_window_to_front()
                time.sleep(0.05)
                
                self.screen_capture.get_window_rect()
                
                _, _, success = self.auto_clicker.click_center(back_buttons[0]['bbox'])
                if success:
                    self.logger.info("已点击返回按钮")
                time.sleep(0.1)
                continue
            
            close_buttons = self.detector.find_close_button(current_detections)
            if close_buttons:
                self.logger.info(f"检测到关闭按钮，点击关闭")
                self.screen_capture.bring_window_to_front()
                time.sleep(0.05)
                
                self.screen_capture.get_window_rect()
                
                _, _, success = self.auto_clicker.click_center(close_buttons[0]['bbox'])
                if success:
                    self.logger.info("已点击关闭按钮")
                time.sleep(0.1)
                continue
            
            self.logger.info(f"未检测到返回/关闭按钮 (尝试 {attempt + 1}/{max_attempts})")
            time.sleep(0.1)
        
        self.logger.warning("多次尝试后仍未返回群聊，继续监控...")
    
    def update_preview(self, image, detections):
        display_image = image.copy()
        
        h, w = display_image.shape[:2]
        canvas_w = self.preview_canvas.winfo_width()
        canvas_h = self.preview_canvas.winfo_height()
        
        if canvas_w < 10 or canvas_h < 10:
            return
            
        self.preview_scale = min(canvas_w / w, canvas_h / h)
        new_w, new_h = int(w * self.preview_scale), int(h * self.preview_scale)
        
        self.preview_offset_x = (canvas_w - new_w) // 2
        self.preview_offset_y = (canvas_h - new_h) // 2
        
        display_image = cv2.resize(display_image, (new_w, new_h))
        display_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        
        self.photo = ImageTk.PhotoImage(Image.fromarray(display_image))
        
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            self.preview_offset_x, self.preview_offset_y,
            image=self.photo, anchor=tk.NW
        )
        
        self.detection_info_label.configure(
            text=f"检测结果: {len(detections)} 个目标"
        )
        
    def capture_and_save(self):
        if self.current_image is not None:
            filepath = self.data_labeler.save_image(self.current_image)
            self.logger.info(f"截图已保存: {filepath}")
            messagebox.showinfo("成功", f"截图已保存到:\n{filepath}")
        else:
            result = self.screen_capture.capture_window()
            if result:
                image, _ = result
                filepath = self.data_labeler.save_image(image)
                self.logger.info(f"截图已保存: {filepath}")
                messagebox.showinfo("成功", f"截图已保存到:\n{filepath}")
            else:
                messagebox.showwarning("警告", "无法捕获窗口")
                
    def on_canvas_click(self, event):
        if self.label_mode_var.get():
            self.drawing_box = True
            self.box_start = (event.x, event.y)
            
    def on_canvas_drag(self, event):
        if self.drawing_box and self.box_start:
            if self.temp_rect:
                self.preview_canvas.delete(self.temp_rect)
            self.temp_rect = self.preview_canvas.create_rectangle(
                self.box_start[0], self.box_start[1],
                event.x, event.y, outline='red', width=2
            )
            
    def on_canvas_release(self, event):
        if self.drawing_box and self.box_start and self.label_mode_var.get():
            self.drawing_box = False
            
            if self.temp_rect:
                self.preview_canvas.delete(self.temp_rect)
                self.temp_rect = None
                
            x1, y1 = self.box_start
            x2, y2 = event.x, event.y
            
            if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:
                class_window = tk.Toplevel(self.root)
                class_window.title("选择类别")
                class_window.geometry("400x500")
                class_window.transient(self.root)
                class_window.grab_set()
                
                ttk.Label(class_window, text="选择目标类别:").pack(pady=10)
                
                class_var = tk.StringVar(value='0')
                for i, cls in enumerate(self.detector.classes):
                    ttk.Radiobutton(class_window, text=cls, value=str(i), 
                                   variable=class_var).pack(anchor=tk.W, padx=30, pady=5)
                
                def save_annotation():
                    self.save_box_annotation(x1, y1, x2, y2, int(class_var.get()))
                    class_window.destroy()
                    
                ttk.Button(class_window, text="保存", command=save_annotation).pack(pady=10)
                
            self.box_start = None
            
    def save_box_annotation(self, x1, y1, x2, y2, class_id):
        if self.current_image is not None:
            filepath = self.data_labeler.save_image(self.current_image)
            
            h, w = self.current_image.shape[:2]
            
            canvas_w = self.preview_canvas.winfo_width()
            canvas_h = self.preview_canvas.winfo_height()
            
            preview_scale = min(canvas_w / w, canvas_h / h)
            preview_offset_x = (canvas_w - int(w * preview_scale)) // 2
            preview_offset_y = (canvas_h - int(h * preview_scale)) // 2
            
            real_x1 = int((x1 - preview_offset_x) / preview_scale)
            real_y1 = int((y1 - preview_offset_y) / preview_scale)
            real_x2 = int((x2 - preview_offset_x) / preview_scale)
            real_y2 = int((y2 - preview_offset_y) / preview_scale)
            
            real_x1 = max(0, min(real_x1, w))
            real_y1 = max(0, min(real_y1, h))
            real_x2 = max(0, min(real_x2, w))
            real_y2 = max(0, min(real_y2, h))
            
            if real_x1 > real_x2:
                real_x1, real_x2 = real_x2, real_x1
            if real_y1 > real_y2:
                real_y1, real_y2 = real_y2, real_y1
            
            box = {
                'bbox': (real_x1, real_y1, real_x2, real_y2),
                'class': class_id
            }
            
            self.data_labeler.save_label(filepath, [box], self.current_image.shape)
            self.logger.info(f"标注已保存: {filepath.stem}")
            
    def train_model(self):
        train_window = tk.Toplevel(self.root)
        train_window.title("模型训练配置")
        train_window.geometry("600x600")
        train_window.transient(self.root)
        
        ttk.Label(train_window, text="数据集路径:").pack(pady=(20, 5))
        data_path_var = tk.StringVar(value='dataset.yaml')
        data_path_entry = ttk.Entry(train_window, textvariable=data_path_var, width=40)
        data_path_entry.pack()
        
        ttk.Label(train_window, text="训练轮数:").pack(pady=(10, 5))
        epochs_var = tk.IntVar(value=200)
        ttk.Entry(train_window, textvariable=epochs_var, width=40).pack()
        
        ttk.Label(train_window, text="批次大小:").pack(pady=(10, 5))
        batch_var = tk.IntVar(value=16)
        ttk.Entry(train_window, textvariable=batch_var, width=40).pack()
        
        ttk.Label(train_window, text="图像尺寸:").pack(pady=(10, 5))
        imgsz_var = tk.IntVar(value=800)
        ttk.Entry(train_window, textvariable=imgsz_var, width=40).pack()
        
        ttk.Label(train_window, text="初始学习率:").pack(pady=(10, 5))
        lr0_var = tk.DoubleVar(value=0.0008)
        ttk.Entry(train_window, textvariable=lr0_var, width=40).pack()
        
        ttk.Label(train_window, text="最终学习率因子:").pack(pady=(10, 5))
        lrf_var = tk.DoubleVar(value=0.01)
        ttk.Entry(train_window, textvariable=lrf_var, width=40).pack()
        
        ttk.Label(train_window, text="权重衰减:").pack(pady=(10, 5))
        weight_decay_var = tk.DoubleVar(value=0.0008)
        ttk.Entry(train_window, textvariable=weight_decay_var, width=40).pack()
        
        ttk.Label(train_window, text="优化器:").pack(pady=(10, 5))
        optimizer_var = tk.StringVar(value='AdamW')
        ttk.Entry(train_window, textvariable=optimizer_var, width=40).pack()
        
        def start_training():
            data_path = data_path_var.get()
            epochs = epochs_var.get()
            batch = batch_var.get()
            imgsz = imgsz_var.get()
            lr0 = lr0_var.get()
            lrf = lrf_var.get()
            weight_decay = weight_decay_var.get()
            optimizer = optimizer_var.get()
            
            train_window.destroy()
            
            self.logger.info(f"开始训练模型: 数据集={data_path}, 轮数={epochs}, 批次={batch}, 图像尺寸={imgsz}")
            
            def train_thread():
                try:
                    import torch
                    device = 'cuda' if torch.cuda.is_available() else 'cpu'
                    
                    model = YOLO('yolo26s.pt')
                    model.train(
                        data=data_path,
                        epochs=epochs,
                        batch=batch,
                        imgsz=imgsz,
                        patience=60,
                        lr0=lr0,
                        lrf=lrf,
                        weight_decay=weight_decay,
                        optimizer=optimizer,
                        mixup=0.12,
                        copy_paste=0.25,
                        mosaic=1.0,
                        cos_lr=True,
                        close_mosaic=15,
                        amp=True,
                        workers=8,
                        device=device,
                        project='runs/train',
                        name='yolo26s_red_pocket',
                        exist_ok=False,
                        seed=42,
                        deterministic=True
                    )
                    self.logger.info("模型训练完成!")
                except Exception as e:
                    self.logger.error(f"训练错误: {e}")
                    
            threading.Thread(target=train_thread, daemon=True).start()
            
        ttk.Button(train_window, text="开始训练", command=start_training).pack(pady=20)


def main():
    root = tk.Tk()
    app = RedPocketApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
