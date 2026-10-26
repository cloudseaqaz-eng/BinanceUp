# BinanceUp · 两种连续性的分布评分

更新日期：2026-10-27（北京时间）。下载BinanceUp-research.zip，覆盖完整research目录，保留research_data。

详情核心指标、成交与订单流、全部指标新增“连续性评分”图：
- 蓝线：主动买入连续性评分，输入为最近5分钟有主动买入分钟占比。
- 黄线：交易连续性评分，输入为最近5分钟有成交分钟占比。

各自计算：70%×所选窗口均值＋30%×最低20%样本均值。默认30分钟取最低6个样本，可切换15分钟取最低3个，范围0–100分。提示框提供原C5、均值、低位均值、高低档占比。曲线保留分钟采样，与K线光标联动；缺口或非法值留空。

停止旧服务后启动：

```bash
python -m research --root research_data serve
```

强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、下载、重建评分特征或训练。原有累计分/基线、连续性、UW与时间窗口功能保留。

79项Python检查、65项Chromium检查通过。初始权重未优化，观察评分不等于上涨概率；完整口径和验证范围见RESEARCH.md、RESEARCH_VALIDATION.md。包不含行情缓存或环境，SHA256SUMS提供校验。
