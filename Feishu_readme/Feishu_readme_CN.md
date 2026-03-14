
# Feishu 配置到 `codexloop init` 输入 `chat id` 为止

这份文档只覆盖一件事：

从 0 开始准备飞书机器人所需信息，然后在当前项目里执行 `codexloop init`，并把 `Feishu chat id` 填进去为止。

不展开后续 `/run`、`/inject`、消息收发验证和故障排查。

## 0. 先确认本地前置条件

进入当前仓库目录：

```bash
cd ./ArgusBot
```

确认 `codex` 和 `codexloop` 可用：

```bash
codex --help
codexloop help
```

如果 `codexloop` 不在 PATH，先在当前仓库安装：

```bash
pip install -e .
```

## 1. 在飞书开放平台创建自建应用

1. 打开飞书开放平台[https://open.feishu.cn/app]。
2. 进入“开发者后台”。
3. 创建一个“自建应用”。
4. 给应用起一个容易识别的名字，例如 `ArgusBot Control`。
5. 创建完成后，进入应用详情页。

你后面会用到两个值：

- `App ID`
- `App Secret`

把它们记下来，后面 `codexloop init` 会要求输入：

- `Feishu app id`
- `Feishu app secret`

<div align="center">
<img src="first.png" width="1000">
</div>

<div align="center">
<img src="Feishu_readme/second.png" width="1000">
</div>

<div align="center">
<img src="Feishu_readme/third.png" width="1000">
</div>

## 2. 准备一个专用飞书群

建议单独建一个群，专门给这个仓库使用，例如：

- 群名：`ArgusBot Control`

然后把刚创建的应用机器人加进这个群里。

这样做的原因很简单：

- 这个仓库当前的飞书控制通道是按 `chat_id` 轮询读取消息
- 一个群对应一个 `chat_id`
- 单独使用一个群最不容易串消息

## 3. 拿到这个群的 `chat_id`

你需要拿到刚才那个专用群的会话 ID。

可行做法是：

1.点开聊天群，点击右上角三个点
2.拉至最底下，即可看见chat_id

如果你拿到的是别的 ID 类型，这个项目后面会发不进群，也轮询不到命令。

<div align="center">
<img src="Feishu_readme/add_bot.png" width="1000">
</div>


<div align="center">
<img src="Feishu_readme/find_chatid.png" width="100">
</div>

## 4. 理解这里要的 `chat_id` 是什么

这个项目里配置的 `Feishu chat id` 不是用户 ID，也不是 open_id。

它要的是“会话 ID / 群聊 ID”，也就是飞书消息接口里的 `chat_id`。在本项目代码中，飞书消息发送和轮询都直接使用这个值作为会话标识。

通常它会长得像这样：

```text
oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 5. 在当前项目里执行 `codexloop init`

确认你当前就在目标项目目录下：

```bash
cd ./ArgusBot
```

然后执行：

```bash
codexloop init
```

初始化过程中会出现类似下面这些问题：

```text
Default check command (optional):(一般可以直接回车跳过)
Select model preset:
Select play mode:
Enable Feishu bidirectional control? [y/N]:
Feishu app id:
Feishu app secret:(为了保证安全性，在输入密码后不会类似app id显示出来，复制粘贴后回车即可)
Feishu chat id:
```

这里按顺序填写：

1. `Enable Feishu bidirectional control?`
输入 `y`

2. `Feishu app id:`
输入你在飞书开放平台看到的 `App ID`

3. `Feishu app secret:`
输入你在飞书开放平台看到的 `App Secret`

4. `Feishu chat id:`
输入你刚才拿到的目标群 `chat_id`

到这里，这份文档就结束。

## 6. 你填完以后，配置会写到哪里

`codexloop init` 会把配置写到当前项目下的：

```text
.codex_daemon/daemon_config.json
```

其中飞书相关字段是：

```json
{
  "feishu_app_id": "...",
  "feishu_app_secret": "...",
  "feishu_chat_id": "oc_xxx"
}
```

## 7. 一个最短检查清单

在执行 `codexloop init` 之前，你只需要确认这 4 件事：

- 已创建飞书自建应用
- 已拿到 `App ID`
- 已拿到 `App Secret`
- 已拿到目标群的 `chat_id`

如果这 4 个值齐了，就可以开始 `codexloop init` 并把 `Feishu chat id` 填进去。
