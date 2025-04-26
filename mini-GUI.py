import wx
import wx.adv
import time
import threading
import os
#from fpdf import FPDF  # 示例中用伪代码模拟PDF读取和翻译
from translation import translate_pdf

class PDFTranslatorGUI(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="PDF翻译工具", size=(600, 600))  # 增大窗口高度以容纳日志区域
        
        # 初始化UI
        self.init_ui()
        self.translation_thread = None
        self.stop_translation = False
        
    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 1. PDF路径输入框
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        lbl_pdf = wx.StaticText(panel, label="PDF路径:")
        self.txt_pdf = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        btn_browse = wx.Button(panel, label="浏览...")
        
        hbox1.Add(lbl_pdf, flag=wx.RIGHT, border=8)
        hbox1.Add(self.txt_pdf, proportion=1, flag=wx.EXPAND)
        hbox1.Add(btn_browse, flag=wx.LEFT, border=8)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.ALL, border=10)
        
        # 2. 翻译按钮
        self.btn_translate = wx.Button(panel, label="翻译")
        vbox.Add(self.btn_translate, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=10)
        
        # 3. 状态显示文本框
        self.txt_status = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_READONLY)
        vbox.Add(self.txt_status, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=10)
        
        # 4. 日志区域
         #self.collapse_panel = wx.CollapsiblePane(panel, label="翻译日志", style=wx.CP_DEFAULT_STYLE)
         #vbox.Add(self.collapse_panel, proportion=1, flag=wx.EXPAND|wx.ALL, border=10)
        lbl_log = wx.StaticText(panel, label="翻译日志:")
        vbox.Add(lbl_log, flag=wx.LEFT|wx.TOP, border=10)
        
        self.txt_log = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        vbox.Add(self.txt_log, proportion=1, flag=wx.EXPAND|wx.ALL, border=10)
        
              
        # 事件绑定
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        self.btn_translate.Bind(wx.EVT_BUTTON, self.on_translate)
      
        panel.SetSizer(vbox)
        
    def on_browse(self, event):
        """选择PDF文件"""
        wildcard = "PDF文件 (*.pdf)|*.pdf"
        dialog = wx.FileDialog(self, "选择PDF文件", wildcard=wildcard, style=wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            self.txt_pdf.SetValue(dialog.GetPath())
        dialog.Destroy()
    
    def on_translate(self, event):
        """启动/停止翻译线程"""
        absolute_pdf_path = self.txt_pdf.GetValue()

          # 检查文件是否存在
        if not os.path.isfile(absolute_pdf_path):
         wx.MessageBox("请选择有效的PDF文件！", "错误", wx.OK | wx.ICON_ERROR)
         return
       # 将绝对路径转换为相对路径
        pdf_path = os.path.relpath(absolute_pdf_path)
        
        if not os.path.isfile(pdf_path):
            wx.MessageBox("请选择有效的PDF文件！", "错误", wx.OK|wx.ICON_ERROR)
            return
            
        if self.translation_thread and self.translation_thread.is_alive():
            self.stop_translation = True
            self.btn_translate.SetLabel("翻译")
            self.update_status("用户手动停止翻译")
        else:
            self.stop_translation = False
            self.btn_translate.SetLabel("停止")
            self.txt_status.Clear()
            self.txt_log.Clear()
            self.update_status("开始翻译...")
            
            # 启动翻译线程
            self.translation_thread = threading.Thread(
                target=self.do_translation, 
                args=(pdf_path,),
                daemon=True
            )
            self.translation_thread.start()
    
    def do_translation(self, pdf_path):
        """模拟翻译过程（需替换为实际PDF解析和翻译逻辑）"""
        #try:
        #if translate_pdf(pdf_path) != None:
        #wx.CallAfter(self.btn_translate.SetLabel, "翻译")
        #except Exception as e:
        #    self.append_log(f"错误: {str(e)}")
        #    self.update_status("翻译失败！")
         # ===== 修改标记1：获取并显示翻译后路径 =====
       # 获取翻译后的文本内容
        translated_text = translate_pdf(pdf_path)
        
        if translated_text:  # 如果翻译成功
            # ===== 关键修改：生成绝对路径 =====
            # 获取原始文件的目录和基本名
            dir_path = os.path.dirname(os.path.abspath(pdf_path))
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            
            # 构建输出文件名（保持命名格式）
            output_name = f"{base_name}-中文翻译版.pdf"
            
            # 组合完整绝对路径
            translated_path = os.path.join(dir_path, output_name)         #---------------------------------直接获取路径

        if translated_path:  # 翻译成功
            self.update_status("翻译完成！")
            self.append_log(f"翻译文件已保存至: {translated_path}")  # 在日志中显示完整路径
            wx.CallAfter(self.btn_translate.SetLabel, "翻译")
        else:  # 翻译失败
            self.update_status("翻译失败！")
            self.append_log("错误: 无法生成翻译文件")
        # ===== 修改结束 ====
    
    def update_status(self, message):
        """更新状态文本框"""
        wx.CallAfter(self.txt_status.SetValue, message)
    
    def append_log(self, message):
       # """添加日志（线程安全）"""
       # wx.CallAfter(self.txt_log.AppendText, f"{message}\n")
        # ===== 修改开始：添加时间戳并优化显示 =====
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        wx.CallAfter(self.txt_log.AppendText, log_message)
        # ===== 修改结束 =====


if __name__ == "__main__":
    app = wx.App(False)
    frame = PDFTranslatorGUI()
    frame.Show()
    app.MainLoop()