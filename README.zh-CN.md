# Ntfy Clipboard

**iPhone 短信 → ntfy → Windows 验证码剪贴板**

[English README](README.md)

这是一个 Windows 桌面小工具：iPhone 通过“快捷指令”把短信转发到 ntfy，Windows 端接收后先复制完整短信，再提取 4 位或 6 位验证码并复制。当前剪贴板是验证码，按 `Win+V` 时上一条是完整短信。

![Ntfy Clipboard 中文界面](docs/screenshot-zh.png)

## 主要功能

- 图形界面，不需要命令行。
- 常驻 Windows 右下角托盘。
- 托盘菜单：**打开管理**、**开始监听**、**停止监听**、**退出**。
- 关闭窗口时隐藏到托盘，监听继续运行。
- 支持 **Windows 登录时自动启动**，启动后最小化到托盘。
- 右上角支持 **中文 / English** 切换。
- ntfy 断线重连、消息去重。
- 支持公共 `ntfy.sh`、自建 ntfy、Bearer Token、Basic Auth。
- 支持全角数字、空格/短横线分隔，以及 Google 风格 `G-123456` / `G-123-456`。
- 支持带操作按钮的 Windows 原生通知。
- 不会从 `1234567` 中错误截取 `123456` 或 `234567`。

![测试与日志](docs/screenshot-tools.png)

## 快速添加 iPhone 捷径

可以直接使用这个公开的 iCloud 捷径：

https://www.icloud.com/shortcuts/2e72a660dec84fd9b8c7abd92d42043f

软件右上角也有 **iPhone 捷径** 按钮，会显示二维码，直接用 iPhone 相机扫描即可打开。

![iPhone 捷径二维码](docs/screenshot-shortcut.png)

导入步骤：

1. 用 iPhone 相机扫描二维码，或在 Safari 中打开链接；
2. 点击 **添加快捷指令**；
3. 服务器保持 `https://ntfy.sh`（或填写你的自建服务器）；
4. topic 粘贴软件里复制的 **主题 Topic**；
5. 完成添加后，在 **快捷指令 → 自动化** 会出现一条 **我收到包含“【”的信息时** 的自动化。它默认是关闭的，需要手动打开右侧开关后才能使用；
6. 如果只想处理验证码短信，可以把自动化条件改成 `验证码` 或 `校验码`。

这个捷径会以 JSON 方式向 ntfy 发布消息，基于谢週五公开的 ntfy 推送通知捷径。如果重复导入，会出现两条自动化，删除多余的一条即可。

## 快速开始

### 1. 获取软件

在项目目录执行：

```powershell
cd D:\CodePlayground\ntfy
.\build.ps1
```

生成：

```text
D:\CodePlayground\ntfy\NtfyClipboard.exe
```

发布到 GitHub 时，可以把 `NtfyClipboard.exe` 作为 Release 附件上传；仓库默认不提交这个二进制文件。

### 2. 启动软件

双击 `NtfyClipboard.exe`。

首次启动会自动生成随机 topic。软件里的 **发布地址** 就是 iPhone 快捷指令需要填写的 URL。

点击 **开始监听**，状态变成 **正在监听**，右下角出现托盘图标。

### 3. 配置 iPhone 快捷指令

1. 打开“快捷指令” → “自动化” → `+`；
2. 选择“信息”触发器；
3. 条件设置为“信息包含”“验证码”或“校验码”，并选择“立即运行”；
4. 添加“获取文本”动作，把短信转成纯文本；
5. 添加“获取 URL 内容”：
   - URL：软件里的“发布地址”
   - 方法：`POST`
   - 请求正文：`文本`，选择短信文本
   - 请求头：`Content-Type` = `text/plain; charset=utf-8`
6. 保存自动化。

软件右上角的 **使用说明** 里也内置了相同步骤。

### 4. 发送测试短信

在软件里点击 **发送测试短信**。

软件会发送：

```text
验证码为 482913，5分钟内有效。
```

几秒后：

- 当前剪贴板变成 `482913`；
- 按 `Win+V` 可以看到验证码和完整短信。

## 剪贴板顺序

默认先写完整短信，等待 `350 ms`，再写验证码。

要保留完整短信记录，请开启：

**Windows 设置 → 系统 → 剪贴板 → 剪贴板历史记录**

如果不希望验证码同步到其他设备，请关闭剪贴板的跨设备同步。

间隔可以在 **高级设置** 中调整。

## Windows 通知

收到短信并识别出验证码后：

1. 立即弹出短通知：
   - 标题：**已复制验证码：123456**
   - 按钮：**查看完整短信**
   - 通知过几秒会自动消失。
2. 约 8 秒后再弹出完整短信通知：
   - 标题：**收到短信**
   - 正文：完整短信内容
   - 按钮：**复制**
   - 这条通知会保留在 Windows 通知中心，直到手动关闭。

点击 **复制** 会再次把验证码写入剪贴板，并显示“已复制验证码”的确认通知。

如果没有识别到验证码，只显示完整短信通知。通知按钮需要后台监听服务保持运行才能正常使用。

## 验证码识别

支持：

```text
1234
123456
G-123456
G-123-456
验证码：123456
校验码：12-34
```

不会从长数字中截取：

```text
1234567     → 不识别
G-1234-567  → 不识别
```

同时会尽量排除手机号、日期、金额、快递单号、订单号等干扰。

可以单独测试：

```powershell
python -m ntfy_clipboard --extract "Your Google verification code is G-123-456."
```

## 托盘与开机自启

- 软件运行期间托盘图标常驻；
- 双击托盘图标或选择 **打开管理** 显示窗口；
- 关闭窗口会隐藏到托盘；
- 托盘菜单选择 **退出** 才会停止监听并退出；
- 勾选 **Windows 登录时自动启动** 后，登录时以最小化到托盘的方式启动。

## 中英文切换

右上角按钮：

- 当前中文时显示 `English`，点击切换到英文；
- 当前英文时显示 `中文`，点击切换到中文。

语言会保存到 `config.json`。

## 配置文件

`config.json` 与 `NtfyClipboard.exe` 放在同一目录：

```json
{
  "server": "https://ntfy.sh",
  "topic": "replace-with-a-long-random-topic",
  "token": "",
  "username": "",
  "password": "",
  "since": "",
  "clipboard_gap_ms": 350,
  "state_file": "state.json",
  "log_file": "logs/ntfy-clipboard.log",
  "reconnect_min_seconds": 1,
  "reconnect_max_seconds": 60,
  "language": "zh-CN"
}
```

| 字段 | 说明 |
| --- | --- |
| `server` | `https://ntfy.sh` 或自建 ntfy 地址 |
| `topic` | iPhone 快捷指令和 Windows 端共用的随机 topic |
| `token` | 受保护 topic 的 Bearer Token |
| `username` / `password` | Basic Auth 账号密码 |
| `since` | 留空只收新消息；收到第一条后会自动使用消息 ID |
| `clipboard_gap_ms` | 完整短信与验证码的写入间隔 |
| `language` | `zh-CN` 或 `en` |

## 从源码运行

```powershell
python -m pip install -e .
python -m ntfy_clipboard.gui
```

打包：

```powershell
.\build.ps1
```

## 开发与测试

```powershell
python -m unittest discover -s tests -v
ruff check ntfy_clipboard tests
ruff format --check ntfy_clipboard tests
```

## 命令行模式

桌面版是主要入口，命令行保留用于调试和高级用法：

```powershell
python -m ntfy_clipboard --config .\config.json --check
python -m ntfy_clipboard --config .\config.json --send "验证码为 482913，5分钟内有效。" --title "SMS"
python -m ntfy_clipboard --config .\config.json --service
```

## 安全说明

- 公共 ntfy 的 topic 相当于密码，请使用长随机字符串。
- 短信和验证码会经过 ntfy 服务端；敏感场景建议自建 ntfy 并启用认证。
- 日志只记录消息 ID 和是否找到验证码，不记录短信正文。
- Windows 剪贴板历史可能同步到云端，如不需要请关闭跨设备同步。

## 项目结构

```text
ntfy_clipboard/
  entry.py          单文件 exe 入口：GUI 或后台服务
  gui.py            Tkinter 桌面界面与托盘
  i18n.py           中英文翻译
  app.py            消息 → 剪贴板业务逻辑
  clipboard.py      Windows 剪贴板写入
  extractor.py      验证码识别
  ntfy_client.py    ntfy 发布/订阅
  service.py        后台重连循环
  state.py          最近消息 ID 持久化
  startup.py        Windows 开机自启注册表
  runtime.py        子进程和 PID 辅助
tests/              单元测试与 GUI 冒烟测试
assets/             应用图标和托盘图标
docs/               脱敏后的界面截图
build.ps1           构建单文件 exe
config.example.json 配置模板
```
