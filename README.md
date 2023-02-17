# IDATools
A repo of collected useful IDA scripts and plugins


## From Github

- diaphora(二进制对比插件，有时候比BinDiff更精确)    
https://github.com/joxeankoret/diaphora

- VulFi: IDA 危险函数分析插件
  > VulFi（漏洞查找器）工具是IDA Pro的插件，可用于在二进制文件中进行错误搜索。它的主要目标是提供一个单一视图，其中包含对最有趣的函数（如strcpy，sprintf，system等）的所有交叉引用。对于可以使用Hexrays反编译器的情况，它将尝试排除对这些从漏洞研究角度来看不感兴趣的函数的调用（想想像strcpy（dst，“Hello World！”）这样的东西）。如果没有反编译器，规则就简单得多（不依赖于架构），因此只排除了最明显的情况。

  https://github.com/Accenture/VulFi

- findcrypt    
一款发现二进制中加密参数的插件    
https://github.com/polymorf/findcrypt-yara   
IDA 7.5安装参考 [IDA7.5安装findcrypt3插件](https://blog.csdn.net/weixin_45055269/article/details/112688365)

- Rename   
Claroty开发的便于修改IDA函数命名的插件，主要根据函数中的字符串提供函数的候选名    
https://github.com/claroty/ResearchTools
