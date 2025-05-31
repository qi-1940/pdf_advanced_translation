# -*- coding: utf-8 -*-
import wx
import wx.adv
import time
import threading
import os
import shutil
import sys
import multiprocessing
from translation import translate_pdf_ai
from utils import get_resource_path

class StdoutRedirector:
    """重定向标准输出到GUI"""
    def __init__(self, append_log_func):
        self.append_log_func = append_log_func
        self.old_stdout = sys.stdout
        
    def write(self, text):
        if text.strip():  # 忽略空行
            self.append_log_func(text.strip())
        # 保持原有的控制台输出用于调试（可选）
        # self.old_stdout.write(text)
        
    def flush(self):
        pass

class PDFTranslatorGUI(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="PDF英文文献翻译工具", size=(600, 450))  # 修改：调整窗口高度
        
        # 定义状态颜色
        self.COLOR_SUCCESS = wx.Colour(200, 255, 200)  # 浅绿色
        self.COLOR_ERROR = wx.Colour(255, 200, 200)    # 浅红色
        self.COLOR_NORMAL = wx.WHITE                    # 默认白色
        
        self.init_ui()
        self.translation_thread = None
        self.stop_translation = False
        self.Centre()
        print('这里会输出一些日志信息，不影响使用，请不要手动关闭，否则翻译会失败')
        # 设置stdout重定向到GUI日志
        sys.stdout = StdoutRedirector(self.append_log)

    def init_ui(self):
        """初始化用户界面"""
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # 尝试加载程序图标
        try:
            # 首先尝试加载 ICO 文件
            ico_path = get_resource_path('resources/logo.ico')
            if os.path.exists(ico_path):
                icon = wx.Icon(ico_path, wx.BITMAP_TYPE_ICO)
                self.SetIcon(icon)
            # 如果没有 ICO 文件，尝试加载 PNG 文件
            elif os.path.exists('resources/logo.png'):
                self.logo = wx.Bitmap(get_resource_path('resources/logo.png'), wx.BITMAP_TYPE_PNG)
                icon = wx.Icon()
                icon.CopyFromBitmap(self.logo)
                self.SetIcon(icon)
        except Exception as e:
            print(f"无法加载图标: {e}")

        # 1. PDF文件选择区域
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        lbl_pdf = wx.StaticText(panel, label="PDF文件路径:")
        self.txt_pdf = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        btn_browse = wx.Button(panel, label="浏览...")
        
        hbox1.Add(lbl_pdf, flag=wx.RIGHT, border=8)
        hbox1.Add(self.txt_pdf, proportion=1, flag=wx.EXPAND)
        hbox1.Add(btn_browse, flag=wx.LEFT, border=8)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.ALL, border=10)

        # 新增：页数选择区域
        hbox_pages = wx.BoxSizer(wx.HORIZONTAL)
        lbl_pages = wx.StaticText(panel, label="翻译页数（0=全部）:")
        self.spin_pages = wx.SpinCtrl(panel, min=0, max=999, initial=0)
        self.spin_pages.SetToolTip("0表示翻译全部页面，其他数字表示翻译前N页")  # 新增
        hbox_pages.Add(lbl_pages, flag=wx.RIGHT, border=8)
        hbox_pages.Add(self.spin_pages, proportion=1, flag=wx.EXPAND)
        vbox.Add(hbox_pages, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=10)
        
        # 2. 翻译按钮
        self.btn_translate = wx.Button(panel, label="开始翻译")
        vbox.Add(self.btn_translate, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=10)
        
        # 3. 状态显示区
        self.txt_status = wx.TextCtrl(panel, style=wx.TE_READONLY|wx.NO_BORDER)  # 移除上下键
        self.txt_status.SetBackgroundColour(self.COLOR_NORMAL)
        self.txt_status.SetValue("准备就绪，请选择PDF文件")
        vbox.Add(self.txt_status, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=10)

        # 4. 日志区域
        lbl_log = wx.StaticText(panel, label="操作日志:")
        vbox.Add(lbl_log, flag=wx.LEFT|wx.TOP, border=10)
        
        self.txt_log = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        vbox.Add(self.txt_log, proportion=1, flag=wx.EXPAND|wx.ALL, border=10)
        
        # 绑定事件
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        self.btn_translate.Bind(wx.EVT_BUTTON, self.on_translate)
        self.txt_pdf.Bind(wx.EVT_TEXT_ENTER, self.on_translate)
      
        panel.SetSizer(vbox)
        
    def on_browse(self, event):
        """打开文件选择对话框"""
        wildcard = "PDF文件 (*.pdf)|*.pdf"
        dialog = wx.FileDialog(self, "选择PDF文件", wildcard=wildcard, style=wx.FD_OPEN)
        
        if dialog.ShowModal() == wx.ID_OK:
            selected_path = dialog.GetPath()
            self.txt_pdf.SetValue(selected_path)
            self.append_log(f"已选择文件: {selected_path}")
            
        dialog.Destroy()
    
    def on_translate(self, event):
        """处理翻译开始/停止操作"""
        pdf_path = self.txt_pdf.GetValue().strip()
        n_pages = self.spin_pages.GetValue()  # 新增：获取页数设置
        
        # 检查文件有效性
        if not pdf_path:
            wx.MessageBox("请先选择PDF文件！", "错误", wx.OK|wx.ICON_ERROR)
            return
            
        if not os.path.isfile(pdf_path):
            wx.MessageBox("指定的文件不存在！", "错误", wx.OK|wx.ICON_ERROR)
            self.append_log(f"文件不存在: {pdf_path}")
            self.update_status("错误：文件不存在", is_error=True)
            return
            
        # 检查是否正在翻译
        if self.translation_thread and self.translation_thread.is_alive():
            import ctypes
            # 强制终止线程
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_long(self.translation_thread.ident), 
                ctypes.py_object(SystemExit)
            )
            self.btn_translate.SetLabel("开始翻译")
            self.append_log("用户停止了翻译进程")
            self.update_status("翻译已停止", is_error=False)
            # 清理临时文件
            if os.path.exists('output'):
                shutil.rmtree(os.path.join(os.getcwd(), 'output'))
        else:
            # 开始新的翻译
            self.btn_translate.SetLabel("停止翻译")
            self.txt_status.Clear()
            self.txt_log.Clear()
            
            self.append_log("=== 开始新的翻译任务 ===")
            self.append_log(f"源文件: {pdf_path}")
            self.append_log(f"翻译模式: {'前%d页' % n_pages if n_pages > 0 else '全部页面'}")  # 新增
            self.update_status("正在翻译中...", is_error=False)
            
            # 修改：传递n_pages参数
            self.translation_thread = threading.Thread(
                target=self.do_translation, 
                args=(pdf_path, n_pages),
                daemon=True
            )
            self.translation_thread.start()
    
    def do_translation(self, pdf_path, n_pages):
        """执行实际的翻译工作"""
        try:
            self.append_log("正在解析PDF文件...")
            translated_path = translate_pdf_ai(pdf_path, n_pages)
            
            # 处理翻译结果
            if(translated_path==0):
                self.update_status("翻译失败！", is_error=True)
                self.append_log("错误: 未能生成输出文件")
                
            elif os.path.exists(translated_path):
                self.update_status("翻译完成！", is_error=False)
                self.append_log(f"成功生成翻译文件: {translated_path}")
                
        except Exception as e:
            self.update_status("翻译过程出现异常！", is_error=True)
            self.append_log(f"错误类型: {type(e).__name__}")
            self.append_log(f"错误详情: {str(e)}")
            
        finally:
            # 清理临时文件
            try:
                if os.path.exists('output'):
                    shutil.rmtree(os.path.join(os.getcwd(), 'output'))
            except Exception as e:
                self.append_log(f"清理临时文件时出错: {e}")
            wx.CallAfter(self.btn_translate.SetLabel, "开始翻译")
            self.stop_translation = True
    
    def update_status(self, message, is_error=None):
        """更新状态栏文本和颜色
        is_error: 
            None - 正常状态（白色）
            True - 错误状态（红色）
            False - 成功状态（绿色）
        """
        def _update():
            self.txt_status.SetValue(message)
            if is_error is None:
                color = self.COLOR_NORMAL
            else:
                color = self.COLOR_ERROR if is_error else self.COLOR_SUCCESS
            self.txt_status.SetBackgroundColour(color)
            self.txt_status.Refresh()
        wx.CallAfter(_update)
    
    def append_log(self, message):
        """添加带时间戳的日志记录"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        wx.CallAfter(self.txt_log.AppendText, log_message)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = wx.App(False)
    frame = PDFTranslatorGUI()
    frame.Show()
    app.MainLoop()