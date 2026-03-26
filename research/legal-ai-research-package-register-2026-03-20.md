# 法律 AI 研究包登记表

日期：2026-03-20

目的：把当前 `research/` 下已完成的法律 AI 研究包登记为**仓库内可审计的运营资产**，明确 source of truth、版本边界、owner-of-record、监测回写路径和首轮落账记录，避免研究包只停留在“已写完”而没有后续运营留痕。

适用范围：

- `research/README.md`
- `research/legal-llm-law-intersections-2026-03-20.md`
- `research/legal-ai-opportunity-risk-matrix-2026-03-20.md`
- `research/legal-ai-regulatory-monitoring-tracker-2026-03-20.md`
- `research/court-facing-ai-rules-sanction-risk-tracker-2026-03-20.md`
- `research/china-legal-ai-go-no-go-memo-2026-03-20.md`
- `research/china-contract-compliance-copilot-management-memo-2026-03-20.md`
- `research/china-contract-compliance-copilot-management-brief-2026-03-20.md`
- `research/china-contract-compliance-copilot-ops-checklist-2026-03-20.md`
- `research/china-contract-compliance-copilot-execution-tracker-2026-03-20.md`
- `research/china-contract-compliance-copilot-validation-plan-2026-03-20.md`
- `research/singapore-legal-ai-go-no-go-memo-2026-03-20.md`
- `research/hong-kong-legal-ai-go-no-go-memo-2026-03-20.md`
- `research/hong-kong-legal-ai-management-brief-2026-03-20.md`
- `research/uk-australia-uae-legal-ai-market-comparison-2026-03-20.md`

这不是法律意见，而是 `2026-03-20` 的研究资产登记文档。

## 1. 包 ID 与 source of truth

- package id：`legal-ai-research-package-2026-03-20-v1`
- canonical package role：`current legal-AI research main package`
- canonical version：`v1.0`
- source of truth：`/home/v-boxiuli/PPT/ArgusBot/research`
- repository entrypoint：`/home/v-boxiuli/PPT/ArgusBot/research/README.md`
- 当前状态：`Active baseline`
- 版本控制状态：`git-tracked delivery baseline`
- baseline tag：`legal-ai-research-package-2026-03-20-v1.0-baseline`
- baseline receipt：`/home/v-boxiuli/PPT/ArgusBot/research/legal-ai-research-package-baseline-receipt-2026-03-20.md`
- 载体形式：repository-side Markdown knowledge base
- 时间边界：本登记表对应 `2026-03-20` 的研究快照；后续变化必须以 dated tracker 记录为准

## 2. 已登记的交付范围

按本次登记时点，这个研究包包含下面四层内容：

- 总览层：法律 LLM / AI 与法律交叉的主结论与后续研究路线
- 优先级层：机会 / 风险矩阵、法域进入顺序、go / no-go 判断
- 法域层：中国、新加坡、香港、英格兰及威尔士 / 澳大利亚 / 阿联酋等 memo 与管理 brief
- 运营层：监管监测 tracker、court-facing sanctions tracker、中国合同 / 合规 copilot 的管理、执行与验证材料

## 3. Owner-of-record 分配

当前上下文未提供具体人员姓名，因此本研究包先按**角色 owner** 登记；后续如有实际姓名，应在不改角色分工逻辑的前提下补到本表或对应 tracker。

| 范围 | primary owner of record | secondary owner | 最低留痕要求 |
| --- | --- | --- | --- |
| 研究包总登记与仓库归档 | `Research owner` | `Product owner` | 每月至少一次回看；任一 `L3` 事件 `48` 小时内补登记 |
| `legal-ai-regulatory-monitoring-tracker` | `Research owner` | `Legal / compliance owner` | 每周至少一次 dated update 或 no-change 记录 |
| `court-facing-ai-rules-sanction-risk-tracker` | `Research owner` | `Legal / compliance owner + Product owner` | 每周 court-facing source sweep；`L2 / L3` 事件必须落账 |
| 中国法域 memo / checklist / brief 回写 | `Legal / compliance owner` | `Research owner` | 命中中国 `L2 / L3` 事件时同步回写 |
| 矩阵与总览结论回写 | `Research owner` | `Product owner + Legal / compliance owner` | 只有当 go / no-go、优先级或统一边界变化时才更新 |

## 3.1 维护节奏基线

为避免“知道谁负责，但不知道什么时候必须落账”，本研究包按下面节奏运行：

| 资产 / 动作 | owner of record | 默认节奏 | 硬触发条件 | 默认落账位置 |
| --- | --- | --- | --- | --- |
| 研究包 register 回看与 change-log 同步 | `Research owner` | 每月一次 | 任一 `L3` 事件 `48` 小时内；任一 owner / cadence / versioning / change-log 规则变化同日补记 | 本文件 section `5` |
| `research/README.md` canonical package 状态回看 | `Research owner` | 每月一次 | package id、canonical role、canonical version 或维护规则发生变化时同日改写 | `research/README.md` + 本文件 |
| `legal-ai-regulatory-monitoring-tracker` 周度 sweep | `Research owner` | 每周至少一次 | 任一中国或跨法域监管 / 标识 / 备案 / 行业专项官方变化 | `legal-ai-regulatory-monitoring-tracker` section `11` / `12`；如命中本表规则变更或 `L2 / L3`，同步本文件 |
| `court-facing-ai-rules-sanction-risk-tracker` 周度 sweep | `Research owner` | 每周至少一次 | 任一 filing / disclosure / evidence / sanction 相关 court-facing 官方变化 | `court-facing-ai-rules-sanction-risk-tracker` section `15` / `17`；如命中本表规则变更或 `L2 / L3`，同步本文件 |
| memo / matrix / synthesis 边界复看 | `Research owner + Legal / compliance owner + Product owner` | 每月一次边界判断 | 任一变化影响 go / no-go、court-facing filing 边界、最低 safeguard 或法域优先级 | 受影响的 memo / matrix / synthesis + 本文件 |

## 4. 版本规则

- `v1.0`：基线登记版本，对应 `2026-03-20` 完整研究包
- `v1.x`：不改变总包边界的增量更新，例如 `L1` 记录、`L2` 分析补充、owner 调整、source list 补强
- `v2.0`：改变了 go / no-go、产品边界、court-facing 规则判断、首批法域排序或中国场景统一边界
- 任何 `L2 / L3` 事件，至少要在相关 tracker 里留下：日期、来源、变化类型、影响判断、owner、截止时间
- 任何 `L3` 事件，除更新相关 tracker 外，还必须同步回写本登记表

## 4.1 Change-log 规则

- `L1 no-change` 周度 sweep：至少落账到对应 tracker；如果没有改变 package metadata、owner、cadence、versioning 或模板规则，可以不单独新增 register 行。
- `L1` 级别的包治理 / 模板 / owner / cadence / source-access 留痕规则补强：同日新增 register 行，因为这类变化会改变后续执行方式。
- `L2` 事件：同日落账到对应 tracker；如果它改变了默认 checkpoint、判断标准、回写路径或维护规则，也要同日补到本文件 section `5`。
- `L3` 事件或任何版本升级：必须在同一次更新中同步改 tracker、`research/README.md`、本文件，以及所有受影响的 memo / matrix / synthesis。
- section `5` 的每一条 change-log 最低要写清：日期、变化类型、记录内容、owner、证据；如果同时改变 version boundary、inventory 或 canonical role，也要在记录内容或证据中明确写出。

## 5. 基线落账记录

| 日期 | 类型 | 记录内容 | owner | 证据 |
| --- | --- | --- | --- | --- |
| `2026-03-20` | knowledge-base entrypoint | 在 `research/` 下建立 package index，把主综述、矩阵、register、tracker 和中国执行层材料整理成正式仓库入口 | `Research owner` | `research/README.md` + 本文件 |
| `2026-03-20` | canonical main-package designation | 将该研究包明确标记为当前 legal-AI 研究主包，并把 canonical role / version 写入 README 与 register，避免后续并行 memo 被误当成主包 | `Research owner` | `research/README.md` + 本文件 |
| `2026-03-20` | baseline registration | 将已完成的 `research/` 研究包登记为 repo-side operating asset；明确 tracker owner-of-record；要求后续变化先回写 tracker，再决定是否改 memo / matrix / 总览 | `Research owner` | 本文件 + `legal-ai-regulatory-monitoring-tracker` + `court-facing-ai-rules-sanction-risk-tracker` |
| `2026-03-20` | first dated monitoring update | 中国治理 / 标识 / 备案 / 行业专项与 court-facing 基线刷源已落账到总 tracker；court-facing 风险基线已落账到专项 tracker | `Research owner + Legal / compliance owner` | `legal-ai-regulatory-monitoring-tracker` section 11 + `court-facing-ai-rules-sanction-risk-tracker` section 15 |
| `2026-03-20` | audit-trail hardening | 为仓库入口补充 `Audit Trail` 导航；将中国重点源清单与首个 dated update 的最小官方锚点对齐，并要求后续中国 `L1 / L2 / L3` 更新至少回链到 `section 11.1` 或新增同级别官方源 | `Research owner` | `research/README.md` + `legal-ai-regulatory-monitoring-tracker` section 3 + section 11.1 |
| `2026-03-20` | China anchor-role split hardening | 将中国监测中的 `备案 / 登记` 锚点与 `标识执法` 锚点明确拆分：`2026-01-09` `CAC` 公告作为备案 / 登记锚点，`2025-11-25` `CAC` 通报作为标识执法锚点，并同步写入 dated update 与下次 sweep 的最低留痕包 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 3 + section 11 + section 11.1 + section 12.1 |
| `2026-03-20` | China meaningful-change rubric hardening | 为中国周度 sweep 增加明确的 meaningful-change 判定规则，要求后续标识、备案 / 登记、行业专项和法院 / 公共法律服务变化都先按 `section 12.2` 判断是否真的触发 `L2 / L3` 或文档回写，而不是只按“有新材料”升级 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 12.1 + section 12.2 |
| `2026-03-20` | README monitoring-rule surfacing | 将中国周度 sweep 的 `section 12.1 / 12.2` 规则显式挂到仓库入口，避免操作方从 `README` 进入时遗漏“先分 no-change 与 meaningful change，再决定是否改 memo / matrix”的维护顺序 | `Research owner` | `research/README.md` + `legal-ai-regulatory-monitoring-tracker` section 12.1 + section 12.2 |
| `2026-03-20` | China sweep output-template hardening | 为中国周度 sweep 增加统一输出模板，并同步把 `README` 的操作规则升级到 `section 12.1 / 12.2 / 12.3`，避免不同执行人留下的 dated update 颗粒度不一致 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 12.3 + `research/README.md` |
| `2026-03-20` | README court-facing checkpoint surfacing | 将 `2026-03-25` 的英格兰及威尔士 `CJC` court-facing `L2` 影响分析节点和 court-facing sweep 的默认入口规则显式挂到 `README`，避免最近的 court-facing 截止日期只留在专项 tracker 内部 | `Research owner` | `research/README.md` + `court-facing-ai-rules-sanction-risk-tracker` section 17 |
| `2026-03-20` | court-facing sweep hardening | 为 court-facing 周度 sweep 增加最低留痕包、meaningful-change 判定规则和统一输出模板，并同步把 `README` 的默认操作路径升级到 `section 17 / 17.1 / 17.2 / 17.3` | `Research owner` | `court-facing-ai-rules-sanction-risk-tracker` section 17.1 + section 17.2 + section 17.3 + `research/README.md` |
| `2026-03-20` | README China second-wave checkpoint surfacing | 将监管 tracker 里已排队的 `2026-04-03` 中国行业专项规则与 court-facing / public-legal-service 规则复核节点显式挂到 `README`，避免第二波中国检查点只留在专项 tracker 内部 | `Research owner` | `research/README.md` + `legal-ai-regulatory-monitoring-tracker` section 12 |
| `2026-03-20` | first-sweep evidence-pack backfill | 补齐中国与 court-facing 首轮 `2026-03-20` sweep 的逐锚点 `no-change / change` 判断，使首轮基线记录本身也满足 `section 12.1 / 12.3` 与 `section 17.1 / 17.3` 的最低留痕格式要求，避免“后续周更规则更严格、首轮基线却只有摘要”的审计断层 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 11.2 + `court-facing-ai-rules-sanction-risk-tracker` section 15.1 |
| `2026-03-20` | China anthropomorphic-interaction anchor hardening | 将 `2025-12-27` `CAC` 《人工智能拟人化互动服务管理暂行办法（征求意见稿）》补入中国监测源、dated update、逐锚点 evidence pack 与开放队列，并把该节点显式挂到 `README`；原因是其已出现面向拟人化互动服务的单独治理框架，并明确卫生健康、金融、法律等专业领域服务需同时符合主管部门规定 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 3 + section 11 + section 11.1 + section 11.2 + section 12 + `research/README.md` |
| `2026-03-20` | China legal-sector follow-on source hardening | 将 `司法部律师工作条线`、`司法部公共法律服务条线`、`12348` 与 `中华全国律师协会` 明确补入中国监测源、`2026-03-27` 开放队列和 evidence-pack / meaningful-change 规则，使 `CAC` 专业领域条款落到法律服务场景时有清晰的主管部门 follow-on 刷源路径，而不是只盯 `CAC` 本身 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 3 + section 12 + section 12.1 + section 12.2 + section 12.3 + `research/README.md` |
| `2026-03-20` | China source-availability logging hardening | 为中国周度 sweep 增加 `source unavailable / fallback official page used` 规则；原因是本轮对 `司法部` 两个法律服务栏目根路径的直接抓取都出现自循环重定向，而 `12348` 与 `中华全国律师协会` 仍可直接访问，后续必须把“源不可达”与“无变化”区分记录 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 12 + `research/README.md` |
| `2026-03-20` | China `MOJ` fallback-path mapping hardening | 将 `司法部律师工作条线` 与 `司法部公共法律服务条线` 的默认 fallback official page 路径进一步具体化为同域 `pub/sfbgw/...` article-page family，并要求后续 dated sweep 同时记录栏目根路径与实际使用的 fallback 页面，避免 `source unavailable` 规则仍然过于抽象 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 3 + section 12.1 + section 12.3 + `research/README.md` |
| `2026-03-20` | China `MOJ` automation-failure escalation hardening | 将 `MOJ` fallback order 继续细化为 `栏目根路径 -> pub/sfbgw/... -> pub/sfbgwapp/... -> manual browser verification`，并要求后续 dated sweep 在自动抓取连续失败时明确记为 `source unavailable (automation)`，避免把抓取环境问题误当成法规无变化 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 3 + section 12.1 + section 12.2 + section 12.3 + `research/README.md` |
| `2026-03-20` | China source-access column hardening | 将中国周度 sweep 的标准输出模板补齐 `source access / fallback used` 专门列，使 `MOJ` 的 `direct / redirected / timeout / source unavailable / source unavailable (automation)` 与具体 fallback page 能直接落在 dated event 表格里，而不是只留在文字说明里 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 12.3 + `research/README.md` |
| `2026-03-20` | first-sweep source-access baseline backfill | 将首轮 `2026-03-20` 中国逐锚点表格补齐 `source access / fallback used` 列，使首轮 dated baseline 与 section `12.3` 的当前输出模板对齐，避免“后续周更有该字段、首轮基线却缺列”的审计断层 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 11.2 + `research/README.md` |
| `2026-03-20` | court-facing source-access hardening | 为 court-facing tracker 增加 `source access / fallback used` 列和最小填写规则，并把首轮 `2026-03-20` court-facing 逐锚点表按当前官方访问状态回填为 `direct`、`source unavailable` 或 `source unavailable (automation)`，避免 court-facing 基线仍落后于中国 tracker 的审计颗粒度 | `Research owner` | `court-facing-ai-rules-sanction-risk-tracker` section 15.1 + section 17.1 + section 17.2 + section 17.3 + `research/README.md` |
| `2026-03-20` | dated-summary source-access rollup hardening | 将监管 tracker section `11` 与 court-facing tracker section `15` 的摘要级 dated 表格也补齐 source-access 汇总列，并把中国 court-facing 行的 `court.gov.cn` 自动抓取状态与专项 tracker 对齐为 `source unavailable (automation)`；这样摘要层与逐锚点 evidence pack 不再出现访问状态口径不一致 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section 11 + section 11.2 + `court-facing-ai-rules-sanction-risk-tracker` section 15 + section 15.1 + `research/README.md` |
| `2026-03-20` | package-governance rule hardening | 将 owner、maintenance cadence、versioning 与 change-log 规则进一步显式化：新增 section `3.1` 和 section `4.1`，把 register / README / tracker / memo 的默认节奏、何时必须进 register，以及何时需要同次更新完成 version-boundary 同步写清，避免后续维护仍靠隐含约定 | `Research owner` | 本文件 section `3.1` + section `4.1` + `research/README.md` |
| `2026-03-20` | England-and-Wales `CJC` `L2` impact-analysis backwrite | 提前完成原排队到 `2026-03-25` 的 `CJC` court-facing `L2` 影响分析；结论是当前 consultation 已足以上调英格兰及威尔士 evidence / disclosure 风险描述的精度，但仍不足以改写统一 `NO-GO / no auto-file / no court-ready final output` 边界，因此回写 court-facing tracker、总监管 tracker、`uk-australia-uae` memo，并关闭 README / tracker 中过期的 `2026-03-25` 开放动作 | `Research owner + Legal / compliance owner` | `court-facing-ai-rules-sanction-risk-tracker` section `15.2` + `legal-ai-regulatory-monitoring-tracker` section `6.1` + `uk-australia-uae-legal-ai-market-comparison` section `3.1.1` + `research/README.md` |
| `2026-03-20` | China legal-sector signal-only filter hardening | 将中国拟人化互动 / 专业领域附加义务的 meaningful-change 规则进一步细化：如果 `MOJ`、`12348` 或 `中华全国律师协会` 官方域名下出现的 AI 相关材料只是地方实践报道、业务进阶文章、行业动态或项目宣传，而不是全国性正式规则 / 指引 / 纪律规范，默认按 `L1 no-change` 的 signal-only 处理，不单独据此改写统一边界；同时把这一执行规则挂到 `README`，并补到中国周度标准输出模板的最低填写要求里 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section `12.2` + section `12.3` + `research/README.md` |
| `2026-03-20` | England-and-Wales `CJC` status-only recheck rule hardening | 基于同日对 `CJC current-work`、`latest-news` 与 consultation / interim material 的 live recheck，补充一条执行规则：在 `2026-04-14 23:59` closing-time 之前，如果官方材料只是继续确认 consultation 仍 open 且 evidence-stage proposal 没有实质推进，默认只记为 tracker-level `L1 no-change` status verification，不重复开启新的 `L2` 分析或 memo 回写；只有 official material、closing-time、final output 或 evidence-stage judgement 实质变化时才重新升级 | `Research owner` | `court-facing-ai-rules-sanction-risk-tracker` section `17.2` + `legal-ai-regulatory-monitoring-tracker` section `6.1` + `research/README.md` |
| `2026-03-20` | England-and-Wales `CJC` live source-path refresh | 将包内仍指向旧 `/2026/02/` interim-report PDF 的英格兰及威尔士 `CJC` 源清单，统一刷新为当前 official current-work page 暴露的 `/2026/03/` consultation PDF 路径；这次更新只修正 source anchor，不改变既有 `L2` 结论或统一边界 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` source list + `court-facing-ai-rules-sanction-risk-tracker` source list + `uk-australia-uae-legal-ai-market-comparison` source list |
| `2026-03-20` | England-and-Wales `CJC` no-change verification backwrite | 将同日 live recheck 的 no-change 结论回写到英格兰及威尔士 `CJC` 的三处分析文本：official materials 仍确认 consultation open through `2026-04-14 23:59`，而 `/2026/03/` PDF path refresh 只属于 source-anchor 更新，不改变既有 `L2` judgement、`P0` 排序或统一 `NO-GO` 边界 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section `6.1` + `court-facing-ai-rules-sanction-risk-tracker` section `15.2` + `uk-australia-uae-legal-ai-market-comparison` section `3.1.1` |
| `2026-03-20` | China legal-sector signal-only example-anchor hardening | 将中国拟人化互动 / 专业领域附加义务的 dated baseline 补上同日 official-domain example page anchors，使 `MOJ` / `中华全国律师协会` 的 `signal-only / L1 no-change` 判断不只停留在抽象口径；同时把“如按 official-domain article 判为 signal-only，至少记录一条具体页名或路径”的要求写入中国 tracker 模板与 `README`，减少后续审计争议 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section `11` + section `11.1` + section `11.2` + section `12.3` + `research/README.md` |
| `2026-03-20` | China `ACLA` signal-only example refresh | 将中国 dated baseline 中的 `中华全国律师协会` `signal-only` example anchor 从泛合规文章刷新为更直接的 AI/律师业务 `业务进阶` 页面，以便 future sweep 在说明“official-domain article != national formal guidance”时使用更贴近主题的 same-day example，而不改变既有 `L1 no-change` / `signal-only` 判断 | `Research owner` | `legal-ai-regulatory-monitoring-tracker` section `11.1` + section `11.2` |
| `2026-03-20` | version-control baseline lock | 将 `research/` 下 `2026-03-20` 法律 AI 研究包纳入 git 版本控制；新增 baseline receipt，明确 baseline tag `legal-ai-research-package-2026-03-20-v1.0-baseline`，使后续 dated tracker / memo / matrix 更新可以回溯到固定的 repository baseline | `Research owner` | `research/README.md` + `research/legal-ai-research-package-baseline-receipt-2026-03-20.md` + `git tag -l` / `git show` |
| `2026-03-20` | inventory snapshot | 记录当前 repo-side 研究包指纹：`17` 个 Markdown 文件、`4263` 总行数，且开放工作标记扫描无命中；其中新增 `legal-ai-research-package-baseline-receipt-2026-03-20.md` 作为基线凭证文件 | `Research owner` | `wc -l research/*.md` + unresolved-marker sweep recorded in execution log |

## 6. 最低运行规则

- 每周至少在一个 tracker 中新增一条 dated no-change 或 change event，避免“只建 tracker 不落账”。
- 中国法域发生标识、备案 / 登记、行业专项规则或 court-facing 规则变化时，优先更新总 tracker，再决定是否回写中国 memo 家族。
- court-facing 相关 `L2 / L3` 事件，必须同时考虑是否回写 `legal-ai-opportunity-risk-matrix` 和法域比较 memo。
- 每月底至少做一次“总包是否仍保持 `v1.x`”判断；如果结论边界发生变化，就升级主版本而不是只补零散说明。
- 如需把其他 dated 包替换为新的 canonical main package，必须在同一次更新中同时改：
  - `research/README.md` 的 canonical role / version
  - 本登记表的 canonical package role / version
  - 本登记表新增一条 dated 变更落账记录
