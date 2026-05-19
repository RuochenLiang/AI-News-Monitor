# AI News Monitor

[English](README.md)

AI News Monitor 是一个本地优先的桌面应用和临时本地服务器，用来监控公开的中文和英文信息源，根据用户主题筛选高相关信息，并通过用户自己的 OpenAI-compatible LLM 完成翻译、摘要、相关性确认和可选深度分析，最后把及时告警发送到适合手机查看的渠道。

本项目不是交易机器人，不连接券商 API，不下单，也不提供个性化投资建议。告警只是 AI 辅助的信息监控结果；采取任何行动前请自行核验原始链接。

## 许可证和 AI 披露

本项目使用 `GPL-3.0-only` 许可证发布，详见 [LICENSE](LICENSE)。

本项目在开发过程中使用了 AI 辅助。AI 辅助生成的代码、文档和测试应由项目所有者或贡献者在发布前审查、测试和维护。详见 [AI_DISCLOSURE.md](AI_DISCLOSURE.md)。

## 安全提醒

不要提交 `.env`、`config.yaml`、`user_config.yaml`、`data/`、`logs/`、SQLite 数据库、API Key、SMTP 凭据、Webhook URL、Telegram Token、Chat ID 或私人提示词。仓库只应包含 `.env.example` 和 `config.example.yaml` 示例文件。

## 开发提示词档案

历史开发提示词以独立 Markdown 文件保存在 [docs/dev-history/prompts/](docs/dev-history/prompts/)，文件名会直接概括每个提示词的主要用途。完整合并版本仍保留在 [docs/dev-history/prompt.md](docs/dev-history/prompt.md)。这些文件只是项目历史，不是正常安装或使用所需文件。

提示词顺序如下：

1. [01-build-lightweight-desktop-ai-news-monitor.md](docs/dev-history/prompts/01-build-lightweight-desktop-ai-news-monitor.md)
2. [02-expand-into-24-7-global-information-agent.md](docs/dev-history/prompts/02-expand-into-24-7-global-information-agent.md)
3. [03-add-presets-minimal-ui-and-source-management.md](docs/dev-history/prompts/03-add-presets-minimal-ui-and-source-management.md)
4. [04-improve-fast-alerts-ui-i18n-sources-notifications.md](docs/dev-history/prompts/04-improve-fast-alerts-ui-i18n-sources-notifications.md)
5. [05-prepare-v0-9-open-source-release-candidate.md](docs/dev-history/prompts/05-prepare-v0-9-open-source-release-candidate.md)
6. [06-stabilize-llm-email-source-diagnostics-and-setup-ux.md](docs/dev-history/prompts/06-stabilize-llm-email-source-diagnostics-and-setup-ux.md)
7. [07-add-source-reliability-freshness-and-intelligence-gaps.md](docs/dev-history/prompts/07-add-source-reliability-freshness-and-intelligence-gaps.md)
8. [08-finalize-github-upload-readiness-and-release-gates.md](docs/dev-history/prompts/08-finalize-github-upload-readiness-and-release-gates.md)
9. [09-prove-e2e-alert-delivery-and-clean-browser-console.md](docs/dev-history/prompts/09-prove-e2e-alert-delivery-and-clean-browser-console.md)
10. [10-clean-root-for-final-github-upload.md](docs/dev-history/prompts/10-clean-root-for-final-github-upload.md)
11. [11-verify-next-phase-features-and-runtime-stability.md](docs/dev-history/prompts/11-verify-next-phase-features-and-runtime-stability.md)

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

浏览器控制台 `http://127.0.0.1:8765` 现在只作为只读监控端，用来查看实时状态、readiness、pipeline funnel、来源健康、通知状态、简洁实时事件、日志和最近告警。它提供 Run Once 和 E2E Test 控件，但配置和凭据仍然在桌面应用里填写。高级用户仍可在本机运行目录中直接编辑 `config.yaml` 和 `.env`。

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
Fetched 441 -> Language 390 -> Keyword 12 -> New 3 -> LLM 2 -> Alerts 0
```

如果本轮 0 告警，控制台会说明主要阻塞点：关键词不匹配、重复、语言不支持、LLM 判定不够相关、低于阈值、冷却中、来源限流、缺少通知渠道或通知失败。低于阈值时会显示最高被拒候选分数和主题阈值。测试全链路时优先使用 E2E Test，或只在测试时临时把阈值降到 50-60；生产监控仍建议保持较高阈值以减少噪音。

## LLM 设置

普通用户通常只需要填写：

- Base URL，例如 `https://api.openai.com/v1`
- 模型名，例如 `gpt-4.1-mini`
- 从提供商控制台复制的 API Key

如果 LLM 测试失败：`invalid_api_key` 表示需要重新复制或生成 Key；`model_not_found` 表示模型名不匹配；`base_url_unreachable`/`network_unreachable` 通常与 URL、网络、VPN、代理或防火墙有关；`unsupported_model_api` 表示该 endpoint 不兼容 OpenAI 风格的 `/chat/completions`。

## 告警模式

默认使用 Fast Alert，内容包括原文标题、链接、翻译标题、来源、发布时间、短摘要、市场观察建议、建议用户操作、匹配原因、关键词/实体、来源可靠性、多来源聚合上下文和质量排序解释。

Full Analysis 是可选模式，会增加 why-it-matters、情景路径、风险和不确定性等更长字段。

## 来源和通知

内置来源包包括 Global News、Finance、Official/Government、China/Taiwan、US Policy、Semiconductor/AI、Company IR、Taiwan + Semiconductor + Official Sources、Geopolitics Starter 和 AI Industry Starter。只添加公开 RSS/Atom feed 或免费公开 API，不要添加付费墙、登录后、私有或未授权抓取来源。详见 [SOURCE_GUIDE.md](SOURCE_GUIDE.md)。

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
- 多来源确认：告警会说明事件是否被多个独立来源确认，并对同一所有者重复确认降低权重。

GDELT 诊断会同时测试生产形状的主题查询和一个简单 smoke 查询。非 JSON 响应、超长查询、异常查询形状、429 限流和超时都会被分类并给出建议。Yahoo Finance 429 会归类为 `api_rate_limited`，进入来源退避；Finance Starter 里还有其他公开财经来源可作为补充。

通知支持 Email、Telegram、WeCom、WeChat relay、QQ relay 和 Generic webhook，并支持重试和回退顺序。第三方 relay 会接触通知正文和链接，使用前请确认其隐私策略、限额和稳定性。详见 [NOTIFICATION_GUIDE.md](NOTIFICATION_GUIDE.md)。

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
