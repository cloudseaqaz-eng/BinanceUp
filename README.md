# BinanceUp · 累计分24小时基线

更新日期：2026-10-26（北京时间）。下载BinanceUp-research.zip，覆盖完整research目录，保留research_data。

持续活跃积累图增加灰色虚线“此前24h累计分均值”。每个时点取截至该时点前30分钟的此前24小时1440个累计分均值，同为0–20分。排除最新30分钟，避免刚出现的变化立即抬高参照。提示框增加较基线高/低多少分；完整历史不足或有缺口时留空。

该基线表示此前累计分常态水平，与已撤EMA观察图的“有成交分钟占比”百分比基线口径不同。当前15、基线2表示高于此前常态13分；当前20、基线19说明此前已很活跃，满分未必是新异常。基线每分钟滚动，不固定在页面评分时刻。

停止旧服务后启动：

```bash
python -m research --root research_data serve
```

强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、重新下载、重建评分特征或训练。

75项Python检查、61项Chromium检查通过。完整说明和验证范围见RESEARCH.md、RESEARCH_VALIDATION.md。包不含行情缓存或环境，SHA256SUMS提供校验。
