# AI News Monitor

[English](README.md)

AI News Monitor 是一个本地优先的桌面应用和临时本地服务器，用来监控公开的中文和英文信息源，根据用户主题筛选高相关信息，并通过用户自己的 OpenAI-compatible LLM 完成翻译、摘要、相关性确认和可选深度分析，最后把及时告警发送到适合手机查看的渠道。

本项目不是交易机器人，不连接券商 API，不下单，也不提供个性化投资建议。告警只是 AI 辅助的信息监控结果；采取任何行动前请自行核验原始链接。

## 许可证和 AI 披露

本项目使用 `GPL-3.0-only` 许可证发布，详见 [LICENSE](LICENSE)。

本项目在开发过程中使用了 AI 辅助。AI 辅助生成的代码、文档和测试应由项目所有者或贡献者在发布前审查、测试和维护。详见 [docs/project/AI_DISCLOSURE.md](docs/project/AI_DISCLOSURE.md)。

## 安全提醒

不要提交 `.env`、`config.yaml`、`user_config.yaml`、`data/`、`logs/`、SQLite 数据库、API Key、SMTP 凭据、Webhook URL、Telegram Token、Chat ID 或私人提示词。仓库只应包含 `.env.example` 和 `config.example.yaml` 示例文件。

## 普通用户最短路径

如果下载的是发布包，请先看 [START_HERE.zh-CN.md](START_HERE.zh-CN.md)。它按“解压 -> 打开应用 -> 填 LLM/来源/主题/通知 -> 测试 -> 开始监控”的顺序说明。

如果下载的是 GitHub 源码 zip，请使用下面的快速运行命令。源码运行仍需要先安装 Python 3.11。

## 文档入口

主要文档入口是 [docs/README.md](docs/README.md)。

- [安装和运行](docs/INSTALL.md)
- [来源策略和来源包](docs/guides/SOURCE_GUIDE.md)
- [通知设置](docs/guides/NOTIFICATION_GUIDE.md)
- [LLM Provider 设置](docs/LLM_PROVIDERS.md)
- [验证流程](docs/VERIFICATION_PIPELINE.md)
- [架构](docs/ARCHITECTURE.md)
- [路线图](docs/ROADMAP.md)
- [Wiki 草稿](docs/wiki/Home.md)
- [GitHub About 信息](docs/github/ABOUT.md)
- [开发提示词档案](docs/dev-history/README.md)

第 15 个提示词加入了下一版基础能力：manual / auto / hybrid 来源模式、主题配置编辑、验证门控、可选社交媒体信号、事件聚合，以及 OpenAI / DeepSeek Provider 路由。英文说明见 [docs/LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md)、[docs/SOCIAL_SOURCES.md](docs/SOCIAL_SOURCES.md) 和 [docs/VERIFICATION_PIPELINE.md](docs/VERIFICATION_PIPELINE.md)。

来源模式说明：

- `manual`: 只使用用户手动配置的来源，这是旧配置的兼容默认值。
- `auto`: 根据主题领域自动选择来源。
- `hybrid`: 先使用手动来源，再补充自动选择的高质量来源。

浏览器控制台的 Sources 页面会显示 Source Selection，说明每个来源为什么被选择、预期价值、风险提示和优先级。告警卡片会显示核验状态、相关性分数、置信度分数、来源对比、时间线和链接。社交媒体单独作为证据时会标记为未确认信号，不应当当作已核验事实。

桌面应用的 Topics 页面可以编辑主题 ID、来源模式、领域、优先地区、是否启用社交媒体、最低相关度、最低置信度和报告结构开关。旧配置缺少这些字段时仍按 `manual` 模式运行，并默认关闭社交媒体来源。

桌面应用的 Settings 页面可以配置 OpenAI / DeepSeek Provider 路由、回退 Provider、本地 API Key，以及默认关闭的 X.com Recent Search 设置。密钥写入本地 `.env`，不会写入源码。
Topics 页面里的“预览来源选择”可以在运行监控前查看手动来源和自动选择来源，包括选择原因、预期价值、风险和优先级。
每个主题的报告结构开关可以隐藏时间线、来源对比或建议操作，让某些主题的告警更短。

可以不打开桌面 UI，直接运行诊断命令：

```bash
python -m ai_news_monitor doctor --check-llm
python -m ai_news_monitor doctor --check-sources
```

## macOS 快速运行

先安装 Python 3.11，然后运行：

```bash
cd "/path/to/AI-News-Monitor"
./scripts/run_macos.sh
```

脚本会在需要时创建 `~/.venvs/ai-news-monitor` 虚拟环境，安装依赖并启动应用。

本地浏览器控制台默认地址：

```text
http://127.0.0.1:8765
```

健康检查和状态端点：

```text
http://127.0.0.1:8765/health
http://127.0.0.1:8765/readiness
http://127.0.0.1:8765/status
http://127.0.0.1:8765/events
```

`/health` 只表示本地 HTTP 服务器还活着。`/readiness` 才表示监控是否真正可用，会汇总监控状态、LLM、通知、来源覆盖、严重缺口、最近一轮结果，以及现在是否能发送告警。

## Windows 快速运行

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## 首次配置

首次启动时，如果可执行文件旁边没有 `config.yaml` 或 `.env`，应用会在系统应用数据目录创建本机运行文件。

- macOS: `~/Library/Application Support/AI News Monitor/`
- Windows: `%APPDATA%/AI News Monitor/`

开始监控前，请在桌面应用的 Settings、Sources、Topics 和 Notifications 页面配置：

- LLM API Key、模型名和 OpenAI-compatible Base URL
- 至少 1 个监控主题
- 来源包或自定义 RSS/Atom feed
- 至少 1 个通知渠道
- Fast Alert 或 Full Analysis 模式

浏览器控制台 `http://127.0.0.1:8765` 现在只作为只读监控端，用来查看实时状态、readiness、pipeline funnel、事件聚合、来源健康、通知状态、简洁实时事件、日志和最近告警。它提供 Run Once 和 E2E Test 控件，但配置和凭据仍然在桌面应用里填写。高级用户仍可在本机运行目录中直接编辑 `config.yaml` 和 `.env`。

## 诊断和测试按钮

开始长时间监控前，建议先在桌面应用中运行测试：

- Settings > LLM Settings > Test LLM 会检查必填字段、API Key、可用时的模型列表接口，以及 chat completions 接口。
- Sources > Test Selected Source 会测试选中的 RSS/Atom feed 或公开来源候选。
- Notifications > Test 会给指定渠道发送测试消息，并显示错误分类、建议修复、已脱敏技术细节和缺少字段。
- 浏览器控制台的 Run Once 会立刻运行一轮真实监控。
- 浏览器控制台的 E2E Test 会使用标记为 `[E2E TEST]` 的本地固定测试文章，用来验证 fetch -> candidate -> LLM -> alert -> notification 全链路，不依赖实时新闻。

常见错误分类包括 `missing_required_field`、`invalid_url`、`invalid_email_address`、`invalid_api_key`、`model_not_found`、`unsupported_model_api`、`base_url_unreachable`、`api_auth_failed`、`api_rate_limited`、`api_timeout`、`api_bad_response`、`query_too_long`、`unsupported_query_shape`、`invalid_encoded_query`、`tls_or_certificate_error`、`network_unreachable`、`proxy_or_firewall_issue`、`smtp_auth_failed`、`smtp_starttls_failed`、`smtp_sender_rejected`、`smtp_recipient_rejected`、`smtp_connection_timeout`、`smtp_provider_blocked`、`webhook_unreachable`、`webhook_http_error`、`webhook_auth_failed`、`feed_unreachable`、`feed_parse_failed`、`feed_empty`、`source_language_unsupported`、`local_server_port_in_use`、`sse_connection_failed` 和 `unknown_error`。

## Pipeline Funnel 和 0 告警

每一轮都会记录一个简洁 funnel，例如：

```text
Fetched 441 -> Dedupe 390 -> Candidates 12 -> Events 3 -> LLM 2 -> Alerts 0
```

如果本轮 0 告警，控制台会说明主要阻塞点：关键词不匹配、重复、语言不支持、LLM 判定不够相关、低于阈值、冷却中、来源限流、缺少通知渠道或通知失败。低于阈值时会显示最高被拒候选分数和主题阈值。事件诊断会区分已抓取文章、去重后文章、候选、事件聚合、送入 LLM 的事件聚合、生成的事件告警和通知。测试全链路时优先使用 E2E Test，或只在测试时临时把阈值降到 50-60；生产监控仍建议保持较高阈值以减少噪音。

## LLM 设置

普通用户通常只需要填写：

- Base URL，例如 `https://api.openai.com/v1`
- 模型名，例如 `gpt-4.1-mini`
- 从提供商控制台复制的 API Key

事件综合和翻译默认优先使用 API 强制的 JSON Schema Structured Outputs。若当前 OpenAI-compatible 服务商只支持 `response_format: {"type": "json_object"}`，应用会自动回退到 JSON mode，并且仍会在本地继续解析和校验输出。

如果 LLM 测试失败：`invalid_api_key` 表示需要重新复制或生成 Key；`model_not_found` 表示模型名不匹配；`base_url_unreachable`/`network_unreachable` 通常与 URL、网络、VPN、代理或防火墙有关；`unsupported_model_api` 表示该 endpoint 不兼容 OpenAI 风格的 `/chat/completions`。

## 告警模式

默认使用 Fast Alert。若多篇文章描述同一事件，应用会先把它们聚合成一个事件，再发送一条综合告警，内容包括事件标题、当前状态、事件级摘要、时间线、关键事实、来源链接、相关文章为何相关、不确定性和建议跟进。若只有单篇来源可用，也会生成一个单来源事件告警，不会人为扩写成复杂事件。

Full Analysis 是可选模式，会增加 why-it-matters、情景路径、风险和不确定性等更长字段。

## 来源和通知

内置来源包包括 Global News、Finance、Official/Government、China/Taiwan、US Policy、Semiconductor/AI、Company IR、Taiwan + Semiconductor + Official Sources、Geopolitics Starter 和 AI Industry Starter。只添加公开 RSS/Atom feed 或免费公开 API，不要添加付费墙、登录后、私有或未授权抓取来源。详见 [docs/guides/SOURCE_GUIDE.md](docs/guides/SOURCE_GUIDE.md)。

## 来源可靠性和覆盖质量

来源现在带有明确的可靠性元数据：

- Tier 1：官方、第一手、通讯社或公司/机构直接来源。
- Tier 2：主流媒体或成熟财经/科技媒体。
- Tier 3：专业、垂直、本地或领域型来源。
- Tier 4：聚合器、博客、转载较多来源或低信心自定义来源。

每个来源还可以显示角色、国家/政府关联、propaganda risk、编辑背景、可靠性分数、新鲜度、连续失败次数、最近返回文章数、缓存状态和智能退避状态。

Dashboard 和只读浏览器控制台会显示：

- 情报缺口：来源包、类别、语言或主题关键来源组是否禁用、过旧、空返回或失败。
- 覆盖质量：当前监控覆盖是 `high`、`medium`、`low` 还是 `critical`。
- 来源包状态：已启用包、实际启用来源数、新鲜来源数，以及没有启用来源包或来源包不新鲜时的提示。
- Last-known-good fallback：来源失败时可使用本地最后一次成功数据辅助诊断，但默认不会用缓存文章产生新告警。
- 事件聚合和多来源确认：当多篇文章共享主题词、关键实体、来源背景和接近的发布时间时，应用会把它们合并成一条事件级告警。告警会说明文章为何相关、列出来源链接，并对同一所有者重复确认降低权重。
- 时间线安全：时间线只使用来源元数据和文章文本。像 `2026-05-25` 或 `May 25, 2026` 这样的明确来源日期可以进入时间线；只有月日等不完整日期会留在说明中，不会自行补年份。未知日期保持未知；如果使用发布时间推断，会明确标注。需要可靠时间线时，应优先配置官方或第一手来源。

GDELT 诊断会同时测试生产形状的主题查询和一个简单 smoke 查询。非 JSON 响应、超长查询、异常查询形状、429 限流和超时都会被分类并给出建议。Yahoo Finance 429 会归类为 `api_rate_limited`，进入来源退避；Finance Starter 里还有其他公开财经来源可作为补充。

通知支持 Email、Telegram、WeCom、WeChat relay、QQ relay 和 Generic webhook，并支持重试和回退顺序。第三方 relay 会接触通知正文和链接，使用前请确认其隐私策略、限额和稳定性。详见 [docs/guides/NOTIFICATION_GUIDE.md](docs/guides/NOTIFICATION_GUIDE.md)。

Gmail 推荐使用 `smtp.gmail.com`、端口 `587` 和 STARTTLS。SMTP 用户名和 From 地址通常都填写发件 Gmail；Recipients 是接收告警的邮箱。From 地址是必填项；如果它和 SMTP 用户名不同，应用会显示 warning，因为有些服务商会拒绝未授权别名。Gmail 通常需要开启两步验证并生成 app password，普通登录密码通常会导致 `smtp_auth_failed`。

## 开发

```bash
./scripts/bootstrap_macos.sh
source "$HOME/.venvs/ai-news-monitor/bin/activate"
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall src tests
```

如果启动时提示缺少 `PySide6`、`feedparser` 等依赖，请使用提示中的 Python 解释器运行：

```bash
python -m pip install -r requirements.txt
```
