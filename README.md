# BinanceUp · UW平滑观察图

更新日期：2026-10-25（北京时间）。下载 BinanceUp-research.zip，覆盖完整 research/ 程序目录，保留 research_data。

新增UW3零值占比和整体上影压力两张平滑图，默认60分钟，可切换30/60/120分钟。原始UW3、压力15通过“展开原始UW3／压力15”对照。提示框显示有效UW3覆盖率、相对当前窗口之前24h的差值（百分点）。窗口缺失留空、全平价压力留空，仅使用已收盘数据。

整体上影压力＝所选窗口上影总长÷振幅总和，按振幅加权。它与压力15均值含义不同；零值占比是UW3零值窗口的占比，不是独立事件次数。这些观察指标尚未验证能提升预测。

停止旧服务，再启动：

```bash
python -m research --root research_data serve
```

强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、重新下载、生成特征或训练。

66项Python检查及50项Chromium交互检查通过，含旧HTML/服务兼容、窗口切换、原始曲线展开、光标联动与未来不改历史。保留中文URL、OI质量/合约映射、活跃状态和无损存储功能。完整说明与验证范围见包内RESEARCH.md、RESEARCH_VALIDATION.md。

包不含行情缓存、环境目录或模拟预测结果；校验值见SHA256SUMS。
