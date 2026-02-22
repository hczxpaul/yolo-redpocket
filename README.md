# YOLO 红包自动抢夺器

基于 YOLO 目标检测的跨平台微信红包自动抢夺工具。

## 项目简介

本项目使用 YOLO (You Only Look Once) 深度学习模型进行实时屏幕目标检测，结合自动化操作实现微信红包的自动识别和抢夺功能。项目支持 Windows、macOS 和 Linux 三大平台。

## 功能特性

- 🎯 **实时目标检测**: 使用 YOLO 模型快速检测红包
- 🖥️ **跨平台支持**: Windows、macOS、Linux
- 🎨 **图形化界面**: 简洁易用的 Tkinter 界面
- ⚡ **高效屏幕捕获**: 使用 mss 进行高性能屏幕录制
- 🔧 **灵活配置**: 支持自定义配置参数
- 📝 **数据标注**: 内置标注工具，方便训练数据准备

## 项目结构

```
yolo-redpocket/
├── main.py                      # 主程序入口
├── labeling_tool.py             # 数据标注工具
├── platform_adapter.py          # 跨平台适配层
├── config_utils.py              # 配置工具
├── train_with_best_practices.py # 模型训练脚本
├── organize_dataset.py          # 数据集整理脚本
├── cleanup.py                   # 清理脚本
├── download_model.py            # 模型下载脚本
├── config.yaml                  # 项目配置文件
├── config.ini                   # 旧版配置（向后兼容）
├── dataset.yaml                 # 数据集配置
├── requirements.txt             # 通用依赖
├── requirements-windows.txt     # Windows 平台依赖
├── requirements-macos.txt       # macOS 平台依赖
├── requirements-linux.txt       # Linux 平台依赖
└── README.md                    # 项目说明文档
```

## 环境要求

- Python 3.10+
- 支持 CUDA 的 GPU（推荐，用于加速推理）
- 微信桌面版

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/yolo-redpocket.git
cd yolo-redpocket
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv
```

激活虚拟环境：

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. 安装依赖

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

### 4. 下载模型

运行模型下载脚本：

```bash
python download_model.py
```

或者从 Ultralytics 官方下载 YOLO 模型。

## 使用说明

### 启动主程序

```bash
python main.py
```

### 使用标注工具

```bash
python labeling_tool.py
```

### 训练模型

```bash
python train_with_best_practices.py
```

## 配置说明

主要配置文件为 `config.yaml`，可以自定义以下参数：

- 模型路径
- 检测阈值
- 屏幕捕获区域
- 点击延迟
- 日志级别

## 注意事项

⚠️ **免责声明：** 本项目仅供学习和研究使用，请勿用于商业用途或违反微信使用条款的行为。使用本工具所产生的一切后果由使用者自行承担。

## 平台兼容性

| 平台 | 状态 | 备注 |
|------|------|------|
| Windows | ✅ 完全支持 | 推荐使用 |
| macOS | ✅ 支持 | 需要额外权限 |
| Linux | ✅ 支持 | 取决于桌面环境 |

详细的平台兼容性说明请参考 [PLATFORM_COMPATIBILITY.md](./PLATFORM_COMPATIBILITY.md)。

## 许可证

MIT License - 详见 [LICENSE](./LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系。
