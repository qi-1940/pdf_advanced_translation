# -*- coding: utf-8 -*-
import sys
import os
import fitz

# 全局日志回调函数
_log_callback = None

def set_log_callback(callback):
    """设置日志回调函数"""
    global _log_callback
    _log_callback = callback

def log_message(message):
    """统一的日志输出函数"""
    # 只输出到GUI，不输出到控制台
    if _log_callback:
        _log_callback(message)

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def draw_custom_rect(page, rect, number):
    # 定义三种颜色：红、绿、蓝
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    # 根据编号选择颜色
    color = colors[number % 3]
    
    # 绘制矩形框
    page.draw_rect(rect, color=color, width=1.5)
    
    # 添加编号（使用相同的颜色）
    page.insert_text((rect.x0-10, rect.y0 - 5), str(number), fontsize=8, color=color)

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