# BinanceUp · 主动买入交易连续性

更新日期：2026-10-26（北京时间）。下载BinanceUp-research.zip，覆盖完整research目录，保留research_data。

详情新增“主动买入交易连续性 · 有主动买入分钟占比”，在核心指标、成交与订单流、全部指标中可见。绘制5/15/60分钟三条曲线，固定0–100%轴，与K线/OI共用时间轴和光标。

计算：窗口内主动买入成交额USDT>0的分钟数÷窗口分钟数。一笔微小买入也算一个活跃分钟；100%不代表买方占优或净买入。缺失/非法值留空，不当零处理。使用已有分钟数据，不增加下载、不改评分。

停止旧服务，再启动：

```bash
python -m research --root research_data serve
```

浏览器强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、下载、重建特征或训练。

69项Python检查、56项Chromium交互检查通过。保留前窗2周、未来72小时/1周、UW平滑图、OI质量/合约映射、中文URL、活跃状态及无损存储。验证范围见包内RESEARCH_VALIDATION.md。

包内不含行情缓存、环境目录或模拟预测结果。SHA256SUMS提供校验值。
