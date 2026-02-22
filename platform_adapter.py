"""
平台适配层 - 提供跨平台的窗口管理和自动化功能
"""
import sys
import logging
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
                    app.activateWithOptions_(1 << 1)
                    return True
        except Exception as e:
            logger.error(f"激活窗口失败: {e}")
        
        return False
    
    def get_window_rect(self, window_info: dict) -> Optional[Tuple[int, int, int, int]]:
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
