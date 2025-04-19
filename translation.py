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
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
import pymupdf # imports the pymupdf library
import os

def txt_to_pdf(txt_path, pdf_path):
    # 创建PDF画布
    c = canvas.Canvas(pdf_path, pagesize=(595.27, 841.89))# A4 pagesize
    height = 841.89
    
    # 设置字体和字号
    c.setFont("STSong-Light", 12)
    
    # 读取文本内容
    with open(txt_path, "r", encoding="utf-8") as f:
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
    r = requests.post(url, params, headers=headers)
    result1 = r.json()
    # Show response
    return result1['trans_result']

def translate_pdf(pdf_path):
    # 保存原始输出对象
    original_stdout = sys.stdout  

    #打开输入的pdf文件
    doc = pymupdf.open(pdf_path)
    with open('output.txt', 'w') as f:
        sys.stdout = f  # 重定向到文件

        for page in doc: # iterate the document pages
            query = page.get_text() # get plain text encoded as UTF-8
            translated_text = baidu_translate(query)
            for row in translated_text:
                print(row['dst'])
                print('\n')

        doc.close()

    # 恢复标准输出
    sys.stdout = original_stdout  

    #生成pdf输出文件
    txt_to_pdf("output.txt", "output.pdf")

    if os.path.isfile("output.pdf"):
        os.remove('output.txt')
        return 1
    else:
        return 0
    