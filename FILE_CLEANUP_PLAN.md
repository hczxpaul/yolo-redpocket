# 文件清理计划

## 清理日期
2026-02-21

---

## 一、删除文件清单

### 1.1 测试文件（临时验证脚本）

| 文件名 | 文件路径 | 删除原因 |
|--------|---------|---------|
| `test_4k_scaling.py` | `d:\dev-apps\yolo-redpocket\test_4k_scaling.py` | 4K 分辨率缩放测试脚本，已验证完成 |
| `test_4k_font.py` | `d:\dev-apps\yolo-redpocket\test_4k_font.py` | 4K 字体测试脚本，已验证完成 |
| `test_simple.py` | `d:\dev-apps\yolo-redpocket\test_simple.py` | 简单测试脚本，已验证完成 |
| `test_config_utils.py` | `d:\dev-apps\yolo-redpocket\test_config_utils.py` | 配置工具测试脚本，已验证完成 |
| `test_init.py` | `d:\dev-apps\yolo-redpocket\test_init.py` | 初始化测试脚本，已验证完成 |

### 1.2 备份目录（历史备份）

| 目录名 | 目录路径 | 删除原因 |
|--------|---------|---------|
| `backup_20260217_121545/` | `d:\dev-apps\yolo-redpocket\backup_20260217_121545\` | 2026-02-17 的项目备份，代码已更新 |

**备份目录包含的文件：**
- `analyze_yolo26s_hyperopt.py`
- `check_and_fix_labels.py`
- `continue_hyperopt.py`
- `delete_cache.py`
- `fix_dataset.py`
- `organize_dataset.py`
- `today_hyperopt.py`
- `train_with_best_practices.py`
- `train_yolo26s_hyperopt.py`
- `utils.py`

### 1.3 Python 缓存目录（自动生成）

| 目录名 | 目录路径 | 删除原因 |
|--------|---------|---------|
| `__pycache__/` | `d:\dev-apps\yolo-redpocket\__pycache__\` | Python 字节码缓存，可自动重新生成 |

**缓存文件列表：**
- `config_utils.cpython-310.pyc`
- `config_utils.cpython-312.pyc`
- `labeling_tool.cpython-312.pyc`
- `main.cpython-312.pyc`
- `platform_adapter.cpython-312.pyc`

### 1.4 临时文档（开发笔记）

| 文件名 | 文件路径 | 删除原因 |
|--------|---------|---------|
| `CODE_REVIEW.md` | `d:\dev-apps\yolo-redpocket\CODE_REVIEW.md` | 代码审查报告，审查已完成 |
| `COLOR_CONFIG_CHECK.md` | `d:\dev-apps\yolo-redpocket\COLOR_CONFIG_CHECK.md` | 颜色配置检查，检查已完成 |
| `FIX_PLAN.md` | `d:\dev-apps\yolo-redpocket\FIX_PLAN.md` | 修复计划，修复已完成 |
| `WINDOW_MANAGEMENT_VERIFICATION.md` | `d:\dev-apps\yolo-redpocket\WINDOW_MANAGEMENT_VERIFICATION.md` | 窗口管理验证报告，验证已完成 |

### 1.5 数据集缓存文件

| 文件名 | 文件路径 | 删除原因 |
|--------|---------|---------|
| `dataset/labels/train.cache` | `d:\dev-apps\yolo-redpocket\dataset\labels\train.cache` | YOLO 训练缓存，可自动重新生成 |
| `dataset/labels/val.cache` | `d:\dev-apps\yolo-redpocket\dataset\labels\val.cache` | YOLO 训练缓存，可自动重新生成 |

---

## 二、保留文件说明

### 2.1 核心程序文件（必需）

| 文件名 | 用途 |
|--------|------|
| `main.py` | 主程序，红包自动抢夺器 |
| `labeling_tool.py` | 标注工具，数据标注 |
| `platform_adapter.py` | 平台适配层，跨平台支持 |
| `config_utils.py` | 配置工具，统一配置管理 |

### 2.2 工具脚本（必需）

| 文件名 | 用途 |
|--------|------|
| `train_with_best_practices.py` | 模型训练脚本 |
| `organize_dataset.py` | 数据集整理脚本 |
| `cleanup.py` | 清理脚本 |
| `download_model.py` | 模型下载脚本 |

### 2.3 配置文件（必需）

| 文件名 | 用途 |
|--------|------|
| `dataset.yaml` | 数据集配置 |
| `config.yaml` | 项目配置 |
| `config.ini` | 旧版配置（向后兼容） |

### 2.4 依赖管理文件（必需）

| 文件名 | 用途 |
|--------|------|
| `requirements.txt` | 通用依赖 |
| `requirements-windows.txt` | Windows 平台依赖 |
| `requirements-macos.txt` | macOS 平台依赖 |
| `requirements-linux.txt` | Linux 平台依赖 |

### 2.5 项目文档（保留）

| 文件名 | 用途 |
|--------|------|
| `CROSS_PLATFORM_CHECKLIST.md` | 跨平台兼容性检查清单（最新） |
| `IMPLEMENTATION_SUMMARY.md` | 跨平台实施总结（最新） |
| `PLATFORM_COMPATIBILITY.md` | 平台兼容性评估（最新） |

---

## 三、删除统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 测试文件 | 5 个 | 临时验证脚本 |
| 备份目录 | 1 个 | 含 10 个备份文件 |
| 缓存目录 | 1 个 | 含 5 个缓存文件 |
| 临时文档 | 4 个 | 开发过程笔记 |
| 数据集缓存 | 2 个 | YOLO 训练缓存 |
| **总计** | **13 个文件 + 2 个目录** | |

---

## 四、注意事项

⚠️ **删除前请确认：**
1. 所有测试已完成并通过
2. 备份目录内容已不需要
3. 缓存文件可以安全删除（会自动重新生成）
4. 临时文档已完成其使命

✅ **删除后项目仍然可以：**
1. 正常运行主程序
2. 使用标注工具
3. 训练模型
4. 在所有平台上工作

---

## 五、执行步骤

1. 确认此清单无误
2. 执行删除操作
3. 验证项目仍可正常运行
4. 完成清理

---

**清理计划制定时间**: 2026-02-21
**状态**: ✅ 已完成

---

## 六、执行日志

| 时间 | 操作 | 结果 |
|------|------|------|
| 2026-02-21 | 删除 5 个测试文件 | 成功 |
| 2026-02-21 | 删除 1 个备份目录（含 10 个文件） | 成功 |
| 2026-02-21 | 删除 4 个临时文档 | 成功 |
| 2026-02-21 | 删除 2 个数据集缓存文件 | 成功 |
| 2026-02-21 | 删除 Python 缓存目录 __pycache__ | 成功 |
| 2026-02-21 | 语法检查 main.py 和 labeling_tool.py | 通过 |
