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
from collections import namedtuple
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

def to_sentences(query):
    #接受的参数query是字符串，函数要返回一个列表，列表里的每个元素都是一个完整的英文句子,句子的开头必须是英文字母
    #删除所有的换行符
    sentences_list=[]
    char_list=[]
    is_begin_of_a_sentence=1
    chars=iter(query)
    while(1):
        try:
            every_char=next(chars)
            if every_char=='.' or every_char=='!' or every_char=='?':
                char_list.append(every_char)
                sentences_list.append(''.join(char_list))
                char_list=[]
                is_begin_of_a_sentence=1
            else:
                while((is_begin_of_a_sentence==1 and every_char==' ') or every_char=='\n'):
                    every_char=next(chars)
                char_list.append(every_char)
                is_begin_of_a_sentence=0
        except StopIteration:
            break
    return sentences_list

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

def is_next_span(last_Span,Span):#1表示“是”
    if abs(last_Span.y0 - Span.y0)<=1.5:
        if abs(last_Span.y1 - Span.y1)<=1.5:
            if abs(last_Span.x1 - Span.x0)<=3:
                #for each_char in Span.text:
                #    if is_english_letter(each_char)!=1 and each_char!=' ':
                #        return 0
                return 1
    return 0

def is_next_line(last_para,Span_v2):
    #print(Span_v2.y0-Span_v2.y1)
    #print(last_para.line_height)
    if is_close(abs(Span_v2.y0-Span_v2.y1),last_para.line_height):
        #print('进入')
        if last_para.num_of_lines==1:#如果last_para只有一行（首行）
            if is_close(last_para.x2,Span_v2.x1):
                return 1
        else:
            if is_close(last_para.x2,Span_v2.x1)==1 and is_close(last_para.x1,Span_v2.x0):
                return 1
    return 0
  
def translate_pdf(input_pdf_path):
    Span = namedtuple("Span", ["text", "x0", "y0",'x1','y1','font_size'])
    para = namedtuple("para", ["text", "x0", "y0",'x1','y1','x2','y2','x3','y3','line_height','num_of_lines'])
    with fitz.open(input_pdf_path) as input_pdf:#打开输入的pdf文件
        #output_pdf=fitz.Document()
        for input_pdf_page in input_pdf: # iterate the document pages
            #output_pdf_current_page=output_pdf.new_page()
            page_blocks=input_pdf_page.get_text('dict')['blocks']
            Span_list=[]#原始Span列表
            for each_block in page_blocks:
                if each_block["type"] == 0:  # 0表示文本块（非图片/表格）
                    for line in each_block["lines"]:
                        for span in line["spans"]:
                            Span_list.append(Span(span['text'],span['bbox'][0],span['bbox'][1],\
                                                  span['bbox'][2],span['bbox'][3],span['size']))
            Span_list_v2=[]#粘和Span的列表
            for Span_v1 in Span_list:
                if Span_list_v2 == [] or is_next_span(Span_list_v2[-1],Span_v1)==0:
                    Span_list_v2.append(Span_v1)
                else :
                    last_Span=Span_list_v2.pop()
                    Span_list_v2.append(Span(last_Span.text+Span_v1.text,last_Span.x0,\
                                             last_Span.y0,Span_v1.x1,Span_v1.y1,last_Span.font_size))
                
            para_list=[]#初级段落列表
            for Span_v2 in Span_list_v2:
                if para_list==[] or is_next_line(para_list[-1],Span_v2)==0:
                    para_list.append(para(Span_v2.text,\
                                        Span_v2.x0,Span_v2.y0,\
                                        Span_v2.x0,Span_v2.y0,\
                                        Span_v2.x1,Span_v2.y1,\
                                        Span_v2.x1,Span_v2.y1,abs(Span_v2.y1-Span_v2.y0),1 ))
                else:
                    last_para=para_list.pop()
                    para_list.append(para(last_para.text+'\n'+Span_v2.text,\
                                            last_para.x0,last_para.y0,\
                                            last_para.x1,last_para.y1,\
                                            Span_v2.x1,Span_v2.y1,\
                                            last_para.x2,last_para.y2,last_para.line_height,last_para.num_of_lines+1))
                    
            tran_para_list=[]
            for each_para_text in para_list:
                tran_para_list.append(baidu_translate(to_plain_block(each_para_text))[0]['dst'])
            #for each_para in para_list:
            #print(para_list[0].text,end='\n')
                #print(Span_v2.x0)
                #print(Span_v2.x0,end='\t')
                #print(Span_v2.y0,end='\t')
                #print(Span_v2.x1,end='\t')
                #print(Span_v2.y1)
                    #block_tran=baidu_translate(to_plain_block(block_text))[0]['dst']
                    #output_pdf_current_page.insert_textbox(block_rect,block_tran,align=0,fontname='china-ss',fontsize=block_font_size)

            '''page_imgs=input_pdf_page.get_images(full=True)
            for page_img in page_imgs:
                xref=page_img[0]
                pix=fitz.Pixmap(input_pdf,xref)
                base_image = input_pdf.extract_image(xref)
                img_data = base_image["image"]  # 二进制图像数据
                
                # 获取图片在源页面的坐标和尺寸（fitz.Rect对象）
                img_rect = input_pdf_page.get_image_bbox(page_img)
                
                # 将图片按原坐标插入新页面
                output_pdf_current_page.insert_image(
                    img_rect,       # 目标区域
                    pixmap=pix,  # 已生成的 Pixmap 对象
                    overlay=False   # 是否覆盖原有内容（True 覆盖，False 叠加）
                )'''
    
    #output_pdf.save(f"{input_pdf_path}-中文翻译版.pdf")
    #output_pdf.close()
    return 1