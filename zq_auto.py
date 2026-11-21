# -*- coding: utf-8 -*-
"""竞彩让球体检 · 云端零依赖版
核心算法与本地 portable/zq_auto.py 完全一致（同一套内嵌校准表、同一套去水与插值），
只增加了 --msg 输出（给手机推送用的纯文本）与按期号分组。

用法:
  python zq_auto.py                 出表
  python zq_auto.py --drift         与 zq_last.json 对比漂移
  python zq_auto.py --msg out.txt   同时把推送文本写入 out.txt
"""
import urllib.request, ssl, json, sys, os, itertools
import numpy as np

API = ("https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry"
       "?poolCode=hhad,had,ttg,crs,hafu&channel=c")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zq_last.json")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------- 内嵌校准表（隐含概率 -> 主队赢2+/恰赢1、客队赢2+/恰赢1） ----------
BINS = [0.215, 0.245, 0.275, 0.305, 0.335, 0.365, 0.395, 0.425, 0.455, 0.485, 0.515,
        0.545, 0.575, 0.605, 0.635, 0.665, 0.695, 0.725, 0.755, 0.785, 0.815, 0.845, 0.875]
BIG_H = [0.06508, 0.07975, 0.0806, 0.11077, 0.12778, 0.14735, 0.17684, 0.19889, 0.21105,
         0.23237, 0.25761, 0.29477, 0.33103, 0.35383, 0.38608, 0.45992, 0.46088, 0.49449,
         0.52778, 0.5724, 0.62461, 0.68, 0.7767]
ONE_H = [0.14979, 0.14855, 0.16478, 0.17749, 0.19774, 0.20231, 0.21441, 0.23141, 0.24674,
         0.24639, 0.24869, 0.28244, 0.26414, 0.28666, 0.2616, 0.2523, 0.2845, 0.2739,
         0.25214, 0.25113, 0.21136, 0.216, 0.1165]
BIG_A = [0.06561, 0.07666, 0.09708, 0.11444, 0.13321, 0.15207, 0.18932, 0.22042, 0.22527,
         0.2533, 0.26833, 0.30635, 0.32765, 0.37978, 0.33811, 0.42941, 0.49627, 0.49174,
         0.54438, 0.56364, 0.56364, 0.56364, 0.56364]
ONE_A = [0.12618, 0.15762, 0.16094, 0.1836, 0.19328, 0.20881, 0.23374, 0.23927, 0.24117,
         0.2511, 0.2346, 0.26508, 0.26515, 0.30562, 0.30946, 0.26765, 0.26493, 0.27273,
         0.27811, 0.25455, 0.25455, 0.25455, 0.25455]
BIAS = [(0.00, -0.040), (0.20, -0.020), (0.30, -0.001), (0.40, +0.012),
        (0.50, +0.003), (0.60, +0.044), (0.70, +0.043), (0.80, +0.044), (0.90, +0.044)]
PICK = ["让胜", "让平", "让负"]
MIN_ODDS = 1.70


def bias(p):
    for i in range(len(BIAS) - 1):
        if BIAS[i][0] <= p < BIAS[i + 1][0]:
            return BIAS[i][1]
    return 0.0


def correct(p):
    p = np.array(p, float); f = int(np.argmax(p)); pf = p[f]
    pf2 = min(max(pf + bias(pf), 0.03), 0.97)
    sc = (1 - pf2) / (1 - pf) if pf < 1 else 0
    for i in range(3):
        if i != f:
            p[i] *= sc
    p[f] = pf2
    return p


def emp(p, side):
    xs = np.array(BINS)
    big = np.interp(p, xs, np.array(BIG_H if side == "h" else BIG_A))
    one = np.interp(p, xs, np.array(ONE_H if side == "h" else ONE_A))
    return float(big), float(one)


def fetch():
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(API, headers={"User-Agent": UA, "Referer": "https://www.sporttery.cn/"})
    d = json.loads(urllib.request.urlopen(req, timeout=40, context=ctx).read().decode())
    rows = []
    for g in d["value"]["matchInfoList"]:
        for m in g["subMatchList"]:
            had = m.get("had") or {}; hh = m.get("hhad") or {}
            if not had.get("h"):
                continue
            rows.append(dict(num=m.get("matchNumStr"), lg=m.get("leagueAbbName"),
                             time=m.get("matchTime"), home=m.get("homeTeamAbbName"),
                             away=m.get("awayTeamAbbName"),
                             o=[float(had["h"]), float(had["d"]), float(had["a"])],
                             upd=f"{had.get('updateDate')} {had.get('updateTime')}",
                             rq=hh.get("goalLine"),
                             oh=[float(hh["h"]), float(hh["d"]), float(hh["a"])] if hh.get("h") else None))
    rows.sort(key=lambda r: (r["num"] or "", r["time"] or ""))
    return rows


def analyze(rows):
    for r in rows:
        inv = np.array([1 / x for x in r["o"]]); r["ret"] = float(1 / inv.sum())
        r["raw"] = inv / inv.sum()
        r["p"] = correct(r["raw"])
        r["ev"] = r["p"] * np.array(r["o"]) - 1
        r["ph"] = None; r["evh"] = None
        if not r["oh"] or not r["rq"]:
            continue
        try:
            L = int(r["rq"])
        except Exception:
            continue
        r["rqn"] = L
        if L == -1:
            big, one = emp(r["raw"][0], "h")
            r["ph"] = np.array([big, one, max(0.01, 1 - big - one)])
        elif L == 1:
            big, one = emp(r["raw"][2], "a")
            r["ph"] = np.array([max(0.01, 1 - big - one), one, big])
        else:
            continue
        r["evh"] = r["ph"] * np.array(r["oh"]) - 1
    return rows


def build_message(rows, drift_lines):
    g = {}
    for r in rows:
        g.setdefault((r["num"] or "")[:2], []).append(r)
    order = ["周六", "周日", "周一", "周二", "周三", "周四", "周五"]
    keys = [k for k in order if k in g] + [k for k in g if k not in order]

    legs = []
    for r in rows:
        if r["ph"] is None:
            continue
        for i in range(3):
            if r["oh"][i] >= MIN_ODDS:
                legs.append(dict(num=r["num"], pick=PICK[i],
                                 odds=float(r["oh"][i]),
                                 p=float(r["ph"][i]),
                                 q=float(r["ph"][i]) * float(r["oh"][i])))

    L = []
    upd = rows[0]["upd"] if rows else "?"
    L.append(f"【竞彩让球体检】盘口更新 {upd} | 共{len(rows)}场")
    if drift_lines:
        L.append("")
        L.append(f"★变盘 {len(drift_lines)} 条")
        L.extend("  " + x for x in drift_lines)

    L.append("")
    L.append("== 正期望腿（≥1.70）==")
    pos = [x for x in legs if x["q"] > 1]
    if not pos:
        L.append("  今日无正期望腿 —— 建议空仓")
    for x in sorted(pos, key=lambda z: -z["q"])[:10]:
        L.append(f"  {x['num']} {x['pick']} {x['odds']:.2f} 概率{x['p']*100:.0f}% 期望{(x['q']-1)*100:+.1f}%")

    L.append("")
    L.append("== 串关（每腿≥1.70，同一期号批次内）==")
    anydone = False
    for k in keys:
        sub = g[k]
        block = []
        for n in (2, 3, 4):
            res = []
            for combo in itertools.combinations(sub, n):
                pool = []
                for r in combo:
                    o = [x for x in legs if x["num"] == r["num"]]
                    if not o:
                        pool = None; break
                    pool.append(o)
                if not pool:
                    continue
                for ch in itertools.product(*pool):
                    price = float(np.prod([x["odds"] for x in ch]))
                    prob = float(np.prod([x["p"] for x in ch]))
                    res.append((prob * price - 1, price, prob, ch))
            if not res:
                continue
            pos2 = sorted([x for x in res if x[0] > 0], key=lambda z: -z[0])
            if not pos2:
                block.append(f"  {n}串 无正期望组合")
                continue
            ev, price, prob, ch = pos2[0]
            txt = " + ".join(f"{x['num']}{x['pick']}{x['odds']:.2f}" for x in ch)
            block.append(f"  {n}串 {price:.2f}倍 命中{prob*100:.1f}% 期望{ev*100:+.1f}%")
            block.append(f"    {txt}")
        if block:
            anydone = True
            L.append(f"[{k}]")
            L.extend(block)
    if not anydone:
        L.append("  无可用组合")
    L.append("")
    L.append("== 全表（价/概率/期望）==")
    for k in keys:
        L.append(f"[{k}] {len(g[k])}场")
        for r in g[k]:
            if r["ph"] is None:
                L.append(f"  {r['num']} {r['home']}v{r['away']} 无让球盘")
                continue
            L.append(f"  {r['num']} {r['home']}v{r['away']} {r['rqn']:+d} "
                     + "/".join(f"{x:.2f}" for x in r["oh"])
                     + " | " + "/".join(f"{x*100:.0f}" for x in r["ph"])
                     + " | " + "/".join(f"{x*100:+.0f}" for x in r["evh"]))
    L.append("")
    L.append("让平腿对价极敏感，开赛前30分钟务必再跑一次。")
    L.append("注：接口的“更新时间”只跟胜平负走，让球变盘以下方★变盘行为准。")
    return "\n".join(L)


def main():
    rows = analyze(fetch())
    drift = []
    old = {}
    if os.path.exists(CACHE):
        try:
            old = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            old = {}
    if "--drift" in sys.argv and old:
        for r in rows:
            o = old.get(r["num"])
            if not o:
                continue
            note = []
            if o.get("rq") != r["rq"]:
                note.append(f"★让球线{o.get('rq')}->{r['rq']}")
            if o.get("oh") and r["oh"]:
                d1 = [r["oh"][i] - o["oh"][i] for i in range(3)]
                if any(abs(x) > 0.02 for x in d1):
                    note.append("让球价" + "/".join(f"{x:+.2f}" for x in d1))
            if o.get("o") and r["o"]:
                d2 = [r["o"][i] - o["o"][i] for i in range(3)]
                if any(abs(x) > 0.04 for x in d2):
                    note.append("胜平负" + "/".join(f"{x:+.2f}" for x in d2))
            if note:
                drift.append(f"{r['num']} {' '.join(note)}")

    msg = build_message(rows, drift)
    print(msg)

    target = None
    if "--msg" in sys.argv:
        i = sys.argv.index("--msg")
        if i + 1 < len(sys.argv):
            target = sys.argv[i + 1]
    if target:
        with open(target, "w", encoding="utf-8") as f:
            f.write(msg)

    json.dump({r["num"]: dict(o=r["o"], oh=r["oh"], rq=r["rq"]) for r in rows},
              open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"[快照] {CACHE}", file=sys.stderr)


if __name__ == "__main__":
    main()
