# BinanceUp 回测代码包 · 无损存储 v2

下载本分支中的 `BinanceUp-research.zip`，解压后阅读 `BinanceUp/RESEARCH.md`。

本次只优化存储：不降采样、不改变数值精度，不改评分、权重搜索或标签公式。

- 无损编码与基础行情列去重，全部分钟指标和图表仍可读取。
- 转换成功并校验后清理ZIP；保留来源哈希，重复下载命令复用已验证数据。
- 已有数据可迁移，不必重新评分和训练。先停止该实验的服务/任务，再运行：

```bash
python -m research --root research_data compact --prune-archives
python -m research --root research_data storage
```

40项自动检查、24项浏览器检查通过。4轮重新训练的14份搜索/模型/报告JSON和10份选中/入池表与升级前完全一致。

存储实测：24币合成数据约1.924GB降为0.987GB（减少48.7%）；BTC真实小样本22.661MB降为10.410MB（减少54.1%）。这些是存储验证，非真实全市场六个月策略结论。

包内没有用户数据、下载缓存或模拟数据集。详细方法、运行步骤、原有数据限制与验证范围见包内说明。校验值见 `SHA256SUMS`。
