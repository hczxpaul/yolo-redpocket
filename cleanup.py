import os
import shutil
from pathlib import Path

def cleanup_project():
    """
    清理项目临时文件
    """
    project_dir = Path(__file__).parent
    print(f"开始清理项目: {project_dir}")
    print("-" * 60)
    
    # 1. 清理 __pycache__ 目录
    pycache_dirs = list(project_dir.rglob("__pycache__"))
    if pycache_dirs:
        print(f"[1/5] 发现 {len(pycache_dirs)} 个 __pycache__ 目录")
        for cache_dir in pycache_dirs:
            try:
                shutil.rmtree(cache_dir)
                print(f"  ✓ 删除: {cache_dir.relative_to(project_dir)}")
            except Exception as e:
                print(f"  ✗ 删除失败 {cache_dir}: {e}")
    else:
        print(f"[1/5] 没有发现 __pycache__ 目录")
    
    # 2. 清理 .pyc 文件
    pyc_files = list(project_dir.rglob("*.pyc"))
    if pyc_files:
        print(f"\n[2/5] 发现 {len(pyc_files)} 个 .pyc 文件")
        for pyc_file in pyc_files:
            try:
                pyc_file.unlink()
                print(f"  ✓ 删除: {pyc_file.relative_to(project_dir)}")
            except Exception as e:
                print(f"  ✗ 删除失败 {pyc_file}: {e}")
    else:
        print(f"\n[2/5] 没有发现 .pyc 文件")
    
    # 3. 清理 .pyo 文件
    pyo_files = list(project_dir.rglob("*.pyo"))
    if pyo_files:
        print(f"\n[3/5] 发现 {len(pyo_files)} 个 .pyo 文件")
        for pyo_file in pyo_files:
            try:
                pyo_file.unlink()
                print(f"  ✓ 删除: {pyo_file.relative_to(project_dir)}")
            except Exception as e:
                print(f"  ✗ 删除失败 {pyo_file}: {e}")
    else:
        print(f"\n[3/5] 没有发现 .pyo 文件")
    
    # 4. 清理 .pyd 文件（Windows编译文件）
    pyd_files = list(project_dir.rglob("*.pyd"))
    if pyd_files:
        print(f"\n[4/5] 发现 {len(pyd_files)} 个 .pyd 文件")
        for pyd_file in pyd_files:
            try:
                pyd_file.unlink()
                print(f"  ✓ 删除: {pyd_file.relative_to(project_dir)}")
            except Exception as e:
                print(f"  ✗ 删除失败 {pyd_file}: {e}")
    else:
        print(f"\n[4/5] 没有发现 .pyd 文件")
    
    # 5. 检查备份目录（不自动删除，提示用户）
    backup_dirs = [d for d in project_dir.iterdir() if d.is_dir() and ('backup' in d.name.lower() or 'bak' in d.name.lower())]
    if backup_dirs:
        print(f"\n[5/5] 发现 {len(backup_dirs)} 个备份目录（建议手动检查）:")
        for backup_dir in backup_dirs:
            size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
            size_mb = size / (1024 * 1024)
            print(f"  - {backup_dir.name} ({size_mb:.1f} MB)")
    else:
        print(f"\n[5/5] 没有发现备份目录")
    
    print("\n" + "-" * 60)
    print("清理完成！")
    print("\n提示:")
    print("  - 如需清理备份文件夹，请手动确认后删除")
    print("  - 数据集文件未被清理")


if __name__ == "__main__":
    cleanup_project()
