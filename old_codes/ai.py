'''
# 安装核心依赖
!pip install doclayout-yolo opencv-python numpy Pillow

# 安装 PyTorch（CUDA 11.8 版本）
!pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 可选：安装 PDF 支持库
!pip install pdf2image

# 使用 pip 安装
!pip install huggingface_hub


# 卸载现有 PyTorch
!pip uninstall torch torchvision torchaudio


# 安装 CUDA 11.8 版本
!pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

!nvidia-smi 

!pip install --upgrade jupyter ipywidgets
'''
import cv2
from doclayout_yolo import YOLOv10

# Load the pre-trained model
model = YOLOv10("doclayout_yolo_docstructbench_imgsz1024.pt")

# Perform prediction
det_res = model.predict(
    "1.pdf",  # Image to predict                        
    imgsz=1024,        # Prediction image size
    conf=0.2,          # Confidence threshold
    device="cpu"    # Device to use (e.g., 'cuda:0' or 'cpu')
)

# Annotate and save the result
annotated_frame = det_res[0].plot(pil=True, line_width=5, font_size=20)
cv2.imwrite("result.jpg", annotated_frame)
