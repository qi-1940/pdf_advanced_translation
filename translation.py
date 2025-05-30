'''
调用翻译函数的方法：
from translation import translate_pdf_ai
translate_pdf_ai(pdf_path, page_num=-1),page_num为-1时，翻译所有页数，否则翻译指定页数
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

# 全局变量用于存储日志回调函数
log_callback = None
redirector_instance = None  # 添加全局重定向器实例
output_path = None

def set_log_callback(callback):
    """设置日志回调函数"""
    global log_callback, redirector_instance
    log_callback = callback
    
    # 如果已有重定向器，先清理
    if redirector_instance:
        redirector_instance.cleanup()
    
    # 创建新的重定向器实例
    if callback:
        redirector_instance = LogRedirector()

class LogRedirector:
    """重定向标准输出的类"""
    def __init__(self):
        self.old_stdout = sys.stdout
        self.is_redirected = False
        self.start_redirect()

    def start_redirect(self):
        """开始重定向"""
        if not self.is_redirected:
            sys.stdout = self
            self.is_redirected = True

    def cleanup(self):
        """清理重定向"""
        if self.is_redirected:
            sys.stdout = self.old_stdout
            self.is_redirected = False

    def write(self, text):
        if text.strip():  # 忽略空行
            if log_callback:
                log_callback(text.strip())
            self.old_stdout.write(text)

    def flush(self):
        self.old_stdout.flush()

    def __del__(self):
        self.cleanup()

def is_segments_overlapping(seg1,seg2):
    '''
    判断两个线段是否重叠，重叠返回重叠的长度
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

    if (s2x0>s1x0 and s2x0<s1x1) or (s2x1>s1x0 and s2x1<s1x1):
        x=[]
        x.append(s1x0)
        x.append(s1x1)
        x.append(s2x0)
        x.append(s2x1)
        x_len=max(x)-min(x)
        s1_len=s1x1-s1x0
        s2_len=s2x1-s2x0
        return s1_len+s2_len-x_len
    elif (s1x0>s2x0 and s1x0<s2x1) or (s1x1>s2x0 and s1x1<s2x1):
        x=[]
        x.append(s1x0)
        x.append(s1x1)
        x.append(s2x0)
        x.append(s2x1)
        x_len=max(x)-min(x)
        s1_len=s1x1-s1x0
        s2_len=s2x1-s2x0
        return s1_len+s2_len-x_len
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
    
    if is_segments_overlapping(r1s1,r2s1)>0.01 and is_segments_overlapping(r1s2,r2s2)>0.01:
        overlapping_area=is_segments_overlapping(r1s1,r2s1)*is_segments_overlapping(r1s2,r2s2)
        if overlapping_area/rect_area(rect1)>0.5 or overlapping_area/rect_area(rect2)>0.5:
            return 1
    return 0

def rect_area(rect):
    '''
    计算矩形面积
    '''
    return abs(rect.x0-rect.x1)*abs(rect.y0-rect.y1)

def add_text_block_rect_check(temp_rect, rect_lists):
    '''
    检查temp_rect和rect_lists里的元素有无冲突，
    如果冲突，返回(1, [num1, num2, ...])，其中num1, num2等是冲突的rect的索引
    如果temp_rect的面积小于任何一个冲突的rect，则返回(1, [])
    如果temp_rect的面积大于所有冲突的rect，则返回(1, [num1, num2, ...])
    返回(0, [])表示没有冲突
    '''
    if rect_lists == []:
        return (0, [])
    
    overlapping_indices = []
    temp_rect_area = rect_area(temp_rect)
    
    # 找出所有重叠的矩形
    for i, rect in enumerate(rect_lists):
        if is_rects_overlapping(temp_rect, rect):
            overlapping_indices.append(i)
    
    # 如果没有重叠，返回(0, [])
    if not overlapping_indices:
        return (0, [])
    
    # 检查temp_rect是否比所有重叠的矩形都大
    for idx in overlapping_indices:
        if rect_area(rect_lists[idx]) >= temp_rect_area:
            return (1, [])  # temp_rect不是最大的，返回空列表
    
    # temp_rect是最大的，返回所有重叠矩形的索引
    return (1, overlapping_indices)

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

def draw_custom_rect(page, rect, number):
    # 定义三种颜色：红、绿、蓝
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    # 根据编号选择颜色
    color = colors[number % 3]
    
    # 绘制矩形框
    page.draw_rect(rect, color=color, width=1.5)
    
    # 添加编号（使用相同的颜色）
    page.insert_text((rect.x0-10, rect.y0 - 5), str(number), fontsize=8, color=color)

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

def translate_pdf_ai(input_pdf_path,page_num=0):

    #预处理（除了文字块外的所有处理）
    if ai_pdf_process(input_pdf_path, page_num) == False:
        print('预处理失败！')
        return 0
    
    print("\n" + "="*50)
    print("第二阶段：文字块处理")
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
                #temp_txt.write(f'temp page num:{temp_page_num}\n')
                input_pdf_page=input_pdf[temp_page_num-1]
                temp_page_text_block_rects=[]
                temp_pdf_page.insert_font(fontfile='msyh.ttf',fontname='msyh')

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
                        #temp_txt.write(f'skip:{each_block_rect}\n')
                        continue

                    #如果当前rect和已存在的有重叠，则跳过当前的block
                    #temp_txt.write(f'each_block_rect:{each_block_rect}\n')
                    #temp_txt.write(f'temp_page_text_block_rects:{temp_page_text_block_rects}\n')
                    check_output = add_text_block_rect_check(each_block_rect, temp_page_text_block_rects)
                    #temp_txt.write(f'check_output:{check_output}\n')
                    if check_output[0] == 0:  # 没有重叠
                        temp_page_text_block_rects.append(each_block_rect)
                        #temp_txt.write(f'append:{each_block_rect}\n')
                    else:
                        if not check_output[1]:  # 返回空列表，说明temp_rect不是最大的
                            pass
                        else:  # 返回了重叠矩形的索引列表
                            # 从后往前删除重叠的矩形，避免索引变化
                            for idx in sorted(check_output[1], reverse=True):
                                del temp_page_text_block_rects[idx]
                            # 添加新的矩形
                            temp_page_text_block_rects.append(each_block_rect)
                            #temp_txt.write('替换了多个重叠的块\n')

                    #temp_txt.write(f'length of temp_page_text_block_rects:{len(temp_page_text_block_rects)}\n')
                
                # 添加编号计数器
                rect_number = 0
                for each_ready_rect in temp_page_text_block_rects:
                    #draw_custom_rect(input_pdf_page, each_ready_rect, rect_number)
                    
                    #获取这个block的详细信息以获得字号
                    each_block_dict_blocks = (input_pdf_page.get_text("dict", clip=each_ready_rect))['blocks']
                    
                    #文字块的字号提取
                    if each_block_dict_blocks != [] and each_block_dict_blocks[0]['type']==0:
                        each_block_fontsize = each_block_dict_blocks[0]['lines'][0]['spans'][0]['size']
                    else:
                        each_block_fontsize=10
                    
                    #识别文字块中的英文
                    each_block_text=to_plain_block(input_pdf_page.get_text('text',clip=each_ready_rect))

                    '''    
                    把即将要拿去翻译的字符串记录到output.txt里
                    temp_txt.write(f'{rect_number}:')
                    temp_txt.write(each_block_text)
                    temp_txt.write('\n')
                    temp_txt.write(f'({each_ready_rect[0]} {each_ready_rect[1]} {each_ready_rect[2]} {each_ready_rect[3]})')
                    temp_txt.write('\n')
                    rect_number += 1
                    '''
                    
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
                    while temp_pdf_page.insert_textbox(rect=each_ready_rect,buffer=each_block_tran,fontname='resourses/msyh.ttf',\
                        fontsize=each_block_fontsize-1) <0:
                        each_ready_rect[0]-=1
                        each_ready_rect[1]-=1
                        each_ready_rect[2]+=1
                        each_ready_rect[3]+=1
                        each_block_fontsize-=1
                        
        output_path = f"{input_pdf_path}-中文翻译版.pdf"
        temp_pdf.save(output_path)
    shutil.rmtree(os.path.join(os.getcwd(), 'output'))#删除output文件夹
    print("\n" + "="*50)
    print("全部完成！")
    print("="*50)
    return output_path
