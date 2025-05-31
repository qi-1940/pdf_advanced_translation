import sys
import os

def setup_poppler_path():
    """设置 poppler 路径"""
    try:
        # 获取程序所在目录
        if getattr(sys, 'frozen', False):
            # 打包后的程序
            base_path = os.path.dirname(sys.executable)
            internal_path = os.path.join(base_path, '_internal')
            if os.path.exists(internal_path):
                base_path = internal_path
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        # 将程序目录添加到 PATH
        os.environ['PATH'] = base_path + os.pathsep + os.environ.get('PATH', '')
        
        # 检查其他可能的位置
        possible_paths = [
            os.getcwd(),
            os.path.dirname(sys.executable),
            os.path.join(os.path.dirname(sys.executable), '_internal')
        ]
        
        for path in possible_paths:
            if path not in os.environ['PATH'].split(os.pathsep) and os.path.exists(path):
                os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
                
    except Exception:
        pass

# 设置路径
setup_poppler_path()

# 简单的异常处理
sys.excepthook = lambda *args: None

# 确保标准输出存在
try:
    if not hasattr(sys.stdout, 'encoding'):
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if not hasattr(sys.stderr, 'encoding'):
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
except Exception:
    pass 