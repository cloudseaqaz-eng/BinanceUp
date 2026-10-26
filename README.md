# BinanceUp · 严格连续时长与细线显示

更新日期：2026-10-27（北京时间）。下载BinanceUp-research.zip，覆盖完整research目录，保留research_data。

详情新增严格连续时长图：主动买入和交易各绘制C5连续≥80%、连续100%的分钟数，共四条。默认log(1+分钟)非线性纵轴，可在“时长刻度”切线性；提示框始终显示实际分钟。条件中断即归零，缺失数据留空。与K线光标联动。

所有详情曲线及虚线统一不超过1 CSS px，包含原始UW展开曲线与动态窗口图；网格、K线影线、光标也为1px，蜡烛实体按密度显示。

停止旧服务后启动：

```bash
python -m research --root research_data serve
```

强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、下载、特征重建或训练。

本轮70项Chromium交互检查和JavaScript语法检查通过。线宽通过拦截实际Canvas绘制属性验证，最大1 CSS px。后端/公式未变，未重复Python套件；完整记录见RESEARCH_VALIDATION.md。

保留6/3小时状态图、累计分及基线、原始连续性、UW和时间窗功能。包不含行情缓存或运行环境；SHA256SUMS提供校验。
