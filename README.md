# BinanceUp · 持续活跃积累曲线

更新日期：2026-10-26（北京时间）。下载BinanceUp-research.zip，覆盖完整research目录，保留research_data。

详情在核心指标、成交与订单流、全部指标中增加“持续活跃积累程度 · 0–20分”。每分钟检查最近5分钟：有成交4–5分钟加1分，2–3分钟保持，0–1分钟扣1分，累计分截在0–20。提示框显示累计分、最近5分钟有成交分钟数和更新规则。

从本地原始历史固定起点以0分开始，切换前窗不重新起算；缺口/非法成交笔数重置，完整5分钟后恢复。始终用过去已收盘分钟，不因显示未来改变历史值。长期活跃币易满分，需结合沉寂背景判断。

停止旧服务后启动：

```bash
python -m research --root research_data serve
```

强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、下载、重新生成评分特征或训练。

73项Python检查、59项Chromium检查通过；计算口径和验证范围见包内RESEARCH.md、RESEARCH_VALIDATION.md。保留原有连续性/UW图与扩展时间窗。包不含行情缓存或环境；SHA256SUMS提供校验。
