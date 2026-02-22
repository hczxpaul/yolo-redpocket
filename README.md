# YOLO 微信红包自动抢夺器

基于 YOLOv8 深度学习目标检测的跨平台微信红包自动抢夺工具。

## 项目简介

使用 YOLOv8 模型进行实时屏幕目标检测，结合自动化操作实现微信红包的自动识别和抢夺。支持 Windows、macOS 和 Linux 三大平台。

## 核心功能

- 🎯 实时目标检测 - YOLOv8 快速检测红包、开按钮等元素
- 🖥️ 跨平台支持 - Windows、macOS、Linux 全平台兼容
- 🎨 图形化界面 - 基于 Tkinter 的直观用户界面
- ⚡ 高效屏幕捕获 - 使用 mss 实现高性能录制
- 📐 窗口管理 - 自动定位微信窗口，支持自定义区域
- 🔧 灵活配置 - YAML 配置文件自定义参数
- 📝 数据标注 - 内置标注工具
- 🚀 模型训练 - 完整训练流程和最佳实践

## 技术栈

| 技术/库 | 用途 |
|---------|------|
| Python 3.10+ | 开发语言 |
| ultralytics 8.2.0+ | YOLO 目标检测框架 |
| OpenCV 4.8.0+ | 图像处理 |
| PyTorch 2.0.0+ | 深度学习框架 |
| NumPy 1.24.0+ | 数值计算 |
| Pillow 10.0.0+ | 图像处理 |
| Tkinter | 图形用户界面 |
| pyautogui | 鼠标键盘自动化 |
| mss | 高性能屏幕捕获 |
| PyYAML | 配置文件管理 |

## 安装

### 环境要求
- Python 3.10+
- 支持 CUDA 的 GPU（推荐）
- 微信桌面版
- 至少 4GB RAM（推荐 8GB+）

### 步骤

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

# 4. 安装依赖
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

将训练好的模型文件放置在 `models/` 目录下，默认路径为 `models/best.pt`。

## 使用

### 启动主程序

```bash
python main.py
```

**功能：** 自动定位微信窗口，实时检测红包，自动点击开按钮。

### 标注工具

```bash
python labeling_tool.py
```

**功能：** 加载图像数据集，绘制边界框标注，导出 YOLO 格式。

### 训练模型

```bash
python train_with_best_practices.py
```

**功能：** 自动数据增强、超参数优化、早停机制、训练可视化。

### 整理数据集

```bash
python organize_dataset.py
```

**功能：** 按比例划分训练集/验证集、数据增强、格式转换。

## 项目结构

```
yolo-redpocket/
├── main.py                      # 主程序入口
├── labeling_tool.py             # 数据标注工具
├── platform_adapter.py          # 跨平台适配层
├── config_utils.py              # 配置工具
├── train_with_best_practices.py # 模型训练脚本
├── organize_dataset.py          # 数据集整理脚本
├── config.yaml                  # 项目配置
├── dataset.yaml                 # 数据集配置
├── requirements.txt             # 通用依赖
├── requirements-windows.txt     # Windows 依赖
├── requirements-macos.txt       # macOS 依赖
├── requirements-linux.txt       # Linux 依赖
├── .gitignore                   # Git 忽略
├── LICENSE                      # MIT 许可证
└── README.md                    # 本文件
```

## 检测类别

| ID | 类别 | 描述 | 颜色 |
|----|------|------|------|
| 0 | red_packet | 红包封面 | 绿色 |
| 1 | open_button | 开红包按钮 | 红色 |
| 2 | amount_text | 金额文字 | 蓝色 |
| 3 | close_button | 关闭按钮 | 黄色 |
| 4 | back_button | 返回按钮 | 橙色 |
| 5 | opened_red_packet | 已拆开的红包 | 灰色 |

## 配置

编辑 `config.yaml` 自定义参数：

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

## 平台兼容性

| 平台 | 状态 | 备注 |
|------|------|------|
| Windows | ✅ 完全支持 | 推荐使用 |
| macOS | ✅ 支持 | 需要屏幕录制和辅助功能权限 |
| Linux | ✅ 支持 | GNOME/KDE 最佳 |

## 常见问题

**Q: 程序找不到微信窗口怎么办？**  
A: 确保微信已登录并在前台运行，使用手动选择窗口功能。

**Q: 检测准确率不高怎么办？**  
A: 降低置信度阈值，或使用自己的数据集重新训练。

**Q: macOS 上权限被拒绝怎么办？**  
A: 在系统设置 > 隐私与安全性中授予屏幕录制和辅助功能权限。

**Q: 如何使用自己的模型？**  
A: 将模型文件放在 models/ 目录下，修改 config.yaml 中的 model.default_path。

## 贡献

欢迎贡献！请遵循以下流程：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

**提交信息格式：**
- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

## 许可证

MIT License - 详见 [LICENSE](./LICENSE)。

## 免责声明

⚠️ **本项目仅供学习和研究使用。请勿用于商业用途或违反微信服务条款的行为。使用本工具所产生的一切后果由使用者自行承担。**

## 联系方式

- GitHub: [https://github.com/hczxpaul/yolo-redpocket](https://github.com/hczxpaul/yolo-redpocket)
- Issues: [GitHub Issues](https://github.com/hczxpaul/yolo-redpocket/issues)

---

**感谢使用！** 🎉
