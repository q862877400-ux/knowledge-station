# ANOM-002 · gov 渠道 TLS 指纹拦截 DCP

## 现象
openstd.samr.gov.cn / std.samr.gov.cn / flk.npc.gov.cn 三站点：httpx 直连与经 Clash 代理均
`SSL: UNEXPECTED_EOF_WHILE_READING`（握手期被服务端切断）；www.gov.cn 双路 200 正常。
浏览器可正常访问三站点 ⇒ 非 IP 封锁/断网，是 **TLS 指纹(JA3)级 WAF 过滤**。

## 影响
official_gb / laws_db 两渠道完全不可用；govcn 渠道（www.gov.cn）可用。
⇒ 当前真实巡检只能走公告检索兜底，主通道失效。

## 复现
```python
httpx.Client(timeout=12).get("https://openstd.samr.gov.cn/bzgk/gb/")  # -> SSL UNEXPECTED_EOF
```
矩阵证据：var/tmp/probe_gov_channels.txt（直连/代理 × 四站点）

## 修复方案（canonical owner = channels/base.py 默认 transport）
1. 引入 `curl_cffi`（impersonate chrome），默认 transport 优先用之；未安装时回退 httpx 并打 WARN
2. pyproject 增加依赖声明
3. 测试保持 mock 表驱动不变；新增可选联网用例默认 skip（RUN_LIVE=1 才跑）

[DCP_VALID]：端点载荷✓ 期望实际✓ 版本指纹✓ 日志窗口✓
