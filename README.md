# BinanceUp · 连续性状态图

更新日期：2026-10-27（北京时间）。下载BinanceUp-research.zip，覆盖完整research目录，保留research_data。

已撤除上次“70%均值＋30%低位均值”的连续性评分图及后台计算，改为连续性状态图：
- 蓝线：主动买入C5≥80%的时间占比。
- 黄线：交易C5≥80%的时间占比。
- 灰色虚线：主动买入C5≤20%的时间占比。

默认最近6小时，可切3小时。C5表示最近5分钟有成交或主动买入的分钟占比。提示框显示当前C5及连续≥80%、连续100%时长；分钟曲线与K线联动。缺失数据留空，连续时长从完整本地历史计算，切换前窗不重置。旧评分控件自动清理，新控件缺失自动补齐。

停止旧服务后启动：

```bash
python -m research --root research_data serve
```

强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、下载、重新生成评分特征或训练。保留原始连续性、累计分/基线、UW及扩展时间窗。

79项Python和66项Chromium检查通过；新计算与SAGA真实分析30,241分钟的14字段逐值一致。完整说明见RESEARCH.md、RESEARCH_VALIDATION.md。本图观察活跃背景，不代表上涨概率。包不含行情缓存或环境，SHA256SUMS提供校验。
