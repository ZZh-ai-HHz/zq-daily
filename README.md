# 竞彩让球体检 · 云端版

每天北京时间 **09:30 / 17:30** 自动抓竞彩官方接口，跑让球三档校准，把结果推到手机。
不需要开着电脑，GitHub 的服务器替你跑（public 仓库完全免费）。

## 文件说明

| 文件 | 作用 |
|---|---|
| `zq_auto.py` | 主程序。零本地数据依赖，校准表内嵌，只需 numpy + 联网 |
| `push.py` | 推送器，按仓库 Secrets 自动选通道 |
| `zq_last.json` | 上一次快照，用于算「变盘」 |
| `.github/workflows/daily.yml` | 定时任务定义 |

## 部署 5 步

### 1. 建仓库
打开 https://github.com/new ，名字填 `zq-daily`，选 Public（私有也行，Secrets 一样安全），
**不要**勾选 "Add a README file"，直接 Create。

### 2. 上传文件
进入新仓库，点 **Add file → Upload files**，把这三个拖进去：
`zq_auto.py`、`push.py`、`zq_last.json`

### 3. 建 workflow
点 **Add file → Create new file**，文件名栏直接输入：

```
.github/workflows/daily.yml
```

（输入 `/` 会自动变成目录，这是 GitHub 的路径语法。）
把 `daily.yml` 的内容粘进去，Commit。

### 4. 加推送通道（选一个就够）
仓库 **Settings → Secrets and variables → Actions → New repository secret**

| Secret 名 | 值从哪来 |
|---|---|
| `WECOM_WEBHOOK` | 企业微信群 → 群设置 → 群机器人 → 添加 → 复制 webhook（微信里就能收到，无条数限制） |
| `SERVERCHAN_KEY` | sct.ftqq.com 微信扫码登录 → SendKey（推微信服务号「方糖」，免费 5 条/天） |
| `PUSHPLUS_TOKEN` | www.pushplus.plus 微信扫码 → 一对一推送 token |
| `FEISHU_WEBHOOK` | 飞书群 → 设置 → 群机器人 → 自定义机器人 → 复制 webhook |
| `BARK_URL` | iPhone 装 Bark，复制形如 `https://api.day.app/xxxx` 的地址 |
| `TG_BOT_TOKEN` + `TG_CHAT_ID` | Telegram @BotFather 建 bot |

只填一个即可，多个会同时推。

### 5. 手动验一次
**Actions** 页 → 左侧 `zq-daily` → 右侧 **Run workflow** → 跑完看手机有没有收到。

## 注意

- GitHub 的定时任务在整点高峰可能延迟 5–30 分钟，所以写在 :30 而不是 :00。
- 每次跑完会把 `zq_last.json` 自动 commit 回仓库，这样下次才有漂移基线。
- 想改时间：编辑 `daily.yml` 里的 cron（**UTC 时间**，北京时间减 8 小时）。
  09:30 北京 = `30 1 * * *`，17:30 北京 = `30 9 * * *`。
- 官方接口只在有在售期次时返回数据；休市日会返回 0 场，推送里会写「无让球盘」，属正常。
