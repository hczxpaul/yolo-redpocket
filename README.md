# YOLO 微信红包自动抢夺器

基于 YOLOv8 深度学习目标检测的跨平台微信红包自动抢夺工具。

## 项目概述

本项目使用 YOLOv8 目标检测模型，结合实时屏幕捕获和自动化操作技术，实现微信红包的自动识别、定位和抢夺功能。项目采用模块化设计，支持 Windows、macOS 和 Linux 三大平台，提供完善的图形用户界面、数据标注工具和模型训练流程。

## 核心功能

### 主程序功能
- 🎯 **实时目标检测** - 使用 YOLOv8 模型快速检测红包、开按钮等 7 类元素
- 🖥️ **跨平台支持** - Windows（最佳支持）、macOS、Linux 全平台兼容
- 🎨 **图形化界面** - 基于 Tkinter 的直观用户界面
- ⚡ **高效屏幕捕获** - 使用 mss 实现高性能屏幕录制
- 📐 **窗口管理** - 自动定位微信窗口，支持自定义区域选择
- 🔧 **灵活配置** - YAML 配置文件自定义参数
- ⌨️ **全局快捷键** - F9 键暂停/恢复抢红包（Windows 支持全局快捷键）
- 🎮 **三级优先级检测** - 开按钮 > 红包 > 返回/关闭按钮
- 🔄 **智能返回** - 自动返回聊天界面继续监控
- 📊 **实时性能监控** - FPS、推理时间、捕获时间显示

### 辅助工具
- 📝 **数据标注工具** - 内置标注工具，支持 YOLO 格式导出
- 🚀 **模型训练** - 完整的训练流程和最佳实践参数
- 📁 **数据集整理** - 自动划分训练集/验证集，数据增强

## 技术栈

### 核心依赖
| 技术/库 | 版本 | 用途 |
|---------|------|------|
| Python | 3.10+ | 开发语言 |
| ultralytics | 8.2.0+ | YOLO 目标检测框架 |
| OpenCV | 4.8.0+ | 图像处理 |
| PyTorch | 2.0.0+ | 深度学习框架 |
| NumPy | 1.24.0+ | 数值计算 |
| Pillow | 10.0.0+ | 图像处理 |

### GUI 和自动化
| 技术/库 | 用途 |
|---------|------|
| Tkinter | 图形用户界面 |
| pyautogui | 鼠标键盘自动化 |
| mss | 高性能屏幕捕获 |

### 平台特定
- **Windows**: win32api, win32con, win32gui (窗口管理、全局热键)
- **macOS**: AppKit, Quartz (窗口管理)
- **Linux**: python-xlib (窗口管理)

### 其他
- PyYAML：配置文件管理
- 支持硬件加速：CUDA、MPS (Apple Silicon)、RKNPU (Rockchip)

## 检测类别

模型可以检测以下 7 个类别：

| ID | 类别名称 | 描述 | 颜色 | 优先级 |
|----|---------|------|------|--------|
| 0 | red_packet | 红包封面 | 绿色 | 2 |
| 1 | open_button | 开红包按钮 | 红色 | 1（最高） |
| 2 | amount_text | 金额文字 | 蓝色 | - |
| 3 | close_button | 关闭按钮 | 黄色 | 3 |
| 4 | back_button | 返回按钮 | 橙色 | 3 |
| 5 | opened_red_packet | 已拆开的红包 | 灰色 | - |
| 6 | play_button | 播放按钮 | 青色 | - |

## 安装与配置

### 环境要求
- Python 3.10 或更高版本
- 支持 CUDA 的 GPU（推荐，用于加速推理）
- 微信桌面版
- 至少 4GB RAM（推荐 8GB+）
- 10GB 可用磁盘空间

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/hczxpaul/yolo-redpocket.git
cd yolo-redpocket

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. 安装通用依赖
pip install -r requirements.txt

# 5. 安装平台特定依赖
# Windows:
pip install -r requirements-windows.txt
# macOS:
pip install -r requirements-macos.txt
# Linux:
pip install -r requirements-linux.txt
```

### 模型准备

将训练好的模型文件放置在 `models/` 目录下，默认模型路径为 `models/best.pt`。

如需训练自己的模型，请参考[模型训练](#模型训练)章节。

## 使用指南

### 启动主程序

```bash
python main.py
```

#### 主程序使用流程

1. **选择监控窗口**
   - 点击"点击选择窗口"按钮
   - 在全屏选择界面中点击微信窗口
   - 或按 ESC 取消选择

2. **加载模型**
   - 点击"加载模型"按钮
   - 选择训练好的 .pt 模型文件
   - 或使用默认模型 `models/best.pt`

3. **开始监控**
   - 点击"开始监控"按钮
   - 微信窗口会自动置顶
   - 右侧预览区域显示实时检测结果

4. **开始抢红包**
   - 点击"开始抢红包"按钮启用自动模式
   - 或按 **F9** 键（全局/窗口内快捷键）暂停/恢复
   - 程序会按优先级自动点击检测到的目标

#### 快捷键

| 快捷键 | 功能 | 平台 |
|--------|------|------|
| F9 | 暂停/恢复抢红包 | 全部（Windows 支持全局） |

#### 检测优先级

1. **最高优先级**：开红包按钮 (open_button) - 立即连续点击
2. **第二优先级**：红包封面 (red_packet) - 点击打开红包
3. **第三优先级**：返回/关闭按钮 - 点击返回聊天界面

### 使用标注工具

```bash
python labeling_tool.py
```

**功能：**
- 加载图像数据集
- 绘制边界框标注
- 支持 7 个类别选择
- 导出 YOLO 格式标注
- 标注质量检查和修复

### 模型训练

```bash
python train_with_best_practices.py
```

**训练特性：**
- 预配置的最佳训练参数
- 自动硬件加速检测（CUDA/MPS/RKNPU）
- 完整的数据增强（mosaic、mixup、copy_paste）
- AdamW 优化器 + 余弦学习率调度
- 早停机制 (patience=60)
- 自动验证和指标记录
- 最佳模型自动保存

**训练输出：**
- 最佳模型：`models/best.pt`
- 带时间戳的模型：`models/yolo26s_best_latest.pt`
- 训练配置：`models/yolo26s_best_config.yaml`

### 整理数据集

```bash
python organize_dataset.py
```

**功能：**
- 按比例划分训练集/验证集
- 数据增强
- 格式转换

## 项目结构

```
yolo-redpocket/
├── main.py                          # 主程序入口
├── labeling_tool.py                 # 数据标注工具
├── platform_adapter.py              # 跨平台适配层
├── config_utils.py                  # 配置工具
├── train_with_best_practices.py     # 模型训练脚本
├── organize_dataset.py              # 数据集整理脚本
├── config.yaml                      # 项目配置文件
├── dataset.yaml                     # 数据集配置文件
├── requirements.txt                 # 通用依赖
├── requirements-windows.txt         # Windows 平台依赖
├── requirements-macos.txt           # macOS 平台依赖
├── requirements-linux.txt           # Linux 平台依赖
├── .gitignore                       # Git 忽略文件
├── LICENSE                          # MIT 许可证
├── README.md                        # 项目说明文档（本文件）
├── dataset/                         # 数据集目录（Git 忽略）
│   ├── images/
│   │   ├── train/                   # 训练集图像
│   │   └── val/                     # 验证集图像
│   └── labels/
│       ├── train/                   # 训练集标注
│       └── val/                     # 验证集标注
├── models/                          # 模型目录（Git 忽略）
│   ├── best.pt                      # 最佳模型权重
│   └── yolo26s_best_latest.pt      # 最新模型备份
└── runs/                            # 训练和验证结果（Git 忽略）
    ├── detect/                      # 检测结果
    └── train/                       # 训练结果
```

## 功能模块介绍

### 核心类 (main.py)

#### 1. LoggerHandler
自定义日志处理器，将日志输出到 Tkinter 文本控件，支持线程安全操作。

#### 2. ScreenCapture
屏幕捕获和窗口管理类，提供跨平台支持：
- `find_wechat_window()` - 自动查找微信窗口
- `set_window_by_point()` - 通过坐标选择窗口（Windows）
- `capture_window()` - 捕获窗口内容
- `bring_window_to_front()` - 将窗口带到前台
- `set_always_on_top()` - 设置窗口置顶

#### 3. RedPocketDetector
红包检测器类，使用 YOLO 模型进行目标检测：
- `load_model()` - 加载 YOLO 模型
- `detect()` - 执行目标检测
- `find_red_packets()` / `find_open_button()` 等 - 查找特定类别
- 自动检测最佳设备：CUDA > MPS > RKNPU > CPU

#### 4. AutoClicker
自动点击类：
- `click_at_position()` - 点击指定位置
- `click_center()` - 点击边界框中心
- 双后端支持：win32api（Windows）或 pyautogui（跨平台）

#### 5. DataLabeler
数据标注辅助类：
- `save_image()` - 保存截图
- `save_label()` - 保存 YOLO 格式标注

#### 6. RedPocketApp
主应用程序类，包含完整的 GUI：
- 控制面板（状态、模型、监控、窗口选择）
- 实时预览（带检测框叠加）
- 日志显示
- 数据标注功能
- 模型训练配置

### 跨平台适配层 (platform_adapter.py)

#### 基类：PlatformAdapter
定义统一的接口：
- `find_target_window()` - 查找目标窗口
- `bring_window_to_front()` - 激活窗口
- `get_window_rect()` - 获取窗口位置

#### 实现类
- **WindowsAdapter** - 使用 win32gui（完整支持）
- **MacOSAdapter** - 使用 AppKit/Quartz
- **LinuxAdapter** - 使用 python-xlib

### 配置工具 (config_utils.py)
- `load_classes_from_config()` - 从 dataset.yaml 加载类别名称
- 支持字典格式和列表格式的 names 字段
- 自动回退到默认类别

## 配置参数说明

### config.yaml

```yaml
project:
  name: 微信红包自动抢夺器 - YOLO版
  version: 2.0.0
  author: RedPocket Team

model:
  default_path: models/best.pt
  default_size: s
  classes:
    - red_packet
    - open_button
    - amount_text
    - close_button
    - back_button
    - opened_red_packet

class_colors:
  red_packet: [0, 255, 0]
  open_button: [255, 0, 0]
  amount_text: [0, 0, 255]
  close_button: [255, 255, 0]
  back_button: [255, 128, 0]
  opened_red_packet: [128, 128, 128]

detection:
  default_confidence: 0.5
  iou_threshold: 0.7

training:
  default_epochs: 100
  default_batch: 16
  default_imgsz: 640
  default_patience: 30
  workers: 8
  amp: true

ui:
  window_width: 1600
  window_height: 1000
  min_window_width: 1400
  min_window_height: 900
  background_color: "#f0f0f0"

paths:
  dataset: dataset
  models: models
  runs: runs
  logs: logs
```

### dataset.yaml

```yaml
path: ./dataset
train: images/train
val: images/val

names:
  0: red_packet
  1: open_button
  2: amount_text
  3: close_button
  4: back_button
  5: opened_red_packet
  6: play_button
```

## 平台兼容性

| 平台 | 状态 | 窗口管理 | 全局热键 | 备注 |
|------|------|---------|---------|------|
| Windows | ✅ 完全支持 | ✅ | ✅ | 推荐使用 |
| macOS | ✅ 支持 | ✅ | ❌ | 需要屏幕录制和辅助功能权限 |
| Linux | ✅ 支持 | ✅ | ❌ | GNOME/KDE 最佳，需要 python-xlib |

### macOS 权限设置

在 macOS 上使用需要授予以下权限：
1. 系统设置 > 隐私与安全性 > 屏幕录制
2. 系统设置 > 隐私与安全性 > 辅助功能

## 常见问题解答

### Q: 程序找不到微信窗口怎么办？
A: 请确保微信已登录并在前台运行，然后尝试使用"点击选择窗口"功能手动选择。

### Q: 检测准确率不高怎么办？
A: 可以尝试：
1. 降低置信度阈值（config.yaml 或 GUI 滑动条）
2. 使用自己的数据集重新训练模型
3. 增加训练数据量

### Q: macOS 上权限被拒绝怎么办？
A: 请在系统设置 > 隐私与安全性中授予终端屏幕录制和辅助功能权限。

### Q: 如何使用自己的模型？
A: 将模型文件放在 models/ 目录下，修改 config.yaml 中的 model.default_path 配置，或在 GUI 中手动加载。

### Q: F9 快捷键没有反应？
A: 
- Windows：确保程序有焦点，或使用全局快捷键
- macOS/Linux：仅支持窗口内快捷键，需要先点击程序窗口

### Q: 如何暂停/恢复抢红包？
A: 点击"暂停抢红包"按钮或按 F9 键（Windows 支持全局）。

## 贡献指南

我们欢迎任何形式的贡献！

### 开发流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码风格

- 遵循 PEP 8 规范
- 使用类型提示
- 编写有意义的注释
- 保持函数单一职责

### 提交信息格式

```
<type>(<scope>): <subject>

类型:
- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 重构
- test: 测试相关
- chore: 构建/工具相关
```

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](./LICENSE) 文件。

## 免责声明

⚠️ **重要提示：**

本项目仅供学习和研究目的使用。请勿将本工具用于商业用途或违反微信服务条款的行为。使用本工具所产生的一切后果由使用者自行承担。

请合理使用，尊重他人权益，遵守相关法律法规。

## 联系方式

- GitHub: [https://github.com/hczxpaul/yolo-redpocket](https://github.com/hczxpaul/yolo-redpocket)
- Issues: [GitHub Issues](https://github.com/hczxpaul/yolo-redpocket/issues)

---

**感谢使用 YOLO 微信红包自动抢夺器！** 🎉
