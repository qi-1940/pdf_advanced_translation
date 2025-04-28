#调用翻译函数的方法：
#from translation import translate_pdf
#translate_pdf(pdf_path)
#如果翻译成功，返回1，否则返回0

import sys
from reportlab.pdfgen import canvas
import hashlib
import hmac
import json
import requests
import time
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import pymupdf 
import os
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

def txt_to_pdf(txt_path, pdf_path):
    # 创建PDF画布
    c = canvas.Canvas(pdf_path, pagesize=(595.27, 841.89))# A4 pagesize
    height = 841.89
    
    # 设置字体和字号
    c.setFont("STSong-Light", 12)
    
    # 读取文本内容
    with open(txt_path, "r",encoding='utf-8') as f:
        lines = f.readlines()
    
    # 初始化坐标和行距
    y = height - 40  # 起始位置距离顶部40单位
    line_height = 15  # 行间距
    
    # 逐行写入PDF
    for line in lines:
        if y < 40:  # 页底留白40单位时换页
            c.showPage()
            c.setFont("STSong-Light", 12)
            y = height - 40
        c.drawString(40, y, line.strip())
        y -= line_height
    
    # 保存PDF
    c.save()

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

def to_same_row_length_sentences(list_of_sentences):
    #参数是一个列表，里面有若干句子（中文字符串），它们长度不一
    #输出一个列表，里面存储的也是这些句子，但列表的元素的长度一致，为40
    same_row_length_sentences=[]
    current_length=0
    for temp_sentence in list_of_sentences:
        temp_sentence_length=len(temp_sentence)
        if temp_sentence_length+current_length<=40:
            same_row_length_sentences.append(temp_sentence)
            current_length+=temp_sentence_length
        else:
            while(temp_sentence_length+current_length>40):
                current_row_space=40-current_length
                temp_sentence_front_part=temp_sentence[:current_row_space]
                temp_sentence_back_part=temp_sentence[current_row_space:]
                same_row_length_sentences.append(temp_sentence_front_part)
                same_row_length_sentences.append("\n")
                current_length=0
                temp_sentence=temp_sentence_back_part
                temp_sentence_length=len(temp_sentence)
            same_row_length_sentences.append(temp_sentence)
            current_length+=temp_sentence_length
    return same_row_length_sentences

def to_plain_block(block):
    plain_block=''
    for every_char in block:
        if(every_char != '\n'):
            plain_block+=every_char
    return plain_block

def make_sentence_short(long_sentence):
    """参数是一个长字符串，返回也是一个长，这个函数会在每40个字符处添加一个换行符
    ，同时会在最末加一个换行符"""
    short_sentence=''
    size=len(long_sentence)
    rows_num=(int)(size/40)
    for i in rows_num:
        short_sentence+=long_sentence[i:i+40]
        short_sentence+='\n'
    short_sentence+=long_sentence[i+40:]
    short_sentence+='\n'
    return short_sentence

def translate_pdf(input_pdf_path):
    with pymupdf.open(input_pdf_path) as input_pdf:#打开输入的pdf文件
        with open('output.txt', 'w',encoding='utf-8') as output_txt:
            for input_pdf_page in input_pdf: # iterate the document pages
                page_blocks = input_pdf_page.get_text('blocks') # get blocks
                for each_block in page_blocks:
                    block_tran=baidu_translate(to_plain_block(each_block[4]))[0]['dst']
                    output_txt.write(make_sentence_short(block_tran))

                
    txt_to_pdf("output.txt", f"{input_pdf_path}-中文翻译版.pdf")#生成pdf输出文件

    if os.path.isfile(f"{input_pdf_path}-中文翻译版.pdf"):
        #os.remove('output.txt')
        return 1
    else:
        return 0