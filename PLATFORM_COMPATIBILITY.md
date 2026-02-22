# Apple Silicon 和 RK 系列处理器平台兼容性评估报告

## 1. 当前代码架构分析

### 1.1 核心依赖
- **YOLO 推理框架**: Ultralytics YOLO (v8.2+)
- **深度学习框架**: PyTorch (v2.0+)
- **计算机视觉**: OpenCV (v4.8+)
- **图形界面**: Tkinter
- **屏幕捕获**: MSS
- **自动化操作**: PyAutoGUI
- **Windows 特定**: win32gui, win32con, win32api, pywin32

### 1.2 硬件加速相关代码

**当前实现** (`main.py:212-237`):
```python
def load_model(self, model_path):
    try:
        import torch
        if torch.cuda.is_available():
            self.device = 'cuda'
            self.logger.info(f"使用GPU加速: {torch.cuda.get_device_name(0)}")
        else:
            self.device = 'cpu'
            self.logger.info("使用CPU运行")
```

## 2. 兼容性评估

### 2.1 Apple Silicon (M1/M2/M3) 平台

| 功能模块 | 当前状态 | 兼容性 | 说明 |
|---------|---------|--------|------|
| **PyTorch + MPS** | ❌ 不支持 | 低 | 代码仅检测 CUDA，不支持 MPS |
| **Ultralytics YOLO** | ✅ 支持 | 高 | YOLO v8 原生支持 Apple Silicon |
| **win32gui/win32api** | ❌ 完全不支持 | 无 | Windows 专属 API，macOS 无法使用 |
| **pyautogui** | ✅ 部分支持 | 中 | macOS 可用，但部分功能受限 |
| **屏幕捕获 (mss)** | ✅ 支持 | 高 | MSS 支持 macOS |
| **Tkinter** | ✅ 支持 | 高 | macOS 内置 Tkinter |

**主要问题**:
1. ❌ 硬编码的 Windows API 依赖
2. ❌ 未检测 Apple MPS 硬件加速
3. ❌ 微信窗口查找逻辑仅适用于 Windows

### 2.2 RK 系列处理器 (Rockchip) 平台

| 功能模块 | 当前状态 | 兼容性 | 说明 |
|---------|---------|--------|------|
| **PyTorch + RKNPU** | ❌ 不支持 | 低 | 代码仅检测 CUDA，不支持 RKNPU |
| **Ultralytics YOLO** | ⚠️ 需要转换 | 中 | 需要转换为 RKNN 格式 |
| **win32gui/win32api** | ❌ 完全不支持 | 无 | Windows 专属 API |
| **pyautogui** | ⚠️ 视系统而定 | 中 | 取决于 Linux 桌面环境 |
| **屏幕捕获 (mss)** | ✅ 支持 | 高 | MSS 支持 Linux |
| **Tkinter** | ✅ 支持 | 高 | Linux 可用 |

**主要问题**:
1. ❌ 硬编码的 Windows API 依赖
2. ❌ 未检测 RKNPU 硬件加速
3. ❌ 微信窗口查找逻辑仅适用于 Windows
4. ⚠️ YOLO 模型需要转换为 RKNN 格式

## 3. 技术分析

### 3.1 硬件加速检测缺陷

**当前问题**:
```python
# 仅支持 CUDA
if torch.cuda.is_available():
    self.device = 'cuda'
else:
    self.device = 'cpu'
```

**缺失检测**:
- Apple MPS: `torch.backends.mps.is_available()`
- RKNPU: 需要使用 `rknn-toolkit2` 或 `torch-rknn`

### 3.2 平台特定依赖问题

**Windows 专属代码** (`main.py:85-160`):
- `win32gui.EnumWindows()` - 窗口枚举
- `win32gui.GetWindowText()` - 获取窗口标题
- `win32gui.GetWindowRect()` - 获取窗口位置
- `win32gui.SetForegroundWindow()` - 激活窗口
- `win32con.SW_RESTORE` - 窗口常量

这些 API 在 macOS 和 Linux 上完全不可用。

## 4. 改进方案

### 4.1 硬件加速跨平台检测

**修改位置**: `main.py:212-237`

**改进后的代码**:
```python
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
    # ... 其余异常处理保持不变

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
```

### 4.2 平台抽象层设计

创建新文件 `platform_adapter.py`:

```python
"""
平台适配层 - 提供跨平台的窗口管理和自动化功能
"""
import sys
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class PlatformAdapter:
    """跨平台适配器基类"""
    
    def __init__(self):
        self.platform = sys.platform
    
    def find_target_window(self, title_contains: str) -> Optional[dict]:
        """查找包含指定标题的窗口"""
        raise NotImplementedError
    
    def bring_window_to_front(self, window_info: dict) -> bool:
        """将窗口带到前台"""
        raise NotImplementedError
    
    def get_window_rect(self, window_info: dict) -> Optional[Tuple[int, int, int, int]]:
        """获取窗口位置和大小 (x1, y1, x2, y2)"""
        raise NotImplementedError


class WindowsAdapter(PlatformAdapter):
    """Windows 平台适配器"""
    
    def __init__(self):
        super().__init__()
        import win32gui
        import win32con
        import win32api
        self.win32gui = win32gui
        self.win32con = win32con
        self.win32api = win32api
    
    def find_target_window(self, title_contains: str) -> Optional[dict]:
        windows = []
        
        def callback(hwnd, _):
            if self.win32gui.IsWindowVisible(hwnd):
                title = self.win32gui.GetWindowText(hwnd)
                if title_contains in title:
                    windows.append({
                        'hwnd': hwnd,
                        'title': title
                    })
            return True
        
        self.win32gui.EnumWindows(callback, None)
        return windows[0] if windows else None
    
    def bring_window_to_front(self, window_info: dict) -> bool:
        try:
            hwnd = window_info['hwnd']
            if self.win32gui.IsIconic(hwnd):
                self.win32gui.ShowWindow(hwnd, self.win32con.SW_RESTORE)
            self.win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            logger.error(f"激活窗口失败: {e}")
            return False
    
    def get_window_rect(self, window_info: dict) -> Optional[Tuple[int, int, int, int]]:
        try:
            return self.win32gui.GetWindowRect(window_info['hwnd'])
        except Exception as e:
            logger.error(f"获取窗口位置失败: {e}")
            return None


class MacOSAdapter(PlatformAdapter):
    """macOS 平台适配器"""
    
    def __init__(self):
        super().__init__()
        try:
            from AppKit import NSWorkspace, NSRunningApplication
            from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
            self.NSWorkspace = NSWorkspace
            self.NSRunningApplication = NSRunningApplication
            self.CGWindowListCopyWindowInfo = CGWindowListCopyWindowInfo
            self.kCGWindowListOptionOnScreenOnly = kCGWindowListOptionOnScreenOnly
            self.kCGNullWindowID = kCGNullWindowID
            self.has_appkit = True
        except ImportError:
            self.has_appkit = False
            logger.warning("未安装 pyobjc，macOS 窗口管理功能受限")
    
    def find_target_window(self, title_contains: str) -> Optional[dict]:
        if not self.has_appkit:
            return None
        
        try:
            windows = self.CGWindowListCopyWindowInfo(
                self.kCGWindowListOptionOnScreenOnly,
                self.kCGNullWindowID
            )
            
            for window in windows:
                window_name = window.get('kCGWindowName', '')
                if title_contains in window_name:
                    return {
                        'window_id': window.get('kCGWindowNumber'),
                        'title': window_name,
                        'owner_pid': window.get('kCGWindowOwnerPID')
                    }
        except Exception as e:
            logger.error(f"查找窗口失败: {e}")
        
        return None
    
    def bring_window_to_front(self, window_info: dict) -> bool:
        if not self.has_appkit:
            return False
        
        try:
            pid = window_info.get('owner_pid')
            if pid:
                app = self.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                if app:
                    app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
                    return True
        except Exception as e:
            logger.error(f"激活窗口失败: {e}")
        
        return False
    
    def get_window_rect(self, window_info: dict) -> Optional[Tuple[int, int, int, int]]:
        # macOS 需要额外实现
        return None


class LinuxAdapter(PlatformAdapter):
    """Linux 平台适配器 (RK 系列等)"""
    
    def __init__(self):
        super().__init__()
        try:
            import Xlib.display
            import Xlib.X
            self.display = Xlib.display.Display()
            self.has_xlib = True
        except ImportError:
            self.has_xlib = False
            logger.warning("未安装 python-xlib，Linux 窗口管理功能受限")
    
    def find_target_window(self, title_contains: str) -> Optional[dict]:
        if not self.has_xlib:
            return None
        
        try:
            root = self.display.screen().root
            windows = self._search_windows(root, title_contains)
            return windows[0] if windows else None
        except Exception as e:
            logger.error(f"查找窗口失败: {e}")
            return None
    
    def _search_windows(self, window, title_contains: str):
        """递归搜索窗口"""
        result = []
        try:
            title = window.get_wm_name()
            if title and title_contains in title:
                result.append({
                    'window': window,
                    'title': title
                })
            
            for child in window.query_tree().children:
                result.extend(self._search_windows(child, title_contains))
        except:
            pass
        return result
    
    def bring_window_to_front(self, window_info: dict) -> bool:
        if not self.has_xlib:
            return False
        
        try:
            window = window_info['window']
            window.set_input_focus(Xlib.X.RevertToParent, Xlib.X.CurrentTime)
            window.configure(stack_mode=Xlib.X.Above)
            self.display.flush()
            return True
        except Exception as e:
            logger.error(f"激活窗口失败: {e}")
            return False
    
    def get_window_rect(self, window_info: dict) -> Optional[Tuple[int, int, int, int]]:
        if not self.has_xlib:
            return None
        
        try:
            window = window_info['window']
            geom = window.get_geometry()
            return (geom.x, geom.y, geom.x + geom.width, geom.y + geom.height)
        except Exception as e:
            logger.error(f"获取窗口位置失败: {e}")
            return None


def get_platform_adapter() -> PlatformAdapter:
    """获取当前平台的适配器"""
    if sys.platform.startswith('win'):
        return WindowsAdapter()
    elif sys.platform == 'darwin':
        return MacOSAdapter()
    elif sys.platform.startswith('linux'):
        return LinuxAdapter()
    else:
        logger.warning(f"未支持的平台: {sys.platform}")
        return PlatformAdapter()
```

### 4.3 更新 requirements.txt

创建平台特定的依赖文件:

**requirements-windows.txt** (原 requirements.txt):
```
# Core dependencies
ultralytics>=8.2.0,<9.0.0
opencv-python>=4.8.0,<5.0.0
numpy>=1.24.0,<2.0.0
Pillow>=10.0.0,<12.0.0
torch>=2.0.0,<3.0.0
torchvision>=0.15.0,<1.0.0

# GUI and Automation
tkinter-tooltip>=2.1.0
pyautogui>=0.9.54
pywin32>=306

# Screen capture and window management
mss>=9.0.0

# Configuration
PyYAML>=6.0.0,<7.0.0
```

**requirements-macos.txt**:
```
# Core dependencies
ultralytics>=8.2.0,<9.0.0
opencv-python>=4.8.0,<5.0.0
numpy>=1.24.0,<2.0.0
Pillow>=10.0.0,<12.0.0
torch>=2.0.0,<3.0.0
torchvision>=0.15.0,<1.0.0

# macOS 特定 - Apple Silicon 优化
torchvision>=0.15.0

# GUI and Automation
tkinter-tooltip>=2.1.0
pyautogui>=0.9.54
pyobjc>=9.0.0

# Screen capture and window management
mss>=9.0.0

# Configuration
PyYAML>=6.0.0,<7.0.0
```

**requirements-linux.txt** (RK 系列):
```
# Core dependencies
ultralytics>=8.2.0,<9.0.0
opencv-python>=4.8.0,<5.0.0
numpy>=1.24.0,<2.0.0
Pillow>=10.0.0,<12.0.0
torch>=2.0.0,<3.0.0
torchvision>=0.15.0,<1.0.0

# Linux 特定 - X11 窗口管理
python-xlib>=0.33

# GUI and Automation
tkinter-tooltip>=2.1.0
pyautogui>=0.9.54

# Screen capture and window management
mss>=9.0.0

# Configuration
PyYAML>=6.0.0,<7.0.0

# Optional: Rockchip RKNPU 支持
# rknn-toolkit2>=1.5.0
# rknn-toolkit-lite2>=1.5.0
```

## 5. 测试步骤

### 5.1 Apple Silicon 测试

#### 前置条件
1. macOS 12.0+ (Monterey 或更高)
2. Apple Silicon (M1/M2/M3) 芯片
3. Python 3.9+

#### 安装依赖
```bash
# 安装 Apple Silicon 优化的 PyTorch
pip3 install torch torchvision torchaudio

# 安装项目依赖
pip3 install -r requirements-macos.txt
```

#### 测试步骤

**测试 1: 硬件加速检测**
```python
from main import RedPocketDetector
import logging

logging.basicConfig(level=logging.INFO)
detector = RedPocketDetector(logger=logging.getLogger())

# 验证设备检测
assert detector._get_best_device() == 'mps', "MPS 未被正确检测"
print("✓ MPS 硬件加速检测通过")
```

**测试 2: 模型加载**
```python
success = detector.load_model("path/to/model.pt")
assert success, "模型加载失败"
assert detector.device == 'mps', "模型未加载到 MPS"
print("✓ 模型在 MPS 上加载成功")
```

**测试 3: 推理性能**
```python
import time
import numpy as np

test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

# 预热
for _ in range(5):
    detector.detect(test_image)

# 测速
start = time.time()
for _ in range(10):
    detector.detect(test_image)
fps = 10 / (time.time() - start)

print(f"✓ 推理速度: {fps:.1f} FPS")
assert fps > 5, "MPS 推理性能过低"
```

**测试 4: 窗口管理 (基础功能)**
```python
from platform_adapter import get_platform_adapter

adapter = get_platform_adapter()
assert isinstance(adapter, MacOSAdapter), "平台适配器错误"
print("✓ macOS 平台适配器加载成功")
```

### 5.2 RK 系列处理器测试

#### 前置条件
1. Rockchip 处理器 (RK3588/RK3568 等)
2. Linux 系统 (Debian/Ubuntu/Armbian)
3. Python 3.9+

#### 安装依赖
```bash
# 基础依赖
pip3 install -r requirements-linux.txt

# 可选: 安装 RKNPU SDK
# 参考: https://github.com/rockchip-linux/rknn-toolkit2
```

#### 测试步骤

**测试 1: 平台检测**
```python
from platform_adapter import get_platform_adapter

adapter = get_platform_adapter()
assert isinstance(adapter, LinuxAdapter), "平台适配器错误"
print("✓ Linux 平台适配器加载成功")
```

**测试 2: 硬件加速检测**
```python
from main import RedPocketDetector
import logging

logging.basicConfig(level=logging.INFO)
detector = RedPocketDetector(logger=logging.getLogger())

device = detector._get_best_device()
print(f"检测到的设备: {device}")
# RKNPU 需要额外配置，CPU 也是可接受的
assert device in ['cpu', 'rknpu', 'cuda'], "设备检测失败"
print("✓ 硬件加速检测通过")
```

**测试 3: 基础推理功能**
```python
import numpy as np

success = detector.load_model("path/to/model.pt")
assert success, "模型加载失败"

test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
detections = detector.detect(test_image)
print(f"✓ 推理成功，检测到 {len(detections)} 个目标")
```

## 6. 验证方法

### 6.1 硬件加速验证清单

| 验证项 | Apple Silicon | RK 系列 | 验证方法 |
|-------|--------------|---------|---------|
| 设备正确识别 | ✅ MPS | ⚠️ RKNPU/CPU | 日志输出 |
| 模型成功加载 | ✅ | ✅ | 无异常抛出 |
| 推理正常执行 | ✅ | ✅ | 返回检测结果 |
| 性能显著提升 | ✅ 相比 CPU | ⚠️ 视配置 | FPS 对比测试 |

### 6.2 兼容性验证矩阵

| 功能模块 | Windows | macOS | Linux (RK) |
|---------|---------|-------|-----------|
| YOLO 推理 | ✅ | ✅ | ✅ |
| 硬件加速 (CUDA) | ✅ | ❌ | ❌ |
| 硬件加速 (MPS) | ❌ | ✅ | ❌ |
| 硬件加速 (RKNPU) | ❌ | ❌ | ⚠️ |
| 屏幕捕获 | ✅ | ✅ | ✅ |
| 窗口管理 | ✅ | ⚠️ | ⚠️ |
| 自动点击 | ✅ | ✅ | ✅ |
| GUI 界面 | ✅ | ✅ | ✅ |

## 7. 预期结果

### 7.1 Apple Silicon (M1/M2/M3)
- ✅ **硬件加速**: 自动检测并使用 MPS
- ⚡ **性能提升**: 相比 CPU 推理速度提升 3-8 倍
- 🔄 **兼容性**: 核心 YOLO 功能完整可用
- ⚠️ **限制**: Windows 专属的微信窗口查找功能需要调整

### 7.2 RK 系列处理器 (RK3588)
- ⚠️ **硬件加速**: 需要转换模型为 RKNN 格式才能启用
- 💻 **CPU 模式**: 可在 CPU 模式下正常运行
- 🔄 **兼容性**: 核心功能可用，性能取决于 CPU 能力
- ⚠️ **限制**: RKNPU 集成需要额外开发

## 8. 后续优化建议

1. **RKNN 模型转换**: 为 RK 系列提供 YOLO 到 RKNN 的转换脚本
2. **性能基准测试**: 建立各平台的性能基准测试套件
3. **CI/CD**: 添加多平台自动化测试
4. **文档完善**: 补充各平台的详细安装和配置指南
