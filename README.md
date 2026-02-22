# YOLO 微信红包自动抢夺器

基于 YOLO (You Only Look Once) 深度学习目标检测的跨平台微信红包自动抢夺工具。

## 项目概述

本项目使用 YOLOv8 目标检测模型，结合屏幕捕获和自动化操作技术，实现微信红包的自动识别、定位和抢夺功能。项目采用模块化设计，支持 Windows、macOS 和 Linux 三大平台。

## 核心功能

- 🎯 **实时目标检测**：使用 YOLOv8 模型快速检测红包、开按钮等元素
- 🖥️ **跨平台支持**：Windows、macOS、Linux 全平台兼容
- 🎨 **图形化界面**：基于 Tkinter 的直观用户界面
- ⚡ **高效屏幕捕获**：使用 mss 库实现高性能屏幕录制
- 📐 **窗口管理**：自动定位微信窗口，支持自定义区域选择
- 🔧 **灵活配置**：通过 YAML 配置文件自定义参数
- 📝 **数据标注**：内置标注工具，方便训练数据准备
- 🚀 **模型训练**：提供完整的训练流程和最佳实践

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
- **Windows**: win32api, win32con, win32gui (窗口管理)
- **macOS**: 原生窗口管理 API
- **Linux**: 基于桌面环境的窗口管理

### 其他
- PyYAML：配置文件管理
- 类型提示支持

## 安装与配置

### 环境要求
- Python 3.10 或更高版本
- 支持 CUDA 的 GPU（推荐，用于加速推理）
- 微信桌面版
- 至少 4GB RAM（推荐 8GB+）
- 10GB 可用磁盘空间

### 步骤 1：克隆仓库

```bash
git clone https://github.com/hczxpaul/yolo-redpocket.git
cd yolo-redpocket
```

### 步骤 2：创建虚拟环境（推荐）

```bash
python -m venv venv
```

**激活虚拟环境：**

Windows:
```bash
venv\Scripts\activate
```

macOS/Linux:
```bash
source venv/bin/activate
```

### 步骤 3：安装依赖

**通用依赖：**
```bash
pip install -r requirements.txt
```

**平台特定依赖：**

Windows:
```bash
pip install -r requirements-windows.txt
```

macOS:
```bash
pip install -r requirements-macos.txt
```

Linux:
```bash
pip install -r requirements-linux.txt
```

### 步骤 4：下载或准备模型

**方式 1：使用提供的下载脚本**
```bash
python download_model.py
```

**方式 2：使用预训练模型**
将训练好的模型文件放置在 `models/` 目录下，默认模型路径为 `models/best.pt`。

### 步骤 5：配置项目

编辑 `config.yaml` 文件以自定义配置：

```yaml
project:
  name: 微信红包自动抢夺器 - YOLO版
  version: 2.0.0

model:
  default_path: models/best.pt
  classes:
    - red_packet
    - open_button
    - amount_text
    - close_button
    - back_button
    - opened_red_packet

detection:
  default_confidence: 0.5
  iou_threshold: 0.7

paths:
  dataset: dataset
  models: models
  runs: runs
  logs: logs
```

## 使用指南

### 启动主程序

```bash
python main.py
```

**主程序功能：**
1. 自动定位微信窗口
2. 实时检测红包和相关元素
3. 自动点击开红包按钮
4. 实时显示检测结果和日志

### 使用标注工具

```bash
python labeling_tool.py
```

**标注工具功能：**
1. 加载图像数据集
2. 绘制边界框标注
3. 导出 YOLO 格式标注
4. 支持类别选择

### 训练模型

```bash
python train_with_best_practices.py
```

**训练功能：**
1. 自动数据增强
2. 超参数优化
3. 早停机制
4. 训练可视化

### 整理数据集

```bash
python organize_dataset.py
```

**数据集整理功能：**
1. 按比例划分训练集/验证集
2. 数据增强
3. 格式转换

## 目录结构

```
yolo-redpocket/
├── main.py                          # 主程序入口
├── labeling_tool.py                 # 数据标注工具
├── platform_adapter.py              # 跨平台适配层
├── config_utils.py                  # 配置工具
├── train_with_best_practices.py    # 模型训练脚本
├── organize_dataset.py              # 数据集整理脚本
├── cleanup.py                       # 清理脚本
├── download_model.py                # 模型下载脚本
├── config.yaml                      # 项目配置文件（YAML）
├── config.ini                       # 旧版配置文件（向后兼容）
├── dataset.yaml                     # 数据集配置
├── requirements.txt                 # 通用依赖
├── requirements-windows.txt         # Windows 平台依赖
├── requirements-macos.txt           # macOS 平台依赖
├── requirements-linux.txt           # Linux 平台依赖
├── .gitignore                       # Git 忽略文件
├── LICENSE                          # MIT 许可证
├── README.md                        # 项目说明文档（本文件）
├── CROSS_PLATFORM_CHECKLIST.md     # 跨平台兼容性检查清单
├── IMPLEMENTATION_SUMMARY.md        # 跨平台实施总结
├── PLATFORM_COMPATIBILITY.md        # 平台兼容性评估
├── FILE_CLEANUP_PLAN.md             # 文件清理计划
├── dataset/                         # 数据集目录（Git 忽略）
│   ├── images/
│   │   ├── train/                   # 训练集图像
│   │   └── val/                     # 验证集图像
│   └── labels/
│       ├── train/                   # 训练集标注
│       └── val/                     # 验证集标注
├── models/                          # 模型目录（Git 忽略）
│   └── best.pt                      # 最佳模型权重
└── runs/                            # 训练和验证结果（Git 忽略）
    └── detect/
        ├── train/                   # 训练结果
        └── val/                     # 验证结果
```

## 检测类别

模型可以检测以下 6 个类别：

| 类别 ID | 类别名称 | 描述 | 颜色 |
|---------|---------|------|------|
| 0 | red_packet | 红包封面 | 绿色 |
| 1 | open_button | 开红包按钮 | 红色 |
| 2 | amount_text | 金额文字 | 蓝色 |
| 3 | close_button | 关闭按钮 | 黄色 |
| 4 | back_button | 返回按钮 | 橙色 |
| 5 | opened_red_packet | 已拆开的红包 | 灰色 |

## 平台兼容性

| 平台 | 状态 | 备注 |
|------|------|------|
| Windows | ✅ 完全支持 | 推荐使用 |
| macOS | ✅ 支持 | 需要屏幕录制和辅助功能权限 |
| Linux | ✅ 支持 | 取决于桌面环境（GNOME/KDE 最佳） |

详细的平台兼容性说明请参考 [PLATFORM_COMPATIBILITY.md](./PLATFORM_COMPATIBILITY.md)。

## 贡献规范

我们欢迎任何形式的贡献！

### 开发流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
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

## 常见问题

### Q: 程序找不到微信窗口怎么办？
A: 请确保微信已登录并在前台运行，然后尝试使用手动选择窗口功能。

### Q: 检测准确率不高怎么办？
A: 可以尝试降低置信度阈值，或使用自己的数据集重新训练模型。

### Q: macOS 上权限被拒绝怎么办？
A: 请在系统设置 > 隐私与安全性中授予终端屏幕录制和辅助功能权限。

### Q: 如何使用自己的模型？
A: 将模型文件放在 models/ 目录下，修改 config.yaml 中的 model.default_path 配置。

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
