# 法律 AI 研究包基线凭证

日期：`2026-03-20`

目的：为 `research/` 下的 `legal-ai-research-package-2026-03-20-v1` 建立首个 git-tracked delivery baseline，使后续 dated tracker / memo / matrix 更新可以回溯到一个固定的、可复核的交付起点。

## 1. 基线身份

- package id：`legal-ai-research-package-2026-03-20-v1`
- canonical version：`v1.0`
- snapshot date：`2026-03-20`
- source of truth：`/home/v-boxiuli/PPT/ArgusBot/research`
- baseline tag target：`legal-ai-research-package-2026-03-20-v1.0-baseline`
- repository branch at lock time：`ppt-feature`
- parent repo commit before baseline lock：`121c29d`
- baseline evidence carrier：`git commit + git tag + 本凭证文件`

## 2. 锁定时点说明

- 下表覆盖的是纳入版本控制时锁定的 `16` 份核心研究文档；连同本凭证文件在内，当前 baseline inventory 为 `17` 份 Markdown 文档。
- 本凭证文件本身不做自哈希；它的完整性由承载它的 git baseline commit 和 baseline tag 提供。
- `wc -l research/*.md` 在 baseline lock 后记录为 `17` 份 Markdown、`4263` 总行数。
- unresolved-marker 扫描在锁定前无命中。

## 3. 文件清单与 SHA-256

| 文件 | 行数 | SHA-256 |
| --- | ---: | --- |
| `research/README.md` | `98` | `02eeb1bf1c13e2fc9164c52b772abcf3d10da79bcafd9be8f70d444354c0d9a9` |
| `research/china-contract-compliance-copilot-execution-tracker-2026-03-20.md` | `309` | `4c51f4e1fe438074fbf4c4d110e7c6f6a6018a4b73fb41784d089b1e7eab6349` |
| `research/china-contract-compliance-copilot-management-brief-2026-03-20.md` | `132` | `3373aa12ae5921132c75c45c7db313010987d64bce9c0cd194002abd39028ff5` |
| `research/china-contract-compliance-copilot-management-memo-2026-03-20.md` | `190` | `a28cc39f53c13c61ee8e01fcf104187e7d91b2ddaa64ce3d5f3dfc813924a763` |
| `research/china-contract-compliance-copilot-ops-checklist-2026-03-20.md` | `136` | `7ee68ce1217998baed3a8995a136b5c4fa3029576815a447e0b60c84723c7345` |
| `research/china-contract-compliance-copilot-validation-plan-2026-03-20.md` | `343` | `60570b1fb0e2c10038a3f352898fb5d3e3a1dabf862fb4a15f0e15a128b202f7` |
| `research/china-legal-ai-go-no-go-memo-2026-03-20.md` | `435` | `c27881f5ac59ea88b27a19ad6a37bb93fd2cd3c512e7b9435cc1d6ab7551bb21` |
| `research/court-facing-ai-rules-sanction-risk-tracker-2026-03-20.md` | `431` | `1382dbef46eed1fe9e13863489bf2869658ea24d8863d93ccc48ae12d1a76128` |
| `research/hong-kong-legal-ai-go-no-go-memo-2026-03-20.md` | `331` | `71f0f259197e5a9a3774c8b4a514cf16f1c8d5612a908f3c1d0785d970c4ec24` |
| `research/hong-kong-legal-ai-management-brief-2026-03-20.md` | `148` | `99a4dfc98e79186e97768b090d0b9f967f4fd57ac8b663340c16915d03f1cf92` |
| `research/legal-ai-opportunity-risk-matrix-2026-03-20.md` | `211` | `a22d76aa27306afa3a993c23ce9d73553fcf67cfbc62f58d4b87dc998ff128b9` |
| `research/legal-ai-regulatory-monitoring-tracker-2026-03-20.md` | `429` | `b4cfc796cf0efb987ed21c29dcefd3e8fd58584de37def34765ff7c585ad8c05` |
| `research/legal-ai-research-package-register-2026-03-20.md` | `136` | `61705437deed619a9d14e0789f1c28d8ea37f76959de4aacb0252525449b5cad` |
| `research/legal-llm-law-intersections-2026-03-20.md` | `246` | `e2f9599b99c1d124e68a071e1477f2a474e1f8a7a474eb425d25bb6f57889125` |
| `research/singapore-legal-ai-go-no-go-memo-2026-03-20.md` | `296` | `ddded14d34a38a32505e3f3d5bfdd393548ecb45a42c15da2765be4c78d54e75` |
| `research/uk-australia-uae-legal-ai-market-comparison-2026-03-20.md` | `336` | `aca590867c6f4e16993b122ab44d0eef2d648f90b12cf26cd62ed9704736b6e3` |

## 4. 复核命令

下面这些命令可以在后续审计时复核这份基线凭证：

```bash
find research -maxdepth 1 -name '*.md' ! -name 'legal-ai-research-package-baseline-receipt-2026-03-20.md' -print0 | sort -z | xargs -0 sha256sum
find research -maxdepth 1 -name '*.md' ! -name 'legal-ai-research-package-baseline-receipt-2026-03-20.md' -print0 | sort -z | xargs -0 wc -l
rg -n '<marker-regex>' research/*.md
git tag -l 'legal-ai-research-package-2026-03-20-v1.0-baseline'
git show --stat 'legal-ai-research-package-2026-03-20-v1.0-baseline'
```
