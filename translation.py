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
from ai3 import ai_pdf_process

def baidu_translate(query):
    app_id = '20250425002342076'
    secret_key = 'pT1QnotEaWuvpefNLgce'
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

def bbox_transform(bbox,x,y):
    '''
    传入的参数是pdf页面转图片后，识别出来的相对矩形位置(bbox),
    以及pdf页面的宽度和长度
    '''
    bbox[0] = bbox[0]*x
    bbox[2] = bbox[2]*x
    bbox[1] = bbox[1]*y
    bbox[3] = bbox[3]*y
    return bbox

def is_tag_textbox(tag_str):
    if tag_str=='title' or \
        tag_str=='abandon' or \
        tag_str=='table_caption' \
        or tag_str=='plain text':
        return 1
    else:
        return 0 

def translate_pdf_ai(input_pdf_path):

    #预处理（除了文字块外的所有处理）
    if ai_pdf_process(input_pdf_path) == False:
        print('预处理失败！')
        return 0
    
    with fitz.open('output/temp.pdf') as temp_pdf:
        with fitz.open(input_pdf_path) as input_pdf:
            temp_page_num=0
            for temp_pdf_page in temp_pdf:
                input_pdf_page=input_pdf[temp_page_num]
                #获取当前页面的宽度和高度
                temp_pdf_page_width = temp_pdf_page.rect.width  # 获取宽度（点）
                temp_pdf_page_height = temp_pdf_page.rect.height  # 获取高度（点）

                #得到每个pdf页面的块列表
                try:
                    with open(f"output/json/{temp_page_num}.json", "r", encoding="utf-8") as temp_page_json_file:
                        temp_page_blocks = json.load(temp_page_json_file)
                        temp_page_num+=1

                    #得到当前页面的文字块列表
                    temp_page_text_blocks=[]
                    for temp_page_block in temp_page_blocks:
                        if is_tag_textbox(temp_page_block['class'])==1:
                            temp_page_text_blocks.append(temp_page_block)

                    #遍历当前页面的所有文字块
                    for each_temp_page_text_block in temp_page_text_blocks:
                        #得到当前文字块的pymupdf坐标
                        if  each_temp_page_text_block["class"]=='title':
                            each_block_bbox=bbox_transform(each_temp_page_text_block["bbox_normalized"],temp_pdf_page_width,temp_pdf_page_height)
                            each_block_rect=fitz.Rect(each_block_bbox[0]-20,each_block_bbox[1],each_block_bbox[2]+5,each_block_bbox[3])
                        else :
                            each_block_bbox=bbox_transform(each_temp_page_text_block["bbox_normalized"],temp_pdf_page_width,temp_pdf_page_height)
                            each_block_rect=fitz.Rect(each_block_bbox[0],each_block_bbox[1],each_block_bbox[2],each_block_bbox[3])
                            
                        each_block_dict_blocks = (input_pdf_page.get_text("dict", clip=each_block_rect))['blocks']
                        #with open("temp.txt", "w", encoding="utf-8") as file:
                        #    each_block_dict_blocks[0]
                        
                        #文字块字号提取、翻译与填充代码
                        if each_block_dict_blocks != [] and each_block_dict_blocks[0]['type']==0:
                            each_block_fontsize = each_block_dict_blocks[0]['lines'][0]['spans'][0]['size']
                            each_block_text=to_plain_block(input_pdf_page.get_text('text',clip=each_block_rect))
                            each_block_tran=baidu_translate(each_block_text)[0]['dst']
                            #print(each_block_tran)
                            #print(each_block_text)
                            while temp_pdf_page.insert_textbox(rect=each_block_rect,buffer=each_block_tran,fontname='china-ss',\
                                fontsize=each_block_fontsize-1) <0:
                                each_block_rect[0]+=1
                                each_block_rect[1]+=1
                                each_block_rect[2]+=1
                                each_block_rect[3]+=1
                                each_block_fontsize-=1
    
                except FileNotFoundError:
                    print("文件不存在！")
                except json.JSONDecodeError:
                    print("JSON 格式错误！")
                
        temp_pdf.save(f"{input_pdf_path}-中文翻译版.pdf")
    return 1