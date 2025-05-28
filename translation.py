'''
调用翻译函数的方法：
from translation import translate_pdf_ai
translate_pdf_ai(pdf_path)
如果翻译成功，返回1，否则返回0
'''
import sys
import hashlib
import hmac
import json
import requests
import time
import fitz 
import os
import shutil
from ai3 import ai_pdf_process

import hashlib
import time
import requests
import re

def is_segments_overlapping(seg1,seg2):
    '''
    判断两个线段是否重叠，重叠返回1
    '''
    if seg1[1]>=seg1[0]:
        s1x1=seg1[1]
        s1x0=seg1[0]
    else:
        s1x1=seg1[0]
        s1x0=seg1[1]

    if seg2[1]>=seg2[0]:
        s2x1=seg2[1]
        s2x0=seg2[0]
    else:
        s2x1=seg2[0]
        s2x0=seg2[1]

    if (s2x0>=s1x0 and s2x0<=s1x1) or (s2x1>=s1x0 and s2x1<=s1x1):
        return 1
    else:
        return 0

def is_rects_overlapping(rect1, rect2):
    """
    判断两个矩形是否无重合区域
    
    参数:
        rect1: fitz.Rect 对象
        rect2: fitz.Rect 对象
    
    返回:
        1: 两个矩形有重合
        0: 两个矩形无重合
    """
    r1s1=(rect1.x0,rect1.x1)
    r1s2=(rect1.y0,rect1.y1)

    r2s1=(rect2.x0,rect2.x1)
    r2s2=(rect2.y0,rect2.y1)
    
    if is_segments_overlapping(r1s1,r2s1) and is_segments_overlapping(r1s2,r2s2):
        return 1
    return 0

def rect_size(rect):
    return abs(rect.x0-rect.x1)+abs(rect.y0-rect.y1)

def add_text_block_rect_check(temp_rect,rect_lists):
    '''
    检查temp_rect和rect_lists里的元素有无冲突，
    如果冲突，返回(1,num)num是冲突的rect的索引，否则返回(0,-1)
    '''
    num=-1
    
    for rect in rect_lists:
        num+=1
        if is_rects_overlapping(temp_rect,rect):
            if rect_size(rect)<rect_size(temp_rect):
                return (1,num)
            else :
                return (1,-1)
    return (0,-1)

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

def draw_custom_rect(page, rect):
    shape = page.new_shape()
    # 绘制矩形（同时填充和描边）
    shape.draw_rect(rect)
    shape.finish()
    
    # 提交到页面
    shape.commit()

def is_all_english_letters(text):
    return all('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in text)

def baidu_translate(query):
    app_id = '20250425002342076'
    secret_key = 'pT1QnotEaWuvpefNLgce'
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

def insert_mixed_text(page, rect, text, font_en, font_cn, base_fontsize):
    """
    在指定矩形区域绘制中英文混合文本（自动区分字体）
    
    参数:
        page: PDF页面对象
        rect: 文本框区域(fitz.Rect)
        text: 要绘制的字符串(可包含中英文)
        font_en: 英文字体
        font_cn: 中文字体
        base_fontsize: 基础字号
    """
    draw_custom_rect(page,rect)
    writer = fitz.TextWriter(rect)
    current_pos = fitz.Point(rect.x0, rect.y0)  # 起始位置
    line_height = base_fontsize * 1.2  # 行高
    
    # 智能分割混合字符串（处理中英文交界情况）
    segments = []
    current_seg = ""
    current_is_chinese = None
    
    for char in text:
        is_chinese = "\u4e00" <= char <= "\u9fff"  # 判断是否为中文字符
        
        if current_is_chinese is None:
            current_is_chinese = is_chinese
            
        if is_chinese == current_is_chinese:
            current_seg += char
        else:
            segments.append((current_seg, current_is_chinese))
            current_seg = char
            current_is_chinese = is_chinese
    
    if current_seg:  # 添加最后一个分段
        segments.append((current_seg, current_is_chinese))

    # 逐段绘制
    for segment, is_chinese in segments:
        font = font_cn if is_chinese else font_en
        fontsize = base_fontsize * 0.95 if is_chinese else base_fontsize  # 中文略小
        
        # 计算当前段文本宽度
        text_width = font.text_length(segment, fontsize=fontsize)
        
        # 检查是否需要换行
        if current_pos.x + text_width > rect.x1:
            current_pos = fitz.Point(rect.x0, current_pos.y + line_height)
        
        # 添加文本段
        writer.append(
            pos=current_pos,
            text=segment,
            font=font,
            fontsize=fontsize
        )
        
        # 更新位置（向右移动）
        current_pos += fitz.Point(text_width, 0)
    
    # 写入页面
    writer.write_text(page, rect)

def translate_pdf_ai(input_pdf_path,page_num=-1):
    #预处理（除了文字块外的所有处理）
    #if ai_pdf_process(input_pdf_path) == False:
    #    print('预处理失败！')
    #    return 0
    
    print("\n" + "="*50)
    print("第二阶段：文字块处理")
    print("="*50)


    with fitz.open('output/temp.pdf') as temp_pdf:
        with fitz.open(input_pdf_path) as input_pdf:
            with open("temp.txt", "a", encoding="utf-8") as temp_txt:
                
                #要翻译的页数
                if page_num==-1:
                    page_num=temp_pdf.page_count

                temp_page_num=0
                
                for temp_pdf_page in temp_pdf:
                    if temp_page_num>page_num:
                        continue

                    print(f'正在处理第{temp_page_num}页，\t共{temp_pdf.page_count}页')
                    temp_txt.write(f'temp page num:{temp_page_num}\n')
                    input_pdf_page=input_pdf[temp_page_num]
                    temp_page_text_block_rects=[]
                    temp_pdf_page.insert_font(fontfile='msyh.ttf',fontname='msyh')

                    #获取当前页面的宽度和高度
                    temp_pdf_page_width = temp_pdf_page.rect.width  # 获取宽度（点）
                    temp_pdf_page_height = temp_pdf_page.rect.height  # 获取高度（点）

                    #得到每个pdf页面的块列表
                    with open(f"output/json/{temp_page_num}.json", "r", encoding="utf-8") as temp_page_json_file:
                        temp_page_blocks = json.load(temp_page_json_file)
                    temp_page_num+=1

                    #得到当前页面的文字块列表
                    temp_page_text_blocks = [temp_page_block for temp_page_block in temp_page_blocks if is_tag_textbox(temp_page_block['class']) == 1]
                    
                    #遍历当前页面的所有文字块，得到文字块rect列表temp_page_text_block_rects
                    for each_temp_page_text_block in temp_page_text_blocks:
                        #得到当前文字块的pymupdf坐标
                        each_block_bbox=bbox_transform(each_temp_page_text_block["bbox_normalized"],temp_pdf_page_width,temp_pdf_page_height)
                        each_block_rect=fitz.Rect(each_block_bbox[0],each_block_bbox[1],each_block_bbox[2],each_block_bbox[3])
                        
                        #如果当前rect和已存在的有重叠，则跳过当前的block
                        if temp_page_text_block_rects==[]:
                            temp_page_text_block_rects.append(each_block_rect)
                        else:
                            check_output=add_text_block_rect_check(each_block_rect,temp_page_text_block_rects)
                            if check_output[0]:
                                temp_txt.write('出现了一次重叠\n')
                                if check_output[1]==-1:
                                    
                                    continue
                                else:
                                    temp_page_text_block_rects[check_output[1]]=each_block_rect
                            else:
                                temp_page_text_block_rects.append(each_block_rect)
                    
                    for each_ready_rect in temp_page_text_block_rects:
                        draw_custom_rect(input_pdf_page,each_ready_rect)

                        #获取这个block的详细信息以获得字号
                        each_block_dict_blocks = (input_pdf_page.get_text("dict", clip=each_ready_rect))['blocks']
                        
                        #文字块的字号提取
                        if each_block_dict_blocks != [] and each_block_dict_blocks[0]['type']==0:
                            each_block_fontsize = each_block_dict_blocks[0]['lines'][0]['spans'][0]['size']
                        else:
                            each_block_fontsize=10
                        
                        #识别文字块中的英文
                        each_block_text=to_plain_block(input_pdf_page.get_text('text',clip=each_ready_rect))
                            
                        #把即将要拿去翻译的字符串记录到output.txt里
                        temp_txt.write(each_block_text)
                        temp_txt.write('\n')

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
            input_pdf.save('temp2.pdf')
        temp_pdf.save(f"{input_pdf_path}-中文翻译版.pdf")
    #current_dir = os.getcwd()  # 获取当前工作目录
    #target_path = os.path.join(current_dir, 'output')  # 构造完整路径
    #shutil.rmtree(target_path)
    print("\n" + "="*50)
    print("全部完成！")
    print("="*50)
    return 1
