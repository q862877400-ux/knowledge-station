# 安徽·芜湖市 政民互动入口侦察（只读，不落库）
#
# 纪律（GOAL.md §七.6）：**没取到一条明细确认答复正文非空之前，不许写适配器。**
# 本脚本只做：抓首页/栏目页 → 列候选链接 → 抓列表 → 抓一条明细 → 打印答复正文片段。
#
# 用法： python recon/probe-ah-wuhu.py [detail|list|home]

import sys
import re
import requests

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
HEAD = {'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9'}
TIMEOUT = 25

BASE = 'https://www.wuhu.gov.cn'
KEYWORDS = ('信箱', '留言', '咨询', '答复', '信件', '互动', '政民', '12345', '投诉', '建议')


def get(url, **kw):
    r = requests.get(url, headers=HEAD, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    enc = r.apparent_encoding or 'utf-8'
    if (enc or '').lower() in ('gb2312', 'gbk', 'iso-8859-1'):
        r.encoding = 'gb18030'
    else:
        r.encoding = enc
    return r


def dump(url, limit=60):
    r = get(url)
    print(f'\n===== {url}  status={r.status_code} bytes={len(r.text)} =====')
    title = re.search(r'<title>(.*?)</title>', r.text, re.S)
    print('title:', title.group(1).strip() if title else '(none)')
    links = re.findall(r'href="([^"]+)"[^>]*>([^<]{2,60})<', r.text)
    seen, hit = set(), 0
    for href, text in links:
        t = text.strip()
        if href in seen:
            continue
        seen.add(href)
        hit += 1
        print(f'  {hit:3d}. {t}  ->  {href}')
        if hit >= limit:
            break
    for m in re.findall(r'(?:src|href)="([^"]+\.js[^"]*)"', r.text):
        print(f'  [JS] {m}')
    for m in re.findall(r'<form[^>]*>', r.text):
        print(f'  [FORM] {m[:160]}')
    for m in re.findall(r'(ajax|\$\.(?:get|post|getJSON)|fetch\()[^\n]{0,160}', r.text)[:12]:
        print(f'  [XHR?] {m.strip()[:160]}')
    return r


def show_home():
    for path in ('/zmhd/index.html', '/', '/zmhd/'):
        url = BASE + path
        try:
            r = get(url)
        except Exception as e:
            print(f'[SKIP] {url} -> {type(e).__name__}: {e}')
            continue
        print(f'\n===== {url}  status={r.status_code} bytes={len(r.text)} =====')
        title = re.search(r'<title>(.*?)</title>', r.text, re.S)
        print('title:', title.group(1).strip() if title else '(none)')
        links = re.findall(r'href="([^"]+)"[^>]*>([^<]{2,40})<', r.text)
        seen = set()
        hit = 0
        for href, text in links:
            t = text.strip()
            if not any(k in t for k in KEYWORDS):
                continue
            if href in seen:
                continue
            seen.add(href)
            hit += 1
            print(f'  {hit:3d}. {t}  ->  {href}')
            if hit >= 40:
                break
        if hit == 0:
            print('  (无关键词链接；打印前 25 条任意链接)')
            for href, text in links[:25]:
                print(f'       {text.strip()}  ->  {href}')
        # 龙讯站常见：把配置写进 JS
        for m in re.findall(r'(src|href)="([^"]+\.js[^"]*)"', r.text):
            if 'config' in m[1].lower() or 'zmhd' in m[1].lower() or 'mail' in m[1].lower():
                print(f'  [JS?] {m[1]}')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        show_home()
    elif args[0] == 'url':
        dump(args[1])
    elif args[0] == 'text':
        r = get(args[1])
        try:
            from html import unescape
            body = re.sub(r'(?is)<(script|style).*?</\1>', ' ', r.text)
            body = re.sub(r'<[^>]+>', '\n', body)
            body = unescape(body)
            lines = [ln.strip() for ln in body.split('\n') if ln.strip()]
            print('\n'.join(lines[:200]))
        except Exception as e:
            print('ERR', e)
    else:
        show_home()
