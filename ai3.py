import json
import fitz
import torch
import tempfile
from PIL import Image
from doclayout_yolo import YOLOv10
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os
from pdf2image import convert_from_path # type: ignore
from utils import get_resource_path

def single_pdf_to_png(pdf_path, output_folder, dpi=300, fmt='png', quality=100, page_limit=0):
    """
    将单个多页PDF转换为PNG（无进度条，保持原始比例）
    :param pdf_path: PDF文件路径
    :param output_folder: 输出目录
    :param dpi: 输出分辨率(默认300)
    :param fmt: 输出格式(png/jpeg)
    :param quality: 图像质量(1-100)
    :param page_limit: 限制转换的页数，0表示转换所有页 
    :return: (成功状态, 生成图片路径列表)
    """
    try:
        # 验证输入文件
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        # 创建输出目录
        os.makedirs(output_folder, exist_ok=True)
        
        # 确定实际转换的页数
        if page_limit > 0:
            print(f"正在转换: {os.path.basename(pdf_path)} -> {fmt.upper()} (DPI={dpi}, 前{page_limit}页)")
        else:
            print(f"正在转换: {os.path.basename(pdf_path)} -> {fmt.upper()} (DPI={dpi})")

        output_paths = []
        
        # 使用临时目录处理
        with tempfile.TemporaryDirectory() as temp_dir:
            # 转换PDF为图像（保持原始宽高比）
            convert_kwargs = {
                'pdf_path': pdf_path,
                'dpi': dpi,
                'output_folder': temp_dir,
                'fmt': fmt,
                'output_file': "page",
                'paths_only': True,
                'thread_count': 4,
                'use_pdftocairo': True,
            }
            
            # 如果指定了页数限制，添加相应参数
            if page_limit > 0:
                convert_kwargs['last_page'] = page_limit
                
            if fmt == 'jpeg':
                convert_kwargs['jpegopt'] = {"quality": quality}
            
            images = convert_from_path(**convert_kwargs)

            # 限制处理的图像数量
            if page_limit > 0:
                images = images[:page_limit]

            for i, img_path in enumerate(images):
                new_path = os.path.join(output_folder, f"page_{i+1:03d}.{fmt}")
                
                # 直接移动文件（保持原始尺寸）
                if fmt == 'png':
                    img = Image.open(img_path)
                    # 保存为无损PNG（保持原始分辨率）
                    img.save(new_path, format='PNG', dpi=(dpi, dpi))
                else:
                    os.rename(img_path, new_path)
                
                output_paths.append(new_path)
                print(f"已生成: {os.path.basename(new_path)}")

        print(f"转换完成! 共生成 {len(output_paths)} 张图像")
        return (True, output_paths)
    
    except Exception as e:
        print(f"转换失败: {str(e)}")
        return (False, [])

def analyze_document_layout(image_path, model_path, page_num,output_dir="output"):
    """
    文档布局分析完整流程：
    1. 加载模型
    2. 预测文档元素
    3. 提取分块位置信息
    4. 保存JSON结果到output/json子目录
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

    # 创建输出目录和json子目录
    json_dir = os.path.join(output_dir, "json")
    os.makedirs(json_dir, exist_ok=True)

    # 保存JSON结果到json子目录
    json_path = os.path.join(json_dir, f"{page_num}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"检测结果已保存至: {json_path}")
    
    return json_path

def generate_clean_pdf(image_paths, json_paths, output_pdf, original_pdf_path=None):
    """
    生成PDF文档：
    - 处理多个图片，每个图片一页
    - 如果检测到表格/公式/图像，则添加这些元素
    - 如果未检测到，则生成有效的空白PDF
    - 保持与原PDF相同的页面尺寸
    """
    try:
        # 获取原始PDF尺寸
        if original_pdf_path:
            with fitz.open(original_pdf_path) as input_pdf:
                # 使用第一页的尺寸作为所有页面的尺寸
                first_page = input_pdf[0]
                pdf_width = first_page.rect.width
                pdf_height = first_page.rect.height
                page_size = (pdf_width, pdf_height)
        else:
            page_size = A4
            pdf_width, pdf_height = A4
        
        # 创建PDF画布
        c = canvas.Canvas(output_pdf, pagesize=page_size)
        
        for img_path, json_path in zip(image_paths, json_paths):
            # 检查是否有检测结果
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    detections = json.load(f)
                
                target_elements = [det for det in detections if det['class'] in [
                    'figure', 'table', 'isolate_formula', 'formula_caption']]
                
                if target_elements:
                    # 处理检测到的元素
                    original_img = Image.open(img_path)
                    img_width, img_height = original_img.size
                    
                    # 计算缩放比例
                    scale_x = pdf_width / img_width
                    scale_y = pdf_height / img_height
                    
                    for i, det in enumerate(target_elements):
                        x1, y1, x2, y2 = map(int, det['bbox_pixels'])
                        cropped = original_img.crop((x1, y1, x2, y2))
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                            cropped.save(temp_file.name, quality=95)
                            # 计算位置
                            pdf_x = x1 * scale_x
                            pdf_y = pdf_height - (y2 * scale_y)  # PDF坐标系统从底部开始
                            c.drawImage(
                                ImageReader(temp_file.name),
                                pdf_x, pdf_y,
                                width=(x2-x1)*scale_x,
                                height=(y2-y1)*scale_y,
                                preserveAspectRatio=True
                            )
                        os.unlink(temp_file.name)
            
            # 添加新页面
            c.showPage()
        
        c.save()
        
        print(f"成功生成PDF: {output_pdf}")
        return True
    
    except Exception as e:
        print(f"生成PDF时出错: {str(e)}")
        return False

def process_pdf_to_final_pdf(pdf_path, model_path, output_dir="output", dpi=300, page_num=0):
    """
    完整处理流程：
    1. PDF转PNG
    2. 对每页进行布局分析
    3. 生成最终PDF
    """
    # 创建必要的目录结构
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "json"), exist_ok=True)
    
    # 第一步：PDF转PNG
    print("\n" + "="*50)
    print("第一步：将PDF转换为PNG图像")
    print("="*50)
    image_dir = os.path.join(output_dir, "images")
    success, image_paths = single_pdf_to_png(
        pdf_path=pdf_path,
        output_folder=image_dir,
        dpi=dpi,
        page_limit=page_num if page_num > 0 else 0  # 传递页数限制
    )
    
    if not success:
        return False
    
    # 第二步：文档布局分析
    print("\n" + "="*50)
    print("第二步：文档布局分析")
    print("="*50)
    json_paths = []
    current_page_num = 0
    for img_path in image_paths:
        print(f"\n正在分析: {os.path.basename(img_path)}")
        json_path = analyze_document_layout(img_path, model_path, current_page_num, output_dir)
        current_page_num += 1
        json_paths.append(json_path)
    
    # 第三步：生成最终PDF
    print("\n" + "="*50)
    print("第三步：生成中间PDF")
    print("="*50)
    final_pdf = os.path.join(output_dir, "temp.pdf")
    generate_clean_pdf(image_paths, json_paths, final_pdf, original_pdf_path=pdf_path)
    
    print("\n" + "="*50)
    print("预处理完成！")
    print("="*50)
    
    return True

def ai_pdf_process(pdf_path, page_num=0):
    # 配置参数
    MODEL_PATH = get_resource_path("resources/doclayout_yolo_docstructbench_imgsz1024.pt")  # 模型路径
    OUTPUT_DIR = "output"  # 输出目录
    DPI = 300  # PDF转换分辨率
    
    # 执行完整流程
    return process_pdf_to_final_pdf(
        pdf_path=pdf_path,
        model_path=MODEL_PATH,
        output_dir=OUTPUT_DIR,
        dpi=DPI,
        page_num=page_num
    )