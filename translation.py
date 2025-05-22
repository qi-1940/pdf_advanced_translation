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
import shutil
from ai3 import ai_pdf_process

import hashlib
import time
import requests

import hashlib
import time
import requests
import re

def baidu_translate(query):
    # 参数验证
    if not query or not isinstance(query, str):
        raise ValueError("查询文本不能为空且必须是字符串")
    
    # 清理文本（移除非法字符）
    query = clean_text(query)
    if not query:
        raise ValueError("清理后的查询文本为空")
    
    app_id = '20250415002334058'
    secret_key = 'SVA9Lv0mE90NQsj76c0W'
    url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
    
    # 生成签名
    salt = str(round(time.time() * 1000))  # 毫秒级时间戳
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
    
    try:
        response = requests.post(url, data=params, timeout=10)
        response.raise_for_status()
        r = response.json()
        
        if 'error_code' in r:
            error_msg = f"错误码 {r['error_code']}: {r.get('error_msg', '未知错误')}"
            if r['error_code'] == '54003':  # 频率限制
                time.sleep(1.1)
            raise Exception(error_msg)
            
        if 'trans_result' not in r:
            raise Exception(f"响应格式异常: {r}")
            
        return r['trans_result']
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求失败: {str(e)}")
    except ValueError:
        raise Exception("响应解析失败，非JSON格式")

def clean_text(text):
    """清理文本中的非法字符"""
    # 移除控制字符（ASCII 0-31和127）
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    # 移除BOM标记
    text = text.replace('\ufeff', '')
    # 移除首尾空白
    return text.strip()

# 使用示例
try:
    # 测试各种情况
    test_cases = [
        "Hello World!",  # 正常文本
        "",              # 空文本
        "\x00Test\x1F",  # 包含控制字符
        "   ",           # 空白文本
        "A" * 7000       # 超长文本
    ]
    
    for text in test_cases:
        try:
            print(f"翻译文本: {text[:50]}...")  # 显示前50个字符
            result = baidu_translate(text)
            print("翻译结果:", result)
        except Exception as e:
            print(f"翻译失败: {str(e)}")
        print("-" * 50)
        
except Exception as e:
    print(f"测试失败: {str(e)}")



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
                            each_block_rect=fitz.Rect(each_block_bbox[0]-5,each_block_bbox[1],each_block_bbox[2]+15,each_block_bbox[3])
                        draw_custom_rect(temp_pdf_page,each_block_rect)
                        each_block_dict_blocks = (input_pdf_page.get_text("dict", clip=each_block_rect))['blocks']
                        
                        #文字块字号提取、翻译与填充
                        if each_block_dict_blocks != [] and each_block_dict_blocks[0]['type']==0:
                            each_block_fontsize = each_block_dict_blocks[0]['lines'][0]['spans'][0]['size']
                            each_block_text=to_plain_block(input_pdf_page.get_text('text',clip=each_block_rect))
                            #with open("output.txt", "a", encoding="utf-8") as f:
                            #    f.write(each_block_text)
                            #    f.write('\n')
                            each_block_tran=baidu_translate(each_block_text)[0]['dst']
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
        current_dir = os.getcwd()  # 获取当前工作目录
        target_path = os.path.join(current_dir, 'output')  # 构造完整路径
        shutil.rmtree(target_path)
    return 1