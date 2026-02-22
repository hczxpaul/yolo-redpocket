
from ultralytics import YOLO
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("正在下载 yolo26s.pt 基础模型...")
model = YOLO('yolo26s.pt')
logger.info("模型下载完成！")
