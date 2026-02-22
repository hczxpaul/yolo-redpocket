import os
import shutil
import random
from pathlib import Path

def organize_dataset():
    dataset_dir = Path('dataset')
    images_dir = dataset_dir / 'images'
    labels_dir = dataset_dir / 'labels'
    
    train_images_dir = images_dir / 'train'
    val_images_dir = images_dir / 'val'
    train_labels_dir = labels_dir / 'train'
    val_labels_dir = labels_dir / 'val'
    
    train_images_dir.mkdir(parents=True, exist_ok=True)
    val_images_dir.mkdir(parents=True, exist_ok=True)
    train_labels_dir.mkdir(parents=True, exist_ok=True)
    val_labels_dir.mkdir(parents=True, exist_ok=True)
    
    print("正在扫描新增的图片和标签...")
    
    loose_images = list(images_dir.glob('*.png')) + list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.jpeg'))
    loose_labels = list(labels_dir.glob('*.txt'))
    
    print(f"找到 {len(loose_images)} 张松散图片")
    print(f"找到 {len(loose_labels)} 个松散标签")
    
    matched_files = []
    unmatched_images = []
    unmatched_labels = []
    
    for img_path in loose_images:
        label_path = labels_dir / (img_path.stem + '.txt')
        if label_path.exists():
            matched_files.append((img_path, label_path))
        else:
            unmatched_images.append(img_path)
    
    for label_path in loose_labels:
        img_found = False
        for ext in ['.png', '.jpg', '.jpeg']:
            if (images_dir / (label_path.stem + ext)).exists():
                img_found = True
                break
        if not img_found:
            unmatched_labels.append(label_path)
    
    print(f"匹配成功: {len(matched_files)} 对")
    print(f"未匹配图片: {len(unmatched_images)}")
    print(f"未匹配标签: {len(unmatched_labels)}")
    
    if unmatched_images:
        print("\n未匹配的图片:")
        for img in unmatched_images[:10]:
            print(f"  - {img.name}")
        if len(unmatched_images) > 10:
            print(f"  ... 还有 {len(unmatched_images) - 10} 张")
    
    random.shuffle(matched_files)
    split_idx = int(len(matched_files) * 0.8)
    train_files = matched_files[:split_idx]
    val_files = matched_files[split_idx:]
    
    print(f"\n将 {len(train_files)} 对分配到训练集")
    print(f"将 {len(val_files)} 对分配到验证集")
    
    for img_path, label_path in train_files:
        shutil.move(str(img_path), str(train_images_dir / img_path.name))
        shutil.move(str(label_path), str(train_labels_dir / label_path.name))
    
    for img_path, label_path in val_files:
        shutil.move(str(img_path), str(val_images_dir / img_path.name))
        shutil.move(str(label_path), str(val_labels_dir / label_path.name))
    
    print("\n数据集整理完成！")
    
    train_count = len(list(train_images_dir.glob('*.png'))) + len(list(train_images_dir.glob('*.jpg')))
    val_count = len(list(val_images_dir.glob('*.png'))) + len(list(val_images_dir.glob('*.jpg')))
    print(f"训练集图片: {train_count}")
    print(f"验证集图片: {val_count}")
    
    cache_files = list(images_dir.glob('*.cache')) + list(labels_dir.glob('*.cache'))
    for cache in cache_files:
        try:
            cache.unlink()
            print(f"已删除缓存文件: {cache.name}")
        except:
            pass

if __name__ == '__main__':
    organize_dataset()
