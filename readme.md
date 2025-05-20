# 【置顶】MXH2025/4/19：
这个文件现在用于开发者间交流，不是面向用户的。

1. python版本3.11，因为wxpython不适配3.12。
2. 已知的依赖包有requests，wxpython，pymupdf，reportlab。版本都装最新的。
3. 不要直接试图打包，因为会产生很大的文件。凡是要上传到github的文件夹里，都不能进行打包操作。
4. 要上传到github里的文件夹一定要精简，最好只有代码，因为目前.git文件夹已近大几百兆了。
建议在本地保存文件夹副本然后自己打包测试。在我看来没必要打包，python mini_GUI.py即可。
END

***

**重要：下面是对每次commit的解释，比如我某一次提交的标签为"commit 2"，那么这次提交对应的解释就在下面能看到。**
- commit 1：
    test.py能用，mini-GUI.py不能用，待解决。实现了一句一句地翻译。下一步是通过坐标识别段落。
- commit 2：
    清理了目录，将plan.txt和readme.txt合并为readme.md，以后专注于这个文件。
- commit 3:
    暂时补住漏洞
- commit 4:
    基本无改动
- commit 5:
    翻译日志显示问题解决，返回翻译文件的绝对路径，给出要翻译文件的相对路径
- commit 7:
    基本能实现文字块的识别和翻译，但还存在重复识别和漏识别文字块等问题。但相比commit5
    已经是巨大的进步，尤其是引进了开源项目的ai模型。
- commit 7.2:
    能实现全流程了。

***

# 以下是留言
1. MXH：第一次计划全文
第一次开始：
需求分析：
1.输入英文文献，格式为pdf，输出翻译成中文的pdf文件。要求输出的文件中只有无任何格式的英文文本。仅一页。
用户故事：
运行程序，弹出界面。用户输入文件绝对路径。旁边有“翻译按钮”。按下后，右边文本框显示日志，如“正在翻译”，
“翻译完成，输出路径为:”。
项目管理：
第二次课结束前必须实现需求。
分工:
jh测试，GUI编写
mxh翻译逻辑
第一次结束

2. MXH发现的问题2025，4，22：
1.主程序mini-GUI.py运行后任务栏未出现图标，导致程序难以关闭。
2.翻译成功结束后主页面应该出现一个按键方便用户打开输出的pdf文件。
3.翻译日志里的页数没有实际意义。
4.按行进行翻译，无法实现预期功能。
5.需要识别出段落。
6.翻译结果的字体、行距、页边距应和输入相同。

3. JH发现的问题2025.4.24
1.JH（Windons系统）在运行 open()函数时编译转换使用'utf-8'发生错误，使用'gbk'时正常运行
2.MXH（类Linux系统）在运行 open()函数时编译转换使用'gbk'发生错误，使用'utf-8'时正常运行
（JH怀疑是Windows和Linux系统对'utf-8'和'gbk'的定义不一样。）

4. class里面的标签类型：abandon,title,table_caption,table,figure,plain text,formula,formula_caption,
----5.13
其中图片/公式/表格需要的class 类有：table,figure,formula,formula_caption

5. 文字处理需要的class 类有title abandon table_capiton,plain text figure_captain(5.20加figure_captain)
----5.17
