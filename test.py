from translation import translate_pdf_ai
import os

# 构造文件路径
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'test_pdfs/test5.pdf')  # 替换为你的文件名


#translate_pdf('1.pdf')
translate_pdf_ai(file_path)