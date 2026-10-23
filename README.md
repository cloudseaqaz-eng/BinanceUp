# BinanceUp 回测代码包 · 中文交易对下载修复

本次修复中文币名直接进入下载URL导致的`ascii`编码错误。现货、OI、资金费率请求统一对URL路径进行UTF-8百分号编码，保留原中文交易对名称、本地文件名和已有缓存。评分公式与数据精度不变。

已有无损存储v2版本，只需下载本分支的`research/data.py`，替换项目内同名文件。也可下载完整`BinanceUp-research.zip`，解压后阅读`BinanceUp/RESEARCH.md`。

保留原数据目录，继续原任务：

```bash
python -m research --root research_data run
```

只想补完下载可用`python -m research --root research_data download`。成功转换并通过校验的币会复用，失败的币重新请求；不用删除缓存、重新初始化或排除中文币。

44项Python自动检查通过；新增4项覆盖中文现货/OI/资金费率URL的真实本地HTTP请求、已编码路径及S3查询不重复编码、404、中文ZIP缓存与转换检查点复用、中文行情文件引用。未宣称完成这些币的真实六个月回测。

保留此前无损存储v2全部改进：原分钟频率和字段精度不变，压缩并去重，转换校验成功才清理ZIP。此前24项浏览器检查通过，4轮重新训练结果与存储升级前完全一致。详细验证范围见包内`RESEARCH_VALIDATION.md`。

包内没有用户数据、下载缓存或模拟数据集。校验值见`SHA256SUMS`。
