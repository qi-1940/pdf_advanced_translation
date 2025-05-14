#调用翻译函数的方法：
#from translation import translate_pdf
#translate_pdf(pdf_path)
#如果翻译成功，返回1，否则返回0

import sys
import hashlib
import hmac
import json
import requests
import time
import fitz 
import os
from ai2 import ai_blocks

def baidu_translate(query):
    app_id = '20250415002334058'
    secret_key = 'SVA9Lv0mE90NQsj76c0W'
    url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
    salt = str(round(time.time()))  # 随机数，这里使用了当前时间戳（秒级）
    sign_str = app_id + query + salt + secret_key
    md5_obj = hashlib.md5()
    md5_obj.update(sign_str.encode('utf-8')) # 对字符串做md5加密，注意需32位小写，即结果为'a1a7461d92e5194c5cae3182b5b24de1'
    sign =md5_obj.hexdigest()
    params = {
        'appid': app_id,
        'q': query,
        'from': "en",
        'to': "zh",
        'salt': salt,
        'sign': sign,
    }
    # Build request
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    # Send request
    r = requests.post(url, params, headers=headers).json()
    # Show response
    return r['trans_result']

def to_plain_block(block):
    plain_block=''
    for every_char in block:
        if(every_char != '\n'):
            plain_block+=every_char
    return plain_block

def is_english_letter(char):
    return len(char) == 1 and char.isalpha() and char.isascii()

def is_close(float1,float2):
    if abs(float1-float2)<=10:
        return 1
    return 0

def bbox_transform(bbox,x,y):
    bbox[0] = bbox[0]*x
    bbox[2] = bbox[2]*x
    bbox[1] = bbox[1]*y
    bbox[3] = bbox[3]*y
    return bbox
    
def translate_pdf_ai(input_pdf_path):
    with fitz.open(input_pdf_path) as input_pdf:
        output_pdf=fitz.Document()
        for input_pdf_page in input_pdf:
            
            #获取当前页面的宽度和高度
            input_pdf_page_width = input_pdf_page.rect.width  # 获取宽度（点）
            input_pdf_page_height = input_pdf_page.rect.height  # 获取高度（点）
            
            #在要输出的文档中添加页面
            output_pdf_current_page=output_pdf.new_page(width=input_pdf_page_width, height=input_pdf_page_height)
            output_pdf_current_page.clean_contents()
            
            #把当前页面转化为temp.png
            input_pdf_page_pixmap=input_pdf_page.get_pixmap(dpi=300)
            input_pdf_page_pixmap.save('temp.png',output='png')
            
            #获取当前页面的所有文本块的pymupdf坐标，接着翻译、填充到要输出的文件的页面
            blocks=ai_blocks('temp.png')
            for each_block in blocks:
                if each_block["class_id"]==1 or each_block["class_id"]==2 :
                    each_block_bbox=bbox_transform(each_block["bbox_normalized"],input_pdf_page_width,input_pdf_page_height)
                    each_block_rect=fitz.Rect(each_block_bbox[0],\
                                            each_block_bbox[1],\
                                            each_block_bbox[2],\
                                            each_block_bbox[3])
                if  each_block["class"]=='title':
                    each_block_bbox=bbox_transform(each_block["bbox_normalized"],input_pdf_page_width,input_pdf_page_height)
                    each_block_rect=fitz.Rect(each_block_bbox[0]-20,\
                                            each_block_bbox[1],\
                                            each_block_bbox[2]+5,\
                                            each_block_bbox[3])
                
                each_block_dict_blocks = (input_pdf_page.get_text("dict", clip=each_block_rect))['blocks']
                
                if each_block_dict_blocks != [] and each_block_dict_blocks[0]['type']==0:
                    each_block_fontsize = each_block_dict_blocks[0]['lines'][0]['spans'][0]['size']
                    each_block_text=to_plain_block(input_pdf_page.get_text('text',clip=each_block_rect))
                    
                    each_block_tran=baidu_translate(each_block_text)[0]['dst']
                    print(each_block_tran,end='\n\n')
                    output_pdf_current_page.draw_rect(each_block_rect, color=(1, 0, 0)) 
                    
                    while output_pdf_current_page.insert_textbox(\
                        rect=each_block_rect,\
                        buffer=each_block_tran,\
                        fontname='china-ss',\
                        fontsize=each_block_fontsize) <0:
                        each_block_rect[0]+=1
                        each_block_rect[1]+=1
                        each_block_rect[2]+=1
                        each_block_rect[3]+=1
                        each_block_fontsize-=1

    output_pdf.save(f"{input_pdf_path}-中文翻译版.pdf")
    output_pdf.close()
    os.remove('temp.png')

    return 1