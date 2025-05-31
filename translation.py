# -*- coding: utf-8 -*-
'''
调用翻译函数的方法：
translate_pdf_ai(pdf_path, page_num=-1)
page_num为-1时，翻译所有页数，否则翻译指定页数
如果翻译成功，返回翻译文件路径，否则返回0
'''
import sys
import hashlib
import json
import requests
import time
import fitz
import os
import shutil
from ai3 import ai_pdf_process
import requests
from utils import get_resource_path, add_text_block_rect_check, rect_area

def to_plain_block(block):
    '''
    删除字符串前后的空格以及其中的任何换行符
    '''
    plain_block=''
    for every_char in block:
        if(every_char != '\n'):
            plain_block+=every_char
    return plain_block.strip()

def bbox_transform(bbox,x,y):
    
    #传入的参数是pdf页面转图片后，识别出来的相对矩形位置(bbox),
    #以及pdf页面的宽度和长度
    
    bbox[0] = bbox[0]*x
    bbox[2] = bbox[2]*x
    bbox[1] = bbox[1]*y
    bbox[3] = bbox[3]*y
    return bbox

def is_tag_textbox(tag_str):
    if tag_str=='title' or \
        tag_str=='abandon' or \
        tag_str=='table_caption' or \
        tag_str=='figure_caption' or \
        tag_str=='plain text':
        return 1
    else:
        return 0 

def is_all_english_letters(text):
    return all('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in text)

def baidu_translate(query):
    app_id = '20250530002369626'
    secret_key = 'my7HZRD2d4wbUPwf5NZf'
    url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
    salt = str(round(time.time()))
    sign_str = app_id + query + salt + secret_key
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    params = {
        'appid': app_id,
        'q': query,
        'from': "en",
        'to': "zh",
        'salt': salt,
        'sign': sign,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post(url, data=params, headers=headers).json()
    try:
        return r['trans_result']
    except KeyError:
        print(r.get('error_msg'))
        return 0

def translate_pdf_ai(input_pdf_path, page_num=0):
    #预处理（除了文字块外的所有处理）
    if ai_pdf_process(input_pdf_path, page_num) == False:
        return 0
    
    print("\n" + "="*50)
    print("第四步：文字块处理")
    print("="*50)

    with fitz.open('output/temp.pdf') as temp_pdf:
        with fitz.open(input_pdf_path) as input_pdf:
            #要翻译的页数
            if page_num==0:
                page_num=temp_pdf.page_count

            temp_page_num=1
            
            for temp_pdf_page in temp_pdf:
                if temp_page_num>page_num:
                    break

                print(f'正在处理\t第{temp_page_num}页，\t共{temp_pdf.page_count}页')
                input_pdf_page=input_pdf[temp_page_num-1]
                temp_page_text_block_rects=[]
                temp_pdf_page.insert_font(fontfile=get_resource_path('resources/msyh.ttf'),fontname='msyh')

                #获取当前页面的宽度和高度
                temp_pdf_page_width = temp_pdf_page.rect.width  # 获取宽度（点）
                temp_pdf_page_height = temp_pdf_page.rect.height  # 获取高度（点）

                #得到每个pdf页面的块列表
                with open(f"output/json/{temp_page_num-1}.json", "r", encoding="utf-8") as temp_page_json_file:
                    temp_page_blocks = json.load(temp_page_json_file)
                temp_page_num+=1

                #得到当前页面的文字块列表
                temp_page_text_blocks = [temp_page_block for temp_page_block in temp_page_blocks if is_tag_textbox(temp_page_block['class']) == 1]
                
                #遍历当前页面的所有文字块，得到文字块rect列表temp_page_text_block_rects
                for each_temp_page_text_block in temp_page_text_blocks:
                    #得到当前文字块的pymupdf坐标
                    each_block_bbox=bbox_transform(each_temp_page_text_block["bbox_normalized"],temp_pdf_page_width,temp_pdf_page_height)
                    each_block_rect=fitz.Rect(each_block_bbox[0],each_block_bbox[1],each_block_bbox[2],each_block_bbox[3])
                    if rect_area(each_block_rect)<10:#跳过面积小于10的块
                        continue
                    check_output = add_text_block_rect_check(each_block_rect, temp_page_text_block_rects)
                    if check_output[0] == 0:  # 没有重叠
                        temp_page_text_block_rects.append(each_block_rect)
                    else:
                        if not check_output[1]:  # 返回空列表，说明temp_rect不是最大的
                            pass
                        else:  # 返回了重叠矩形的索引列表
                            # 从后往前删除重叠的矩形，避免索引变化
                            for idx in sorted(check_output[1], reverse=True):
                                del temp_page_text_block_rects[idx]
                            # 添加新的矩形
                            temp_page_text_block_rects.append(each_block_rect)
                
                for each_ready_rect in temp_page_text_block_rects:
                    #获取这个block的详细信息以获得字号
                    each_block_dict_blocks = (input_pdf_page.get_text("dict", clip=each_ready_rect))['blocks']
                    
                    #文字块的字号提取
                    if each_block_dict_blocks != [] and each_block_dict_blocks[0]['type']==0:
                        each_block_fontsize = each_block_dict_blocks[0]['lines'][0]['spans'][0]['size']
                    else:
                        each_block_fontsize=10
                    
                    #识别文字块中的英文
                    each_block_text=to_plain_block(input_pdf_page.get_text('text',clip=each_ready_rect))

                    #获取翻译后的文本
                    if(is_all_english_letters(each_block_text)):
                        each_block_tran=each_block_text
                    else:
                        each_block_tran=baidu_translate(each_block_text)
                        if(each_block_tran==0):
                            continue
                        else:
                            each_block_tran=each_block_tran[0]['dst']
                    
                    #插入翻译后的文本
                    while temp_pdf_page.insert_textbox(rect=each_ready_rect,buffer=each_block_tran,fontname='msyh',\
                        fontsize=each_block_fontsize-1) <0:
                        each_ready_rect[0]-=1
                        each_ready_rect[1]-=1
                        each_ready_rect[2]+=1
                        each_ready_rect[3]+=1
                        each_block_fontsize-=1
                        
        output_path = f"{input_pdf_path}-中文翻译版.pdf"
        temp_pdf.save(output_path)
    return output_path
