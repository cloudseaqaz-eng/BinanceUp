# BinanceUp · K线纵轴最小涨幅跨度50%

更新日期：2026-10-27（北京时间）。下载BinanceUp-research.zip，覆盖完整research目录，保留research_data。

K线图纵轴涨幅跨度按“上界÷下界−1”计算，最小50%。可见K线高低价比不足1.5时，围绕几何中心扩展；达到或超过1.5时直接按实际最低/最高价显示。不是上下各50%，也不是绝对价格差50。前窗/周期/未来观察变动时按可见K线重算，不修改OHLC或评分。

停止旧服务后启动：

```bash
python -m research --root research_data serve
```

强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、下载、生成评分特征或训练。

本轮72项Chromium检查和JavaScript语法检查通过。保留全图最多1px细线、严格连续时长、3/6小时连续性状态、累计分/基线及其他图表。完整验证范围见RESEARCH_VALIDATION.md。

包不含行情缓存或环境，SHA256SUMS提供校验。
