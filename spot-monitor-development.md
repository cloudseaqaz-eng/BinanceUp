---
title: "现货监控（spot-monitor）开发与交付规范"
subtitle: "模块架构 · 上游接口 · UW3兼容 · 历史回放 · 生产验收"
date: "2026-11-12 · 文档版本 2.0"
lang: zh-CN
---

# 1. 文档用途与交付范围

本文面向接手开发的工程师，定义独立项目 **现货监控（spot-monitor）** 的功能、数据契约、算法兼容要求、任务恢复、界面和验收条件。本文是开发规范，不表示项目已经实现或部署。

目标流程：观察池名单 → 币安现货K线 → UW3零值占比 → 历史特征 → 分类状态 → 每小时快照 → 前端人工回看。

- 固定市场：Binance USDT现货；固定K线周期：15分钟。
- 基础指标：上影UW3零值占比，EMA半衰期24小时。
- 分类：预警池、长期活跃池、其他池。“预警”仅表示重点关注类别，不发送通知、不下单。
- 提供最近90天人工回看，按当时可得数据判断。
- 前端紧凑布局、亮色主题，只展示业务信息。
- 原始数据和基础指标独立保存；研究特征及分类支持“清除并重算”。

**优先级：用户要求与已核验参考源码 > 本文概述公式 > 实施者自行推导。分类默认参数属于实验方案，UW3兼容规则属于必须满足的约束。**

# 2. 已核验资料与版本

本次已经实际读取上传的《现货观察池 API · 消费服务对接文档》，适用 spot-watchlist V1.7.1、schemaVersion="1.0"。该附件日期为2026-11-11。

同时核验 BinanceUp 项目族中两份不同实现：

| 来源 | 实际算法 | 本项目用途 |
|---|---|---|
| BinanceUp/research/uw.py | 最近3根一分钟上影比例均值；30/60/120分钟滚动零值占比 | 解释旧版语义，不作为24小时EMA实现 |
| ContinuityLiveViewer/lib/upper-wick.js，v1.21.1 | 所选周期最近3根上影比例均值；零值状态EMA | **截图对应的计算基准** |
| ContinuityLiveViewer/lib/metrics.js | 一分钟K线按UTC边界聚合所选周期、补齐时间轴 | 时间和缺口行为基准 |
| ContinuityLiveViewer/lib/binance.js | 现货uiKlines，读取1分钟数据 | 参考行情来源 |

这里将“与BinanceUp一致”明确为：与该仓库发布的、能生成用户截图中“15分钟K线·半衰期24小时”曲线的查看器实现一致。不得把Python旧版滚动窗口替换成一个自行解释的EMA后声称兼容。

参考仓库：https://github.com/cloudseaqaz-eng/BinanceUp

参考发布提交：`98e54d721f9af106ac419ff897d7de65051f886a`

参考发布包：

<https://raw.githubusercontent.com/cloudseaqaz-eng/BinanceUp/98e54d721f9af106ac419ff897d7de65051f886a/ContinuityLiveViewer.zip>

已核对发布ZIP中的 upper-wick.js 与本地参考文件完全相同。哈希见附录。本文附带兼容代码与数值样例，接手者应继续保留参考文件和来源标记。

# 3. 架构与模块边界

技术栈：Node.js 24 LTS、TypeScript、Fastify、React、Vite、SQLite。依赖版本锁定并提交锁文件。SQLite驱动可选支持Node 24的 better-sqlite3。生产构建由一个应用提供前端静态资源、接口及后台任务。

| 模块 | 职责 | 变动预期 |
|---|---|---|
| providers | 观察池、币安接口、限流、重试、响应校验 | 低 |
| market-sync | 初始化、增量、缺口修复 | 低 |
| market-storage | K线、基础指标、计算进度 | 低 |
| indicators | 与参考实现一致的UW3计算 | 较低 |
| features | 分位、中位数、下降幅度、持续占比、斜率 | 中高 |
| classification | 入池、转池、恢复和状态推进 | 高 |
| research-storage | 研究批次、特征、快照、状态 | 中 |
| rebuild / jobs | 重算、恢复、调度、清理 | 中 |
| api / web | 列表、详情、历史时间、参数、任务状态 | 中 |

计算模块接收已规范化的数据并返回结果，不自行请求外部接口、不自行执行SQL。实时和回放共用相同计算入口。

```text
spot-monitor/
  server/src/
    config/
    providers/watchlist/
    providers/binance/
    market-sync/{bootstrap,incremental,gap-repair}/
    market-storage/
    indicators/
    features/
    classification/{contracts,rules,registry}/
    research-storage/
    rebuild/
    jobs/
    api/
    main.ts
  web/src/
    pages/{pools,symbol-detail}/
    components/
    settings/
    api/
  shared/
  tests/
  docs/
  data/
    control.sqlite
    research.sqlite
    history/
      RLCUSDT/market.sqlite
      GTCUSDT/market.sqlite
  .env.example
  package.json
  README.md
```

数据目录名称固定为 `history/`，不是 `spot/`。数据、日志、密钥、实际.env不提交仓库。

# 4. 上游一：观察池名单接口

## 4.1 地址、请求和鉴权

```http
GET {WATCHLIST_BASE_URL}/api/v1/watchlist?requireFresh=true
Accept: application/json
```

同机部署示例：`http://127.0.0.1:8787/api/v1/watchlist?requireFresh=true`。

**127.0.0.1只表示消费服务所在机器。跨服务器部署必须配置实际可达的域名或主机；附件没有给出可公开调用的生产域名。** 容器内的127.0.0.1也不是宿主机或其他容器。

按V1.7.1文档，该服务GET接口本身不需要鉴权凭据。公网网关若另设鉴权，应单独配置，不能凭空生成API Key字段。第一版使用默认精简响应，不需要 full=true、includeRules=true。

`/watchlist`返回完整当前名单，不分页；不要为它添加猜测的page参数。需要服务端分页/排序的是另一个 `/api/v1/symbols` 接口。

## 4.2 响应与使用方式

以下为**缩写的合成结构示例**，不能作为真实行情或回测输入：

```json
{
  "schemaVersion": "1.0",
  "generation": 42,
  "exchange": "binance",
  "market": "spot",
  "quoteAsset": "USDT",
  "generatedAt": "2026-11-11T12:00:00.000Z",
  "sourceUpdatedAt": "2026-11-11T12:00:00.000Z",
  "expiresAt": "2026-11-11T12:03:00.000Z",
  "stale": false,
  "count": 1,
  "symbols": [{
    "symbol": "RLCUSDT",
    "baseAsset": "RLC",
    "quoteAsset": "USDT",
    "category": "watchlist",
    "exchangeStatus": "TRADING",
    "marketEligible": true,
    "primarySector": null,
    "ticker": null,
    "classification": null
  }]
}
```

| 字段 | spot-monitor如何使用 |
|---|---|
| schemaVersion | 校验兼容的结构版本；忽略未知可选新字段 |
| generation | 目录成功发布代数，不是时间戳；标记本地名单版本 |
| exchange / market / quoteAsset | 校验binance / spot / USDT，防止混入合约或其他市场 |
| generatedAt / sourceUpdatedAt / expiresAt / stale | 分别保存，判断名单时效；不能当作K线更新时间 |
| symbols[].symbol | 唯一交易对标识，直接作为币安请求symbol，不从baseAsset拼接 |
| category | 应为watchlist，属于上游资产分类，不是本项目三个UW3类别 |
| exchangeStatus / marketEligible | 决定是否可继续常规现货同步；异常时保留数据并标记暂停 |
| primarySector / sector | 可选展示和后续筛选；不参与首版UW3计算 |
| ticker / tickerUpdatedAt | 可选24小时行情展示，必须标注其时间；不能用于构造15分钟K线 |
| classification | 上游资产分类依据；未核验不等于本项目UW3计算无效 |
| rotationEligible | 板块轮动资格，首版不据此剔除观察池成员 |
| counts | 全目录统计，不可当成观察池成员数组；本地池计数自行计算 |
| events | 最近一轮发布事件，非完整历史，不能当作可靠队列 |

ticker、sector、classification等可为空或缺省。symbols数组顺序是目录顺序，不是成交额排名。firstSeenAt是上游首次发现时间，不是上市时间。

名单同步默认每15分钟：成功校验新快照后，按symbol原子对账；新增进入初始化队列；移除暂停更新并归档，不直接断言下架。记录观察到的成员变化时间。成功返回的合法空名单与网络失败必须分开处理，合法空名单可经保护性复核后应用，不能永久忽略。

## 4.3 缓存、失败和增量事件

| 情况 | 处理 |
|---|---|
| 200、stale=false | 校验并应用名单 |
| 200、stale=true | 仅作为旧展示；不扩大或替换有效名单 |
| 304 | 无正文，使用已缓存名单；结合过期时间和X-Data-Stale判断时效 |
| 429 | 遵守Retry-After，带抖动退避 |
| 503 DATA_NOT_READY | 保留现状，等待初始化完成 |
| 503 DATA_STALE | 保留最后有效名单，标记上游过期 |
| 超时、502、500、解析失败 | 重试并保留最后有效名单，禁止当成symbols=[] |

保存ETag，下次请求可发送If-None-Match。ETag与generation、订单rulesHash不是同一个概念。名单版本相同也应关注其过期时间。

需要补偿成员变更事件时使用：

```http
GET {WATCHLIST_BASE_URL}/api/v1/changes?since=0&afterId=1234&limit=500
```

响应包含data、hasMore、nextAfterId、generation；data内每条事件有持久化id。幂等落库成功后再推进afterId；hasMore=true继续拉取。since和afterId同时提供是AND过滤；只按id消费时since=0。上游重建数据库后事件id可能重置，应重新全量对账。事件读取为可选增强，不代替全量快照对账。

上游健康接口：`GET /api/v1/health`。上游成员移出原因可查changes或单币详情 `/api/v1/symbols/{symbol}`；不能凭缺席就认定退市。

# 5. 上游二：币安现货K线

## 5.1 生产采集接口

```http
GET https://api.binance.com/api/v3/klines
    ?symbol=RLCUSDT
    &interval=15m
    &startTime={UTC毫秒}
    &endTime={UTC毫秒}
    &limit=1000
```

公共现货市场数据不要求用户API Key。基础地址可配置为官方可达的市场数据域名，例如 `https://data-api.binance.vision`。不得静默切到合约接口，也不得在网络失败时生成假数据。

timeZone保持默认UTC，不配置其他时区。服务时钟可通过 `GET /api/v3/time` 校验。参数startTime/endTime使用毫秒。

参考查看器实际使用 `https://www.binance.com/api/v3/uiKlines`，interval=1m，再按15分钟聚合。该来源与上述原生15分钟接口**不能未经验证就假定完全相同**，尤其UW3对极短上影和精确零值敏感。

生产采集以原生15分钟为目标，必须通过第7章对齐门槛后启用；有差异时保留生产源数据，使用明确的兼容采集配置修复，不能通过调阈值掩盖。参考源不可达时，写明未完成来源对齐，不宣称完整兼容。

## 5.2 返回数组字段及用途

每条K线是数组，按0开始计数：

| 索引 | 含义 | 存储与使用 |
|---|---|---|
| 0 | 开盘时间 | open_time，主键的一部分 |
| 1 | 开盘价 | open，UW3与K线展示 |
| 2 | 最高价 | high，UW3与K线展示 |
| 3 | 最低价 | low，UW3与K线展示 |
| 4 | 收盘价 | close，UW3与K线展示 |
| 5 | 基础资产成交量 | volume，保留原字符串 |
| 6 | 收盘时间，通常为时段末毫秒 | close_time，核验区间和收盘状态 |
| 7 | 计价资产成交额 | quote_volume，USDT金额；供后续研究 |
| 8 | 成交笔数 | trade_count，整数 |
| 9 | 主动买入基础资产量 | taker_buy_base_volume，保留 |
| 10 | 主动买入计价资产金额 | taker_buy_quote_volume，保留供后续研究 |
| 11 | 忽略字段 | 不参与算法，可保留在原始审计载荷中 |

上游观察池ticker.quoteVolume24h不是索引7的替代品。UW3本身只使用有效OHLC；成交额字段不作为零值状态权重。

收盘边界标准化：`time = openTime + 900000`。用该整刻边界标识计算点，不用closeTime末毫秒直接定位小时。只有时段已经结束的K线才进入正式计算。

若使用官方历史下载文件，应另建适配器，校验时间单位和格式；部分历史现货归档可能使用微秒，不能套用REST毫秒解析器。本版不要求实现归档下载。

## 5.3 分页、校验与限流

- 每页最多1000条，成功持久化后再保存页进度。
- 下一页从上一页最后开盘时间＋900000开始，避免死循环和跳页。
- 返回空页不等于历史完整，必须按目标时间轴检查缺口。
- 校验时间对齐、越界、重复、OHLC有限且合法、数量非负、成交笔数整数。
- 原始价格和金额以字符串保留；计算时按参考实现转JavaScript Number。
- 429/418遵守服务器冷却；不要并发冲击。403/451提示访问限制；-1121标记交易对不可查询，不替换symbol。
- 全局限流、请求超时、有限次数重试、指数退避和抖动；失败进任务队列而非无限占用线程。

# 6. UW3兼容：必须照源码实现

本章修正此前概述中容易偏离源码的内容：**参考EMA从首个有效zeroInput直接起步；发生无效K线后，满3根有效K线即可再次输出；不存在内置14天不显示规则。** 研究层可以另行标记预热质量，不能改变基础zeroRate。

输入为按UTC时间轴排列的15分钟K线，OHLC已转换为Number。有效性与参考一致：OHLC均为有限数、low>0、high≥max(open,close)、low≤min(open,close)。

```text
span = high - low
upperRatio = span === 0 ? 0
  : max(0, min(1, (high - max(open, close)) / span))

UW3 = 最近3根有效上影比例的算术平均
zeroInput = Number(UW3 === 0)

alpha = 1 - 2 ** (-15 / 1440)
ema = 首个有效输入 ? zeroInput
    : previousEma + alpha * (zeroInput - previousEma)
zeroRate = ema
```

关键边界：

1. 已知平价K线计上影比例0，三根平价K线的首个zeroRate为1。
2. 前两根输出uw3、zeroInput、zeroRate均为null。
3. 任意一根存在非零上影，三根窗口的UW3就不等于0。不引入最小上影阈值。
4. 下影变化可能改变非零上影比例的具体值，但在上影是否为零不变时，不改变zeroInput与zeroRate。
5. 无效K线将一个null放入三根窗口，并把EMA置null。再输入三根有效K线后，以新的zeroInput重新起步。
6. 计算器本身不检查时间跳跃。调用者必须把缺失15分钟时段作为无效占位逐个推入，不能直接跳过。
7. 使用参考的Number转换、clamp、严格等零和更新表达式。即使Decimal理论精度更高，也不能直接替换兼容计算路径；原始字符串保留用于审计。

alpha约为0.00719428。连续96次zeroInput=0，EMA衰减到原先约一半。占比低不直接等于上影短、交易活跃或上涨概率高。

完整参考函数原文见附录A。复制或移植后保留来源、版本和兼容测试。

# 7. 与BinanceUp逐点对齐的验收方法

分开验收算法与来源，不能只比较图片：

**算法对齐**：向原参考函数及新函数输入完全相同的15分钟K线、起点和缺失占位。比较每个time、uw3、zeroInput、zeroRate。null位置和zeroInput必须完全一致；浮点结果绝对误差≤1e-12。同语言直接复用时应争取完全相同。

**来源对齐**：同一symbol、UTC区间，同时取得原生15分钟和参考1分钟uiKlines。15根完整分钟按open首根、high最大、low最小、close末根聚合；缺任一分钟则整个桶无效。以收盘整刻对齐，不从用户输入时间重新分桶。

比较OHLC、平价状态、上影精确零值、三根窗口和最终EMA。开始计算的历史起点必须相同；不能拿不同起点造成的EMA种子误差当算法差异。对已有状态续跑时需使用同一份EMA及两根上影上下文。

至少覆盖活跃币、冷门币、低价币、平价区间、显著上影和缺口；真实样本和固定合成样本都保留。发现极短上影差异必须记录来源，不用容差改zeroInput。

最小样例：

| 输入场景 | 预期 |
|---|---|
| 连续3根 O=100,H=100,L=99,C=100 | 前两根null，第3根UW3=0、zeroInput=1、zeroRate=1 |
| 上例后接 O=100,H=101,L=99,C=100 | UW3=1/6、zeroInput=0、zeroRate=1-alpha |
| 已有输出后接一个无效占位 | 当前zeroRate=null |
| 无效后接3根都有非零上影的有效K线 | 前两根null，第3根zeroInput=0、zeroRate=0 |
| 三根 O=H=L=C=100 | 第3根zeroRate=1 |

本次已运行参考上影测试文件且通过；尚未为spot-monitor实现生产代码，也未完成真实双源行情对齐。验收记录必须区分这两件事。

# 8. 存储模型与断点恢复

control.sqlite：观察池快照与成员变更、配置、持久化任务、租约和运行记录。

history/{symbol}/market.sqlite：klines、uw3_points、sync_state、indicator_state、data_gaps、schema_migrations。

research.sqlite：research_runs、feature_points、classification_states、hourly_snapshots、classification_events、active_run、schema_migrations。

原始K线唯一键为interval＋open_time，数据库所属symbol固定。字段映射见第5章；额外保存source、source_hash和updated_at。计算点保存uw3、zeroInput、zeroRate、质量状态、指标版本和数据修订版本。

增量和初始化写同一张klines表。重复内容不新增、不无故修订版本；内容变化登记dirtyFrom，后续指标与研究结果按依赖重算。

独立保存：同步页进度、已知缺口、指标进度与EMA上下文、研究计算进度、小时快照进度。数据和对应进度在同一数据库事务内提交。跨数据库流程采用幂等任务和可重建索引，不假设跨文件天然原子。

重启流程：校验本地状态 → 重叠拉取最后4～8根并补齐停机区间 → 修复内部缺口 → 补算指标 → 补算研究与小时快照 → 恢复调度。不能只获取重启时最新一根。

保存指标检查点时包含EMA、最近两根上影比例及时间、算法参数、起点和修订版本。修正历史K线后，应从修正前的有效检查点重算直到当前，不能只改一根EMA。

# 9. 初始化范围与过期清理

用户目标为最近90天人工回看，每个时刻使用此前90天基线。仅保留90天所有数据无法满足历史判断。

| 数据 | 默认策略 |
|---|---|
| 原始15分钟K线 | 滚动90天 |
| UW3基础指标及小时基础值 | 至少180天，另加状态预热所需历史，建议约194天 |
| 研究特征 | 覆盖90天回放及至少14天状态预热 |
| 小时分类快照 | 滚动90天 |
| 未结束分类状态与原始基线 | 保留至状态结束及相应回看期限 |

建议初始化约208天：90天回看＋90天统计基线＋14天状态预热＋14天EMA历史。额外EMA历史用于减小种子影响，不改变参考函数立即输出的行为。14天后种子残余系数约2^-14。

按规则参数自动计算所需历史；如果只初始化180天，最早边界必须标记不完整。状态预热不保证恢复无限久以前的事件起点：边界已在低位时记起点未知，不能伪造新信号。

每日清理，依据数据所属时间，不依据文件mtime。只有基础指标、检查点和研究依赖已成功落盘后，才删除旧原始K线。SQLite释放空间供后续复用，避免每次同步VACUUM。

更改分类阈值通常无需旧原始K线；更改基础UW算法、周期、半衰期时，完整重算可能需要重新获取被清理的原始数据。

# 10. 小时快照与历史特征

统一UTC毫秒存储，北京时间展示。内部比例0～1，展示乘100。下降0.03显示“下降3个百分点”，不是“下降3%”。

10:00小时主值取09:45～10:00已收盘K线对应zeroRate。不再对四个值取均值或中位数；指标自身已有24小时EMA。另存一小时和最近六小时低位占比，用于持续性判断。

历史窗口严格为[t-90天,t)，使用有效小时基础值。每15分钟判断时，可从该区间小时序列取基线，排除当前时刻。历史时间戳必须代表所属整点，不得使用请求完成时间。

特征：当前值R、中位数M、Q20、Q25、Q75、IQR、历史分位P、下降幅度D、低位门槛L、近6小时与14天低位占比、覆盖率、质量原因。

分位数固定采用线性插值：排序后h=(n-1)p，在相邻值之间插值。历史分位采用中秩：P=(小于R的数量＋0.5×等于R的数量)/有效数量。

历史基线需完整时间跨度且覆盖率≥99%。缺失用null，不补零；不能用十天有效样本假装完整90天。历史分位不是上涨概率。

# 11. 首版实验分类规则

以下是可配置的v1研究规则，不是已证明有效的预测模型。初版按确定的参数和状态机实现，后续通过回放优化。

| 参数 | 默认值 |
|---|---|
| 历史基线 | 90天 |
| 低位参考 | Q20 |
| 最小下降 | 0.03，即3个百分点 |
| 波动幅度系数 | 0.5×IQR |
| 确认窗口 | 6小时，24个15分钟点 |
| 确认要求 | 至少20个异常低位点，且当前仍低 |
| 长期低位参考 | 0.25 |
| 长期窗口 | 14天 |
| 长期低位比例 | ≥80% |
| 恢复确认 | 6小时 |

```text
requiredDrop = max(0.03, 0.5 * IQR)
异常低位点 = R <= Q20 AND M - R >= requiredDrop
lowReference = min(Q20, M - requiredDrop)
```

六小时24点需连续有效；至少20点异常低位且当前满足才确认。不能删除缺失点缩小分母。25%不作为预警的硬条件，避免遗漏从70%明显下降到30%的变化。

长期条件：最近14天覆盖≥99%，低于25%的点数/预期总点数≥80%，初次进入时当前也低于25%。它是“指标长期低位”的业务名称，不等同于成交额活跃。

三个对外类别：ALERT→预警池；LONG_LOW→长期活跃池；OTHER→其他池。内部允许待确认和未知质量状态，数据不足条目放其他池但显著标记“数据不足”，不作为正常结论。

# 12. 分类状态机与事件生命周期

规则统一输入：判断时间、当前特征、上一状态、事件初始基线、参数、数据质量。统一输出：所属池、原因码、证据数值、下一状态。规则模块不自行读数据库。

事件保存candidateStartedAt、confirmedAt、initialMedian、initialIqr、initialLowReference、recoveryReference、transitionedToLongAt、endedAt、rearmedAt、leftCensored。

| 当前状态/事件 | 操作 |
|---|---|
| 普通/允许重新触发 | 满足六小时确认进入预警，冻结初始基线 |
| 无新预警且满足长期条件 | 进入长期活跃 |
| 预警持续≥14天且满足长期条件 | 转长期活跃，沿用同一事件身份，禁止旧条件重复触发 |
| 当前事件恢复确认 | 结束事件；根据长期条件决定去向 |
| 长期活跃、未有冻结事件 | 新一轮异常下降经确认，可进入预警 |
| 数据不足 | 不推进确认或恢复；保持可追踪状态，界面标记不可判断 |

恢复门槛参考：min(1, initialLowReference + max(0.03,0.2×initialIqr))，连续24个有效15分钟点达到该值才结束本轮事件。

从预警转长期后的事件需先恢复并重新允许触发，再重新累计六小时新确认，不能沿用旧窗口重复入池。无事件的长期状态退出可采用达到30%持续六小时，避免25%附近反复。

初始历史已经低位时标记起点未知，不把计算开始时间当成真实转折。实时与回放都从同样的初始状态规则启动。冻结基线不能被当前滚动基线覆盖；滚动分位回升本身不是恢复。

# 13. 研究批次与清除重算

前端提供“清除并重算”，默认作用于当前整个观察池，不受页面搜索、分类、分页影响。

清除研究特征、分类状态、冻结基线、分类事件、小时快照及缓存；原始K线、基础指标与对应进度不清除。

执行：固定规则参数、名单、数据截止与修订版本 → 创建新run → 检查基础数据 → 重算特征 → 顺序回放状态 → 生成快照 → 追平新增数据并检查修订 → 校验 → 事务切换active_run → 清理旧研究批次。

先构建再替换。失败时展示旧完整结果并显示重算失败；成功后列表、详情、参数一起切换。研究任务浏览器关闭后继续，重启后可恢复，重复点击幂等。

批次保存ruleId、ruleVersion、parameters、parametersHash、indicatorVersion、symbols、inputCutoff、inputRevision、startedAt、completedAt、progress、status和错误摘要。

新规则不得复用旧规则的事件基线和上一分类状态；只可在输入与特征版本、参数完全一致时复用特征。旧结果不需长期累积，保留配置与任务执行记录即可。

# 14. 调度与并发

观察池刷新默认15分钟；每个K线收盘后20～30秒增量更新；小时数据处理完后生成整点快照；启动及周期检查缺口；每日清理。

数据采集与研究重算并行，原始数据写入与同一symbol指标计算串行。实时更新优先于大批初始化。CPU重算使用后台工作线程，主线程提供API。所有外部请求共用限流器。

持久化任务包含类型、symbol或批次、输入范围、进度、重试次数、租约、最后错误和时间。任务断点必须可幂等重试。防止同一数据目录同时被两个应用实例调度。

SQLite开启WAL、忙等待、短事务；集中管理研究库写入。发生磁盘不足或事务失败时不推进进度。跨库摘要允许短暂落后，但必须能从交易对权威数据重建。

# 15. 前端布局与历史回看

紧凑亮色页面：顶部“现货监控”、北京时间选择、查看现在、前后逐小时、设置；下方三个分类标签与数量、搜索排序、紧凑列表。避免介绍页、大幅空白及架构描述。

列表字段：交易对、当前UW3、历史中位数、下降百分点、历史分位、六小时低位占比、状态时长、分类原因、数据质量。预警默认按确认时间倒序。

详情展示K线、UW3、历史中位数、低位参考、25%线、入池/转池/恢复标记。各图固定高度并共享时间位置；默认只显示回看时刻之前的数据，后续走势由用户主动展开。

输入10:37统一读取10:00快照；显示实际快照时间、数据时间和不足状态。列表与详情使用同一asOf。未来时间拒绝或明确限制，不静默用今天结果冒充历史。

设置面板提供研究参数和“清除并重算”；展示进度、成功或失败，不展示内部批次哈希、文件路径、异常栈。重算期间清晰标记仍在展示上次结果。颜色辅以文字，不以单独颜色表达状态。

生产界面不注入示例行情、演示币种或虚构分类。上游ticker如用于列表，需单独标明缓存时间，不把当前ticker放进过去页面冒充历史价格。

# 16. 本项目HTTP接口

| 方法/路径 | 职责 |
|---|---|
| GET /api/pools | 分类、计数、搜索、排序、分页 |
| GET /api/symbols/:symbol/series | K线、UW3、基线和标记 |
| GET /api/symbols/:symbol/history | 分类事件历史 |
| GET /api/research/settings | 生效参数及待应用参数 |
| PUT /api/research/settings | 校验保存待应用参数 |
| POST /api/research/rebuild | 启动清除重算 |
| GET /api/jobs/:id | 进度与状态 |
| GET /api/status | 上游、同步、计算状态 |
| GET /health/live | 进程存活 |
| GET /health/ready | 应用与本地存储就绪 |

查询支持asOf、pool、symbol、sort、order、page、pageSize。响应返回requestedAsOf、effectiveAsOf、dataAsOf、quality、counts、items、pagination。标记成员模式current或historical。

时间采用带明确时区的ISO格式或UTC毫秒。字段白名单、参数schema和SQL绑定必须落实。缓存键包含活动run和asOf，批次切换后失效。保护修改参数和重算写接口，不允许任意路径作为symbol或数据目录。

# 17. 历史名单与回测边界

上游watchlist仅提供当前名单；它本身不能还原过去90天每个小时的完整成员。首次回看应标明“当前观察池历史表现”，从本系统运行开始保存成员变更。changes可补部分事件，但不应未经全量核对就宣称恢复了全部历史名单。

下架、暂停、无数据保存明确状态，不自动替换交易对。后续价格仅用于评估，不参与当时分类。

比较规则版本时，固定数据修订、名单、时间段和基础指标版本。先比较池规模、入池时间、反复切换次数、停留时长，再看后续价格。不能只挑已拉盘截图验证阈值。

# 18. 生产配置与运行要求

```text
HOST=127.0.0.1
PORT=8790
DATA_DIR=./data
WATCHLIST_BASE_URL=http://127.0.0.1:8787
WATCHLIST_POLL_MINUTES=15
BINANCE_API_BASE=https://api.binance.com
KLINE_INTERVAL=15m
UW_HALF_LIFE_MINUTES=1440
RAW_RETENTION_DAYS=90
REVIEW_DAYS=90
BASELINE_DAYS=90
STATE_WARMUP_DAYS=14
EMA_HISTORY_DAYS=14
```

以上为配置样例，不包含生产上游域名或凭据。其余配置包括请求超时、重试、并发、限流、日志级别、研究参数和认证。

提供锁文件、生产构建、迁移、启动脚本、结构化日志和优雅退出。所有迁移带版本，禁止启动时破坏性重建已有数据库。对外部署需认证、写请求保护和正确的反向代理配置。

SQLite备份使用官方备份机制或正确处理WAL；不能只复制正在写入的主文件。数据与日志脱离构建目录，升级代码不删除数据。密钥不返回前端、不写普通日志。

# 19. 测试与验收清单

| 范围 | 必须通过 |
|---|---|
| 观察池 | 200/304/429/503、过期、空名单、可选字段缺省、全量对账 |
| 行情 | 分页边界、重叠去重、停机补齐、内部缺口、非法数据、未收盘过滤 |
| UW3 | 源函数逐点对比、flat、短上影、缺口复位、首值、24小时半衰期 |
| 来源 | 原生15分钟与参考分钟聚合对照，差异报告 |
| 特征 | 不含当前及未来、分位、覆盖不足、长窗口过期 |
| 状态 | 确认、恢复、转池、禁止重复、边界起点未知 |
| 回放 | 顺序实时输入与一次历史回放一致 |
| 重算 | 失败保留旧结果、原子启用、恢复、参数和结果同批 |
| 清理 | 不误删未结束状态、检查点和依赖历史 |
| 前端 | 紧凑亮色、三池、统一时间、详情、空态、重算进度 |

故障注入至少覆盖：保存K线后指标前崩溃、指标后快照前崩溃、初始化中重启、重算中重启、历史修订、单币失败、数据库不可写。重复执行相同任务不应产生重复K线、快照或事件。

因果测试：修改未来K线，较早结果不变。比较批处理和逐根输入结果。允许的研究规则实验与必须严格兼容的UW3测试分开。

所有验收记录写清真实接口、固定样本、模拟上游分别验证了什么，禁止以模拟数据测试通过代替真实双源对齐。

# 20. 开发顺序与交付

1. 骨架、数据库迁移、观察池适配器、单币分页初始化与恢复。
2. 原样复用UW3内核，完成黄金样本与来源对齐。
3. 历史特征和规则状态机，完成因果与实时/回放一致性。
4. 研究批次、清除重算、失败与重启恢复。
5. 前端三池列表、详情、历史时间与设置。
6. 并发、清理、备份、生产构建与部署验证。

交付源代码、锁文件、配置样例、迁移、生产构建、测试、接口文档、算法兼容说明、运维手册、真实验证记录。项目初始化数据和用户密钥不放源码包。

本文仅核验输入资料和参考算法。spot-monitor代码尚未开发，部署地址与真实行情来源对齐仍是实施阶段的验收项。

# 附录A：参考UW3函数

以下原文摘自已核验的ContinuityLiveViewer v1.21.1。调用时显式传入period=15、uwHalfLife=1440。TypeScript移植可加类型，但不得改变数值、null和重置语义。

```javascript
// Values are fractions in [0, 1]; the UI formats them as percentages.
export function uwSettings({period=3,uwHalfLife=60}={}){
  if(![1,3,5,15,30,60].includes(period))throw Error('不支持的UW周期');
  if(![30,60,120,240,360,1440].includes(uwHalfLife))throw Error('UW半衰期须为30、60、120分钟、4、6或24小时');
  return {period,halfLifeMinutes:uwHalfLife,wickBars:3,shadow:'upper',alpha:1-2**(-period/uwHalfLife)};
}
export function createUWCalculator(settings){
  const recent=[];let ema=null;
  return {push(c){
    const valid=[c.open,c.high,c.low,c.close].every(Number.isFinite)&&c.low>0&&c.high>=Math.max(c.open,c.close)&&c.low<=Math.min(c.open,c.close);
    const span=c.high-c.low;
    // Original UW convention: a known flat candle has no upper shadow.
    recent.push(valid?(span===0?0:Math.max(0,Math.min(1,(c.high-Math.max(c.open,c.close))/span))):null);
    if(recent.length>settings.wickBars)recent.shift();
    const result={time:c.time,uw3:null,zeroInput:null,zeroRate:null};
    if(recent.length===settings.wickBars&&recent.every(v=>v!==null)){
      result.uw3=recent.reduce((sum,v)=>sum+v,0)/settings.wickBars;
      result.zeroInput=Number(result.uw3===0);
    }
    ema=result.zeroInput===null?null:ema===null?result.zeroInput:ema+settings.alpha*(result.zeroInput-ema);
    result.zeroRate=ema;return result;
  }};
}
```

# 附录B：来源摘要与核验记录

核验日期：2026-11-12（北京时间）。

- 观察池文档：spot-watchlist V1.7.1，2026-11-11版；schemaVersion 1.0。
- 参考发布：ContinuityLiveViewer 1.21.1，BinanceUp仓库提交98e54d721f9af106ac419ff897d7de65051f886a。
- upper-wick.js与发布ZIP内容已做字节比较，一致。
- 已执行参考test/upper-wick.test.js，命令退出码0。该测试验证内核和合成集成数据，不代表生产双源行情已经对齐。

SHA-256（自动换行展示，核验时去除换行）：

**watchlist-api-guide.md**

`0a89e6becfaa7b08425c3e66163db1900086321c34dc9602ad3784baee6ec15a`

**upper-wick.js**

`0a07cd01978a473044ef5ce1348d09ec53da6af4179f35bdec1a3963ffa2df14`

**metrics.js**

`2186bc80cbcdc2e17589945de626e7d9a7729d527cee04f2e4e19f792e8e9c19`

**binance.js**

`8b24ab45d4d4501bd1c00f618685ce9fa001005ec9efaa2f269670a7999ba61a`

**Python research/uw.py**

`d9b51287062d13e8264e58c9d5a24dd2ce27fbf43a2726663aa3c51cfafcc4b8`

**ContinuityLiveViewer.zip**

`67c012e751ffebc6984214f1d4bc407bf4e9fbf2e76077aba7c6adc6e1b2421f`

官方现货接口文档索引：

<https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints>

接口限额、可访问域名和归档格式以实施时官方文档为准。本PDF中的上游观察池字段已对照用户提供的文档；该接口的生产主机地址需由部署方提供。
