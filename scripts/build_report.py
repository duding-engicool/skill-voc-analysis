#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VOC 顾客声音分析报告生成器：读取结构化 JSON，输出 Markdown + 精美网页版 HTML。"""
import argparse
import json
import sys
from collections import defaultdict

PRIO_RANK = {"高": 0, "中": 1, "低": 2}


def build_md(data):
    prod = data.get("product", "未命名对象")
    purpose = data.get("purpose", "")
    strat = data.get("strategy_text", "")
    fbs = data.get("feedbacks", [])
    lines = []
    lines.append("# VOC 顾客声音分析报告\n")
    lines.append(f"**分析对象**：{prod}")
    if purpose:
        lines.append(f"**分析目的**：{purpose}")
    if strat:
        lines.append(f"**关联战略/重点**：{strat}")
    else:
        lines.append("**关联战略/重点**：（未提供，优先级标注「待提供战略后复核」）")
    lines.append("")
    # 维度分布
    dim = defaultdict(lambda: {"count": 0, "neg": 0, "neu": 0, "pos": 0})
    for f in fbs:
        d = f.get("dimension", "其他")
        dim[d]["count"] += 1
        s = f.get("sentiment", "中")
        if s == "负":
            dim[d]["neg"] += 1
        elif s == "正":
            dim[d]["pos"] += 1
        else:
            dim[d]["neu"] += 1
    lines.append("## 一、反馈维度分布\n")
    lines.append("| 维度 | 反馈数 | 负面 | 中性 | 正面 |")
    lines.append("|------|--------|------|------|------|")
    for d, v in sorted(dim.items(), key=lambda x: -x[1]["count"]):
        lines.append(f"| {d} | {v['count']} | {v['neg']} | {v['neu']} | {v['pos']} |")
    lines.append("")
    # 反馈清单
    lines.append("## 二、反馈清单与分类\n")
    lines.append("| 反馈原文 | 维度 | 情感 | 频次 | 需求类别 | CTQ | 优先级 |")
    lines.append("|----------|------|------|------|----------|-----|--------|")
    for f in fbs:
        note = " ⚠待确认" if f.get("note") else ""
        lines.append(f"| {f.get('text','')} | {f.get('dimension','')} | {f.get('sentiment','')} | "
                     f"{f.get('freq','')} | {f.get('category','')} | {f.get('ctq','') or '—'} | {f.get('priority','')}{note} |")
    lines.append("")
    # CTQ 树
    lines.append("## 三、CTQ 树（关键质量特性）\n")
    lines.append(f"- {prod}（产品级 CTQ）")
    for d, v in sorted(dim.items(), key=lambda x: -x[1]["count"]):
        lines.append(f"  - 维度：{d}")
        for f in fbs:
            if f.get("dimension") == d and f.get("ctq"):
                lines.append(f"    - CTQ：{f.get('ctq')}（源自：{f.get('text','')}）")
    lines.append("")
    # 优先级
    ranked = sorted(fbs, key=lambda f: (PRIO_RANK.get(f.get("priority", "低"), 9), -int(f.get("freq", 0) or 0)))
    lines.append("## 四、改善优先级\n")
    lines.append("| 优先级 | 反馈 | 维度 | 建议 |")
    lines.append("|--------|------|------|------|")
    for f in ranked:
        note = "（待确认）" if f.get("note") else ""
        lines.append(f"| {f.get('priority','')} | {f.get('text','')} | {f.get('dimension','')} | "
                     f"{'优先改善' if f.get('priority')=='高' else ('维持/观察' if f.get('priority')=='中' else '低优先级')}{note} |")
    lines.append("")
    pending = [f for f in fbs if f.get("note")]
    if pending:
        lines.append("## 五、供参考·待确认项\n")
        for f in pending:
            lines.append(f"- {f.get('text','')}：{f.get('note')}")
        lines.append("")
    return "\n".join(lines)


def build_html(data):
    prod = data.get("product", "未命名对象")
    purpose = data.get("purpose", "")
    strat = data.get("strategy_text", "")
    fbs = data.get("feedbacks", [])
    strat_html = f"<p><b>关联战略/重点：</b>{strat}</p>" if strat else \
        "<p><b>关联战略/重点：</b><span class='warn'>未提供，优先级标注「待提供战略后复核」</span></p>"
    # 维度卡片
    dim = defaultdict(int)
    for f in fbs:
        dim[f.get("dimension", "其他")] += 1
    dim_cards = "".join(f"<div class='dcard'><div class='dname'>{d}</div><div class='dnum'>{n}</div><div class='dlabel'>条反馈</div></div>"
                         for d, n in sorted(dim.items(), key=lambda x: -x[1]))
    # 反馈列表
    rows = []
    for f in fbs:
        color = {"负": "#E74C3C", "正": "#27AE60", "中": "#F39C12"}.get(f.get("sentiment", "中"), "#95A5A6")
        note = "<span class='warn'>⚠ 待确认</span>" if f.get("note") else ""
        rows.append(f"<tr><td>{f.get('text','')}</td><td>{f.get('dimension','')}</td>"
                    f"<td><span class='dot' style='background:{color}'></span>{f.get('sentiment','')}</td>"
                    f"<td>{f.get('freq','')}</td><td>{f.get('ctq','') or '—'}</td>"
                    f"<td>{f.get('priority','')} {note}</td></tr>")
    rows_html = "".join(rows)
    # CTQ 树
    tree = [f"<li>{prod}<ul>"]
    for d in sorted(dim.keys()):
        tree.append(f"<li>维度：{d}<ul>")
        for f in fbs:
            if f.get("dimension") == d and f.get("ctq"):
                tree.append(f"<li>CTQ：{f.get('ctq')} <em>（源自：{f.get('text','')}）</em></li>")
        tree.append("</ul></li>")
    tree.append("</ul></li>")
    tree_html = "".join(tree)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>VOC 顾客声音分析报告 - {prod}</title>
<style>
 *{{box-sizing:border-box;font-family:-apple-system,"Microsoft YaHei",sans-serif;color:#2c3e50;}}
 body{{margin:0;background:#f4f6f8;padding:32px;}}
 .wrap{{max-width:960px;margin:0 auto;background:#fff;border-radius:12px;padding:36px;box-shadow:0 4px 20px rgba(0,0,0,.08);}}
 h1{{color:#1a252f;margin-top:0;}}
 .meta{{color:#7f8c8d;font-size:14px;margin:4px 0;}}
 .warn{{color:#e67e22;}}
 .dcards{{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0;}}
 .dcard{{background:#f8f9fa;border:1px solid #ecf0f1;border-radius:8px;padding:12px 18px;text-align:center;}}
 .dname{{font-size:13px;color:#555;}}
 .dnum{{font-size:24px;font-weight:700;color:#2980B9;}}
 .dlabel{{font-size:11px;color:#aaa;}}
 table{{width:100%;border-collapse:collapse;margin-top:10px;}}
 th,td{{border:1px solid #ecf0f1;padding:8px 10px;font-size:13px;text-align:left;}}
 th{{background:#f8f9fa;}}
 .dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle;}}
 .sec{{margin-top:26px;}}
 ul{{line-height:1.8;}}
 em{{color:#888;font-style:normal;font-size:12px;}}
</style></head><body><div class="wrap">
<h1>VOC 顾客声音分析报告</h1>
<div class="meta">分析对象：{prod}　|　分析目的：{purpose or '—'}</div>
{strat_html}
<div class="sec"><h2>反馈维度分布</h2><div class="dcards">{dim_cards}</div></div>
<div class="sec"><h2>反馈清单与分类</h2>
<table><tr><th>反馈原文</th><th>维度</th><th>情感</th><th>频次</th><th>CTQ</th><th>优先级</th></tr>{rows_html}</table></div>
<div class="sec"><h2>CTQ 树</h2><ul>{tree_html}</ul></div>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--md-out")
    ap.add_argument("--html-out")
    a = ap.parse_args()
    try:
        data = json.load(open(a.input, encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        sys.exit(1)
    md = build_md(data)
    html = build_html(data)
    if a.md_out:
        open(a.md_out, "w", encoding="utf-8").write(md)
    if a.html_out:
        open(a.html_out, "w", encoding="utf-8").write(html)
    if not a.md_out and not a.html_out:
        print(md)
    else:
        print(json.dumps({"status": "success", "md": a.md_out, "html": a.html_out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
