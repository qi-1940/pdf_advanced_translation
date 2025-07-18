![logo](resourses/logo.png)
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
- commit 7.4:
    - 解决了模型重复识别框的问题
    - 统一字体微软雅黑（msyh.ttf）
    - 添加了.gitignore文件
    - 添加了开发者调试脚本run.sh
    - 添加了commit_outputs文件夹，以后重大更新的成果会放在这里
    - 成果如下![7.4](./commit_outputs/7.4.png)
- commit 7.5:
    - 进行了前后端整合，并以此为基础发布1.0版本，[从官网下载](https://www.qi-1940.top)

***
# 课程要求（重要）
![要求1](resourses/软件工程要求1.png)
![要求2](resourses/软件工程要求2.png)

# 以下是留言
1. MXH：第一次计划全文
第一次开始：
需求分析：
1.输入英文文献，格式为pdf，输出翻译成中文的pdf文件。要求输出的文件中只有无任何格式的英文文本。仅一页。
用户故事：
运行程序，弹出界面。用户输入文件绝对路径。旁边“翻译按钮”。按下后，右边文本框显示日志，如“正在翻译”，
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


**需求分析设计https://vv19fzqqa8m.feishu.cn/wiki/GLv6wWt3ri3NIrke2OfcdBeenLd?from=from_copylink**

## MXH功能描述
1. 翻译过程中输出日志到前端，及时给与用户反馈。
2. 利用现有开源项目的模型识别可翻译区块和不可翻译区块。保持位置不变搬运不可翻译区块。得到可翻译区块在页面的相对坐标后转化为pymupdf中的坐标。用pymupdf进行一个可翻译块区域内的文字提取和字号提取。调用百度翻译得到翻译后的字符串再用pymupdf填充。
3. 模型会识别出重复文字块，自研算法删除不合适的文字块区域。

