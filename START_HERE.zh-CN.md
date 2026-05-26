# 从这里开始

如果你下载的是发布包，例如 `AI-News-Monitor-macOS.zip` 或
`AI-News-Monitor-Windows.zip`，目标流程是：解压、打开应用、在桌面界面填写
自己的信息、运行内置测试、开始监控。不要把 API Key、邮箱密码、Webhook 或
私人提示词写进源码仓库。

## 1. 打开应用

macOS:

- 解压发布包。
- 打开 `AI News Monitor.app`。
- 如果 macOS 提示未签名应用，右键点击 app，选择“打开”，再确认。

Windows:

- 解压发布包。
- 打开 `AI News Monitor/AI News Monitor.exe`。

如果你下载的是 GitHub 源码 zip，而不是发布包，请先安装 Python 3.11，再按
`README.zh-CN.md` 或 `docs/INSTALL.md` 里的命令运行。

## 2. 填写 LLM 设置

打开 Settings -> LLM Settings，填写：

- Provider：OpenAI、DeepSeek 或其他 OpenAI-compatible 服务。
- Base URL，例如 `https://api.openai.com/v1`。
- 模型名，例如 `gpt-4.1-mini`。
- 从服务商控制台复制的 API Key。

继续下一步前先点击 Test LLM。密钥只会写入本机运行目录里的 `.env` 文件。

## 3. 选择信息来源

打开 Settings -> Sources。

- 可以先保留默认 starter source packages。
- 也可以按需要启用具体来源包。
- 只添加公开且允许访问的 RSS/Atom feed。
- 不确定某个来源是否可用时，先用 Test Selected Source 测试。

## 4. 添加监控主题

打开 Topics，至少添加一个已启用主题。

- Name：简短名称。
- Prompt：说明你要监控什么。
- Keywords：关键人名、公司、政策词、产品名或股票代码。
- Output language：`zh-CN` 或 `en`。
- Source mode：首次配置建议用 `hybrid`。

正式运行前可以点击 Preview Source Selection，先看应用会选哪些来源。

## 5. 配置通知

如果希望手机收到告警，打开 Settings -> Notifications，至少配置一个通知渠道。

- Email 通常需要 app password，不是普通登录密码。
- Telegram 需要 bot token 和 chat ID。
- Webhook、WeCom、WeChat relay、QQ relay 等第三方服务会接触通知正文和链接，
  使用前请确认隐私策略、限额和稳定性。

开始监控前点击对应渠道的 Test 按钮。若只想在本机应用和浏览器控制台查看告警，
可以先跳过通知。

## 6. 验证并运行

- 打开本地控制台：`http://127.0.0.1:8765`。
- 用 E2E Test 验证本机 fetch -> LLM -> alert -> notification 链路。
- 用 Run Once 跑一轮真实监控。
- readiness 正常后再开始长期监控，并保持电脑唤醒。

本机运行文件会自动创建在：

- macOS: `~/Library/Application Support/AI News Monitor/`
- Windows: `%APPDATA%/AI News Monitor/`
