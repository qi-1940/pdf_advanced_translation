import cv2
import json
from doclayout_yolo import YOLOv10
import torch
import os

def analyze_document_layout(image_path, model_path, output_dir="output"):
    """
    文档布局分析完整流程：
    1. 加载模型
    2. 预测文档元素
    3. 提取分块位置信息
    4. 保存JSON结果和可视化标注图
    """
    # 初始化模型
    model = YOLOv10(model_path)

    # 执行预测
    det_res = model.predict(
        image_path,
        imgsz=1024,
        conf=0.2,
        device="cuda:0" if torch.cuda.is_available() else "cpu"  # 自动切换设备
    )

    # 提取检测结果
    detections = det_res[0]
    results = []

    # 解析每个检测到的元素
    for det in detections:
        # 获取边界框（绝对坐标和归一化坐标）
        bbox = det.boxes.xyxy[0].tolist()       # [x1, y1, x2, y2] 像素坐标
        bbox_norm = det.boxes.xyxyn[0].tolist() # [x1_norm, y1_norm, x2_norm, y2_norm] 归一化坐标
        
        # 构建结果字典
        result = {
            "class": det.names[int(det.boxes.cls[0])],  # 类别名称
            "class_id": int(det.boxes.cls[0]),          # 类别ID
            "confidence": float(det.boxes.conf[0]),      # 置信度
            "bbox_pixels": [round(x, 1) for x in bbox],  # 保留1位小数的像素坐标
            "bbox_normalized": [round(x, 4) for x in bbox_norm],  # 归一化坐标
            "width_pixels": round(bbox[2] - bbox[0], 1), # 区域宽度
            "height_pixels": round(bbox[3] - bbox[1], 1)  # 区域高度
        }
        results.append(result)
        
        # 创建输出目录
        
        os.makedirs(output_dir, exist_ok=True)

        # 保存JSON结果
        json_path = os.path.join(output_dir, "layout_analysis.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"检测结果已保存至: {json_path}")

        # 可视化标注并保存
        annotated_img = detections.plot(
            pil=True,
            line_width=3,
            font_size=16,
            labels=True,
            conf=True  # 显示置信度
        )
        img_path = os.path.join(output_dir, "annotated_result.jpg")
        cv2.imwrite(img_path, cv2.cvtColor(annotated_img, cv2.COLOR_RGB2BGR))
        print(f"标注图像已保存至: {img_path}")
        
    return results

def ai_blocks(png_path):
    
    # 输入参数
    MODEL_PATH = "doclayout_yolo_docstructbench_imgsz1024.pt"  # 或自定义模型路径
    
    # 执行分析
    return analyze_document_layout(png_path, MODEL_PATH)