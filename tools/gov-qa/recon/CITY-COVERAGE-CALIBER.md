# 地级市覆盖的**口径修正**（2026-10-10 第 7 轮）

> **一句话**：此前报的「262 个地级市缺来源」**是错的**。按数据实测：
> **141 个市有记录 / 193 个市真的零记录**。
> 差的 69 个市**不是没采，是「有数据但没有专属通道」被口径漏计了。**

---

## 1. 怎么发现的（不是推理，是实测）

起点是给「洛阳 / 芜湖 / 宜昌」找 IGI siteId（`recon/probe-igi-cities.py`），
得到候选 `4103000021` / `6787231,6787891` / `54`。

**`recon/probe-igi-context.py` 用实测把它们全部证伪**（GOAL.md #7）：

| 市 | 候选 siteId | IGI 接口实测 | 真实归属 |
|---|---|---|---|
| 洛阳 | `4103000021` | **HTTP 404** | `t.ly.gov.cn/openview`（内容开放 API）—— 而且这个数**恰好是洛阳的行政区划代码 410300** |
| 芜湖 | `6787231` / `6787891` | **HTTP 404** | 龙讯科技 CMS 的 `data-setting` |
| 宜昌 | `54` | **HTTP 404** | `hubei.gov.cn/zxjy/zxft`（省级在线访谈） |

⇒ **「页面里出现 `siteId=`」≠「用 IGI」**。`siteId` 这个词被各种 CMS 滥用。

## 2. 顺手查出一个更大的问题：覆盖口径漏计

`recon/missing-cities.py` 的口径是「**该市有没有一个 `level=city` 的通道**」。
但**省级/平台级通道的记录里带 `extra.city`**：

```
$ grep -l '"city": *"鞍山市"' data/*.jsonl
data/ln-8890-辽宁省·12345民心智慧听（咨询投诉+知识库）.jsonl      ← 省级通道！
```

辽宁 14 个地级市里 **12 个有数据**（鞍山 2,307 / 抚顺 2,189 / 锦州 2,156 …），
全在 `ln-8890`（**辽宁省级** 12345 平台）里 ——
可 `missing-cities.py` 报「辽宁缺 13 个」。

## 3. 修正后的数字（`coverage-report.py --missing-cities`）

| 口径 | 有记录 | 零记录 | 说明 |
|---|---|---|---|
| 旧（只数通道） | 72 | **262** | 把「有数据但无专属通道」的市全算成缺 |
| **新（数据口径）** | **141** | **193** | 归属 = `extra.city`，缺失时回落到市级通道 |

`coverage-report.py --quiet` 现在多一个键：`CITY_DATA_ONLY=85`
（= **没有专属通道、但确实有数据**的市，其中多数来自省级 12345 平台）。

## 4. 实现（`coverage.py` / `coverage-report.py`）

- 新增 `CoverageUnit.data_records` —— 按 `extra.city` 归属的条数
- 新增 `norm_city()` / `known_cities()` / `channel_city_map()` /
  `count_by_city()` / `merge_city_data()`
- `build_units(..., city_counts=...)` —— 把「数据口径的市」**补建**为市级单元
- **状态判定改为 `max(total_records, data_records)`**；
  `total_records` 保持「只算本级通道」的原义 ⇒ **不破坏既有报表**
- `--missing-cities` 输出真正零记录的地级市（按省分组）

### 两个**必须**注意的坑（都已用测试钉住）

1. **占位值必须过滤** —— IGI 的 `CITY` 字段常是 `市辖区` /
   `省直辖县级行政区划`。不过滤会凭空造出「市辖区市」，实测**虚增 ~80 个假单元**。
   ⇒ `count_by_city(only_known=True)` 用 `regions.PROVINCE_CITIES`（334 个）白名单过滤。
2. **补建市级单元不得改省级 `total_incl_cities`** —— 省级通道的记录本身已计入省级
   `total_records`，再加一次会把省总量**翻倍**（辽宁 `ln-8890` 2 万条全带 `extra.city`）。
   ⇒ 测试 `test_merge_does_not_inflate_province_total` 钉住。

## 5. 测试

`tests/test_coverage.py` 新增 8 个（**58 passed**）：

- `test_norm_city` / `test_known_cities_covers_334`
- `test_data_records_drive_city_status`（复现鞍山）
- `test_data_records_thin_when_below_threshold`
- `test_merge_city_data_creates_units_for_data_only_cities`
- `test_merge_does_not_inflate_province_total`（防重复计数）
- `test_count_by_city_filters_placeholder_and_falls_back`
- `test_count_by_city_extra_city_wins_over_channel`

## 6. 对下一步的影响

- **M4 的分母变了**：要做的是 **193 个市**，不是 262 个。
- **优先级也变了**：广东（21）/ 河南（18）/ 安徽（16）/ 云南（16）/ 湖南（14）
  这 5 省占了 85 个 —— **集中打这 5 省收益最大**。
- 反面：**辽宁/四川/贵州/山西/吉林** 的市大量已被省级平台覆盖，
  **不要再去给它们逐市建通道**（重复投入）。

## 7. 已判死（勿重复投入）

- 洛阳 `t.ly.gov.cn` 的 `consultview` / `openview` **返回 HTML 页面，不是 JSON 接口**
- 宜昌 `/Szrx/lists` **返回 HTML 外壳**（数据另走 AJAX，未找到）
- 芜湖 `/c1/wuhu/messageBoardInfoList-wh-01{,.json,.js}` **全部 404**
  （龙讯 CMS 的静态列表文件不在该路径；`/content/article/<id>` 可用但需先有列表）
