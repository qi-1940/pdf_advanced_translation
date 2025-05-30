# -*- coding: utf-8 -*-
import wx
import wx.adv
import time
import threading
import os
from translation import translate_pdf_ai  # 确保该函数已支持n_pages参数
from utils import get_resource_path

class FileDropTarget(wx.FileDropTarget):
    """处理文件拖放的类"""
    def __init__(self, window):
        super().__init__()
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        if len(filenames) > 0:
            pdf_path = filenames[0]
            if pdf_path.lower().endswith('.pdf'):
                self.window.txt_pdf.SetValue(pdf_path)
                self.window.append_log(f"拖放文件成功: {pdf_path}")
            else:
                wx.MessageBox("请拖放有效的PDF文件！", "错误", wx.OK | wx.ICON_ERROR)
        return True

class PDFTranslatorGUI(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="PDF英文文献翻译工具", size=(600, 450))  # 修改：调整窗口高度
        
        self.init_ui()
        self.translation_thread = None
        self.stop_translation = False
        self.SetDropTarget(FileDropTarget(self))
        self.Centre()
        
        # 在初始化时设置一次日志回调，避免重复设置
        self.setup_log_callback()

    def init_ui(self):
        """初始化用户界面"""
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # 尝试加载程序图标
        try:
            if os.path.exists('resources/logo.png'):
                self.logo = wx.Bitmap(get_resource_path('resources/logo.png'), wx.BITMAP_TYPE_PNG)
                self.SetIcon(wx.Icon(self.logo))
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
        self.txt_status = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.txt_status.SetValue("准备就绪，请选择PDF文件")
        vbox.Add(self.txt_status, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=10)

        # 4. 日志区域（删除进度条后重新编号）
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
            return
            
        # 检查是否正在翻译
        if self.translation_thread and self.translation_thread.is_alive():
            self.stop_translation = True
            self.btn_translate.SetLabel("开始翻译")
            self.append_log("用户停止了翻译过程")
        else:
            # 开始新的翻译
            self.stop_translation = False
            self.btn_translate.SetLabel("停止翻译")
            self.txt_status.Clear()
            self.txt_log.Clear()
            
            self.append_log("=== 开始新的翻译任务 ===")
            self.append_log(f"源文件: {pdf_path}")
            self.append_log(f"翻译模式: {'前%d页' % n_pages if n_pages > 0 else '全部页面'}")  # 新增
            self.update_status("正在翻译中...")
            
            # 修改：传递n_pages参数
            self.translation_thread = threading.Thread(
                target=self.do_translation, 
                args=(pdf_path, n_pages),
                daemon=True
            )
            self.translation_thread.start()
    
    def setup_log_callback(self):
        """在初始化时设置日志回调"""
        try:
            from translation import set_log_callback
            set_log_callback(self.append_log)
        except ImportError:
            pass
    
    def do_translation(self, pdf_path, n_pages):
        """执行实际的翻译工作"""
        try:
            self.append_log("正在解析PDF文件...")
            translated_path = translate_pdf_ai(pdf_path, n_pages)
            
            # 处理翻译结果
            if os.path.exists(translated_path):
                self.update_status("翻译完成！")
                self.append_log(f"成功生成翻译文件: {translated_path}")
            else:
                self.update_status("翻译失败！")
                self.append_log("错误: 未能生成输出文件")
                
        except Exception as e:
            self.update_status("翻译过程出现异常！")
            self.append_log(f"错误类型: {type(e).__name__}")
            self.append_log(f"错误详情: {str(e)}")
            
        finally:
            wx.CallAfter(self.btn_translate.SetLabel, "开始翻译")
            self.stop_translation = True
    
    def update_status(self, message):
        """更新状态栏文本"""
        wx.CallAfter(self.txt_status.SetValue, message)
    
    def append_log(self, message):
        """添加带时间戳的日志记录"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        wx.CallAfter(self.txt_log.AppendText, log_message)

if __name__ == "__main__":
    app = wx.App(False)
    frame = PDFTranslatorGUI()
    frame.Show()
    app.MainLoop()