# -*- coding: utf-8 -*-
"""测试 Moonshot/Kimi 视觉：对比 orig_pN(原图) vs prev_pN(预览)，检测差异(图缺失/符号/表)。
读 MOONSHOT_API_KEY(注册表)，调 moonshot-v1-8k-vision-preview。"""
import base64
import json
import os
import sys
import urllib.request
import winreg

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_key():
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        i = 0
        while True:
            try:
                n, v, _ = winreg.EnumValue(k, i)
                i += 1
                if n == "MOONSHOT_API_KEY":
                    return v
            except OSError:
                break
    except Exception:
        pass
    return os.environ.get("MOONSHOT_API_KEY")


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def main():
    key = get_key()
    if not key:
        print("no MOONSHOT_API_KEY")
        return
    orig = sys.argv[1]
    prev = sys.argv[2]
    prompt = ("对比两张图：left_orig=原始PDF页面转图；right=右侧文本重建预览。"
              "找出重建预览相对原图丢失/错位的内容（尤其：图/表格/公式/上下标/符号(如 C带帽 Ĉ、C带上划线 C̄、±、C下标)；字符丢失；错行）。"
              "输出 JSON：{\"differences\":[{\"type\":\"missing|wrong|ok\",\"what\":\"...\"}],\"summary\":\"...\"}，若无差异 summary='ok'")
    payload = {
        "model": "moonshot-v1-8k-vision-preview",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64(orig)}},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64(prev)}},
            {"type": "text", "text": prompt},
        ]}],
        "temperature": 0.0, "max_tokens": 800,
    }
    req = urllib.request.Request("https://api.moonshot.cn/v1/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode())
            print(data["choices"][0]["message"]["content"])
    except Exception as e:
        print("Moonshot vision error:", e)


if __name__ == "__main__":
    main()
