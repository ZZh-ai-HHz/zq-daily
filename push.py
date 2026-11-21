# -*- coding: utf-8 -*-
"""把 zq_auto.py 生成的文本推到手机。按环境变量自动选通道，配了哪个用哪个。

支持:
  WECOM_WEBHOOK          企业微信群机器人 webhook（微信里能收到，无条数限制，最推荐）
  SERVERCHAN_KEY         Server酱 SendKey（推微信服务号「方糖」，免费 5 条/天）
  PUSHPLUS_TOKEN         PushPlus token（推微信公众号，免费有日限）
  FEISHU_WEBHOOK         飞书群自定义机器人
  BARK_URL               Bark（iPhone）
  TG_BOT_TOKEN + TG_CHAT_ID   Telegram
一个都没配 -> 只打印到日志，不推送（不影响任务成功）。

用法: python push.py out.txt "标题"
"""
import os, sys, json, urllib.request, urllib.parse

TITLE_DEFAULT = "竞彩让球体检"


def post_json(url, data):
    req = urllib.request.Request(url, data=json.dumps(data, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(errors="ignore")


def post_form(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(errors="ignore")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "out.txt"
    title = sys.argv[2] if len(sys.argv) > 2 else TITLE_DEFAULT
    with open(path, encoding="utf-8") as f:
        msg = f.read()
    if len(msg) > 8000:
        msg = msg[:8000] + "\n...(已截断)"

    wecom = os.environ.get("WECOM_WEBHOOK", "").strip()
    sc = os.environ.get("SERVERCHAN_KEY", "").strip()
    pplus = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    wh = os.environ.get("FEISHU_WEBHOOK", "").strip()
    bark = os.environ.get("BARK_URL", "").strip()
    tg_tok = os.environ.get("TG_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TG_CHAT_ID", "").strip()

    sent = 0
    if wecom:
        r = post_json(wecom, {"msgtype": "text", "text": {"content": f"{title}\n\n{msg}"}})
        print(f"[企业微信] {r[:200]}"); sent += 1
    if sc:
        r = post_form(f"https://sctapi.ftqq.com/{sc}.send", {"title": title, "desp": msg})
        print(f"[Server酱] {r[:200]}"); sent += 1
    if pplus:
        r = post_json("https://www.pushplus.plus/send",
                      {"token": pplus, "title": title, "content": msg, "template": "txt"})
        print(f"[PushPlus] {r[:200]}"); sent += 1
    if wh:
        r = post_json(wh, {"msg_type": "text", "content": {"text": f"{title}\n\n{msg}"}})
        print(f"[飞书] {r[:200]}"); sent += 1
    if bark:
        u = bark.rstrip("/") + "/" + urllib.parse.quote(title, safe="") + "/" + urllib.parse.quote(msg, safe="")
        req = urllib.request.Request(u, headers={"User-Agent": "zq-push"})
        with urllib.request.urlopen(req, timeout=30) as rr:
            print(f"[Bark] {rr.read().decode(errors='ignore')[:200]}")
        sent += 1
    if tg_tok and tg_chat:
        r = post_json(f"https://api.telegram.org/bot{tg_tok}/sendMessage",
                      {"chat_id": tg_chat, "text": f"{title}\n\n{msg}"})
        print(f"[Telegram] {r[:200]}"); sent += 1

    if not sent:
        print("[push] 未配置通道，仅打印日志")
        print(msg)


if __name__ == "__main__":
    main()
