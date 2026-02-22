import sys
import yaml
import json
import torch
import shutil
import csv
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_device():
    if torch.cuda.is_available():
        device = 'cuda'
        logger.info(f"使用GPU加速: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'
        logger.info("使用 Apple MPS (Apple Silicon) 加速")
    else:
        try:
            import rknnlite
            device = 'rknpu'
            logger.info("使用 Rockchip RKNPU 加速")
        except ImportError:
            device = 'cpu'
            logger.info("使用CPU运行")
    return device


def main():
    logger.info("=" * 100)
    logger.info("YOLO26s 模型训练 - 使用最佳实践参数")
    logger.info("=" * 100)
    
    device = get_device()
    
    best_params = {
        'epochs': 200,
        'batch': 16,
        'imgsz': 800,
        'patience': 60,
        'lr0': 0.0008,
        'lrf': 0.01,
        'weight_decay': 0.0008,
        'optimizer': 'AdamW',
        'mixup': 0.12,
        'copy_paste': 0.25,
        'mosaic': 1.0,
        'cos_lr': True,
        'close_mosaic': 15,
    }
    
    logger.info("\n最佳训练参数:")
    for key, value in best_params.items():
        logger.info(f"  {key}: {value}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_yaml = 'dataset.yaml'
    model = YOLO('yolo26s.pt')
    
    logger.info("\n开始训练...")
    start_time = datetime.now()
    
    results = model.train(
        data=data_yaml,
        epochs=best_params['epochs'],
        batch=best_params['batch'],
        imgsz=best_params['imgsz'],
        patience=best_params['patience'],
        lr0=best_params['lr0'],
        lrf=best_params['lrf'],
        weight_decay=best_params['weight_decay'],
        optimizer=best_params['optimizer'],
        mixup=best_params['mixup'],
        copy_paste=best_params['copy_paste'],
        mosaic=best_params['mosaic'],
        cos_lr=best_params['cos_lr'],
        close_mosaic=best_params['close_mosaic'],
        amp=True,
        workers=8,
        device=device,
        project='runs/train',
        name=f'yolo26s_best_{timestamp}',
        exist_ok=False,
        seed=42,
        deterministic=True,
    )
    
    end_time = datetime.now()
    training_time = (end_time - start_time).total_seconds() / 60
    
    logger.info("\n" + "=" * 100)
    logger.info("训练完成!")
    logger.info("=" * 100)
    logger.info(f"训练时间: {training_time:.2f} 分钟")
    
    val_results = model.val(
        data=data_yaml,
        split='val',
        imgsz=best_params['imgsz'],
        device=device,
        verbose=True
    )
    
    logger.info("\n验证结果:")
    logger.info(f"  mAP50:        {float(val_results.box.map50):.4f}")
    logger.info(f"  mAP50-95:     {float(val_results.box.map):.4f}")
    logger.info(f"  Precision:    {float(val_results.box.mp):.4f}")
    logger.info(f"  Recall:       {float(val_results.box.mr):.4f}")
    
    best_model_path = Path(results.save_dir) / 'weights' / 'best.pt'
    target_path = Path('models') / 'yolo26s_best_latest.pt'
    best_target_path = Path('models') / 'best.pt'
    
    if best_model_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_model_path, target_path)
        logger.info(f"\n最佳模型已保存到: {target_path}")
        
        shutil.copy2(best_model_path, best_target_path)
        logger.info(f"最佳模型已复制到: {best_target_path}")
        
        config_file = Path('models') / 'yolo26s_best_config.yaml'
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump({
                'timestamp': timestamp,
                'training_time_min': training_time,
                'params': best_params,
                'metrics': {
                    'mAP50': float(val_results.box.map50),
                    'mAP50-95': float(val_results.box.map),
                    'precision': float(val_results.box.mp),
                    'recall': float(val_results.box.mr)
                }
            }, f, allow_unicode=True)
        logger.info(f"训练配置已保存到: {config_file}")
    
    logger.info("\n" + "=" * 100)
    logger.info("所有任务完成!")
    logger.info("=" * 100)


if __name__ == '__main__':
    main()
