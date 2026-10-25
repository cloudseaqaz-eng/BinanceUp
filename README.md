# BinanceUp · 撤除状态观察图

更新日期：2026-10-26（北京时间）。下载BinanceUp-research.zip，覆盖完整research目录，保留research_data。

已撤除活跃状态转折图、状态观察控件、快慢EMA/基线/阶段状态后台计算；旧HTML残留控件自动移除。保留交易连续性、主动买入连续性、UW曲线和扩展前后窗。0–5分曲线目前只讨论，未加入程序。

停止旧服务后启动：

```bash
python -m research --root research_data serve
```

强制刷新：Mac ⌘⇧R；Windows/Linux Ctrl+Shift+R。无需run、重新下载、生成评分特征或训练。

本轮13项Python针对性检查、57项Chromium检查通过。完整验证范围见RESEARCH_VALIDATION.md。包不含行情缓存或运行环境，SHA256SUMS提供校验。
