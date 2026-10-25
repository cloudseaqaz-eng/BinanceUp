# BinanceUp · UW详情页初始化兼容修复

更新日期：2026-10-25（北京时间）。下载`BinanceUp-research.zip`并覆盖完整程序文件，保留原`research_data`数据目录。

修复`detail.js:168`的`Cannot set properties of null (setting onchange)`：新脚本遇到旧HTML中缺少UW开关时，原来会中断整页初始化。现在等待DOM就绪，自动补齐新开关和UW组选项，可选说明节点缺失时也继续绘图。旧服务未提供UW字段时保留K线，并提示重启服务，不伪造新指标。

详情脚本/样式带版本参数，静态资源不缓存，减少新旧文件混用。

更新后先停止原服务，再启动：

```bash
python -m research --root research_data serve
```

浏览器强制刷新：Mac按`⌘⇧R`，Windows/Linux按`Ctrl+Shift+R`。**不需要run、重新下载、重新计算特征或训练。**

65项Python检查与46项Chromium检查通过。新增场景实际模拟旧HTML缺控件、缺说明节点和旧API缺UW字段，均能正常显示或给出明确提示，无JS运行时错误。

保留UW独立压力/变化强度图、分钟标记、原评分、OI修复、活跃状态和无损存储全部功能。详情选择“UW观察（含K线）”查看新图。包内不含行情数据、缓存或模拟结果。详细说明见`RESEARCH.md`与`RESEARCH_VALIDATION.md`，校验值见`SHA256SUMS`。
