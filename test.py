from translation import translate_pdf_ai
from translation import add_text_block_rect_check
import os
from old_codes.ai2 import ai_blocks
import fitz 

# 构造文件路径
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'test_pdfs/test2.pdf')  # 替换为你的文件名

translate_pdf_ai(file_path,1)
#print(ai_blocks('output/images/page_002.png'))
#print(add_text_block_rect_check(fitz.Rect(85.07122904663086,434.60169581909184,538.9432026306152,475.8884529418945),\
#                                [fitz.Rect(84.59497304077149,347.665197454834,540.1933746459961,526.0627703063965)]))