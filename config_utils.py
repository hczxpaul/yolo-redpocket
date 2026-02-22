import logging
from pathlib import Path
import yaml

DEFAULT_CLASSES = [
    'red_packet', 'open_button', 'amount_text', 
    'close_button', 'back_button', 'opened_red_packet', 'play_button'
]

logger = logging.getLogger(__name__)


def load_classes_from_config(config_path='dataset.yaml', logger_instance=None):
    log = logger_instance or logger
    
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            log.warning(f"配置文件不存在: {config_path}，使用默认类别")
            return DEFAULT_CLASSES.copy()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if 'names' in config:
            if isinstance(config['names'], dict):
                classes = [config['names'][i] for i in sorted(config['names'].keys())]
                log.info(f"从配置文件加载了 {len(classes)} 个类别")
                return classes
            elif isinstance(config['names'], list):
                log.info(f"从配置文件加载了 {len(config['names'])} 个类别")
                return config['names']
        
        log.warning("配置文件中未找到 names 字段，使用默认类别")
        return DEFAULT_CLASSES.copy()
        
    except Exception as e:
        log.warning(f"加载配置文件失败: {e}，使用默认类别")
        return DEFAULT_CLASSES.copy()
