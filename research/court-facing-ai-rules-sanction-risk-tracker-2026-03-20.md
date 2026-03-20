# 法院链路 AI 规则与 sanction 风险跟踪表

日期：2026-03-20

目的：补一份**聚焦法院 / 仲裁 / tribunal 提交链路**的专项跟踪文档，专门盯 filing、citation、fact verification、affidavit / witness material、disclosure 和 sanction risk。这份文档不重复一般性监管清单，而是把最容易改变“能不能碰 court-facing workflow”的规则和风险收口成一张表。

适用范围：

- `research/legal-ai-opportunity-risk-matrix-2026-03-20.md`
- `research/legal-ai-regulatory-monitoring-tracker-2026-03-20.md`
- `research/singapore-legal-ai-go-no-go-memo-2026-03-20.md`
- `research/hong-kong-legal-ai-go-no-go-memo-2026-03-20.md`
- `research/hong-kong-legal-ai-management-brief-2026-03-20.md`
- `research/uk-australia-uae-legal-ai-market-comparison-2026-03-20.md`
- `research/china-legal-ai-go-no-go-memo-2026-03-20.md`
- `research/legal-ai-research-package-register-2026-03-20.md`

这不是法律意见，而是 `2026-03-20` 的研究运营快照。

## 1. 结论先行

当前阶段，这个研究包对 **court-facing AI** 的默认结论仍然不变：

- **只允许内部 pre-filing QA、citation check、fact-verification support、filing checklist**
- **不允许 auto-file**
- **不允许把 AI 输出包装成 court-ready final product**
- **不允许把未经强复核的 AI 输出直接写进 affidavits、witness statements、expert reports 或正式提交材料**

如果必须用一句话概括本轮官方材料的共同方向，就是：

- 法院并没有普遍禁止 AI
- 但法院和法官持续强调：**提交责任、人类核验责任、引文真实性和事实真实性仍由提交方承担**
- 一旦把**虚构引文、错误事实、未经核验的 AI 输出**放进 court documents，风险会快速从“产品错误”升级为**costs / wasted costs / strike-out / regulator referral / contempt** 级别的问题

## 2. 为什么单独盯这一层

现有研究包已经把 court-facing workflow 放在最后进入的高风险阶段，但这类风险和一般合规风险不同，原因有三点：

- 它直接碰到**candor to tribunal / duties to court / evidence integrity**
- 它的后果不是普通产品投诉，而可能是**程序制裁、费用制裁、职业纪律或法官直接点名**
- 它的规则并不总是写在同一个地方，而是散落在**court guide、practice direction、judgment、disciplinary referral、judicial guidance** 里

所以需要一份单独 tracker，把“能不能碰 filing、citation、fact verification”单列出来。

## 3. 默认产品红线与最小允许范围

| 项目 | 当前默认结论 |
| --- | --- |
| auto-file / 自动向法院提交 | 不允许 |
| 生成可直接提交的 final pleading / submission | 不允许 |
| 生成 affidavits / witness statements / expert reports 的最终内容 | 不允许 |
| 无来源裸答进入 court documents | 不允许 |
| AI 直接决定 facts / authorities 是否真实 | 不允许 |
| 内部 pre-filing QA | 可以，但必须有人类逐项确认 |
| citation checker | 可以，但必须回链 primary source |
| fact-verification checklist | 可以，但只能作为人工核验辅助 |
| filing checklist / disclosure checklist | 可以，但不能替代律师 / court user 最终责任 |

## 4. 法域专项跟踪表

| 法域 | 当前官方姿态 | filing / disclosure 规则 | citation / fact / evidence 规则 | sanction / 程序风险 | 当前默认产品姿态 |
| --- | --- | --- | --- | --- | --- |
| 中国 | 按当前研究包处理：**仍无单独的全国 court-user GenAI filing 指引被纳入本包**；继续盯最高法、互联网法院和法院公告 | 当前研究包里仍把法院提交链路工具放在 `P2 / 最后进入`，不把中国作为 court-facing 首发法域 | 当前重点仍是“不要直接进入法院提交链路”；citation / fact verifier 只允许作为内部 QA 思路，不允许对外承诺 | 一旦出现正式 court-facing 规则，默认按 `L3` 处理并专项复核 | 继续保持 `NO-GO / 不进入 filing chain` |
| 新加坡 | Singapore Courts **不禁止** court users 使用 GenAI 起草 court documents，但明确 guide 不改变既有法定义务、规则、职业规范和 practice directions | 除非法院特别要求，**不需要预先主动声明**使用了 GenAI；但 court user 对输出负全部责任 | 法律人和 SRP 都必须确保提交材料**独立核验、准确、真实、适当**；AI 不得被用来 fabricate / tamper evidence；现有要求继续适用于被引用的 case law、legislation、textbooks、articles | guide 本身没有单列 AI-only sanction ladder，但风险直接回到既有 court / professional consequences | 只允许 professional-internal drafting + pre-filing QA；不允许 auto-file |
| 香港 | 当前公开法庭材料里，最直接的官方文本仍是 **Judiciary 给 judges / staff 的 AI 指引**；其重点不是放开 court-facing use，而是提醒核验、保密和 legal analysis 风险 | 本轮 source set 未纳入单独的 public court-user filing guide；因此仍不把香港当作 court-facing workflow 已明确开放的法域 | Judiciary 明确提醒：AI 可能虚构 cases / citations / quotes，也可能给出 factual errors；法官在适当情形下应提醒律师履行义务并确认其已核验 AI research / citations，也可向 litigant 询问做了哪些 accuracy checks；在无 proven confidentiality 与 adequate verification 前，using GenAI for legal analysis **not recommended** | 当前公开材料更像“谨慎信号”而不是“可直接操作的 court-user safe harbour”；因此 sanction risk 暂按高风险待处理 | 保持 `NO-GO / not court-ready by default`；只保留内部 research / QA |
| 英格兰及威尔士 | CJC 已发布 **Interim Report and Consultation**，范围明确覆盖 pleadings、witness statements、expert reports；`current-work` page 显示 eight-week consultation 正在进行，`latest-news` page 进一步写明截止到 `2026-04-14 23:59`；同时 `Ayinde / Al-Haroun` 已把假引文 / 假材料的 sanction 路径讲清楚 | 当前不再只是抽象讨论“需不需要新规则”；consultation 的初步 proposal 已经是：在特定情形下要求 legal representatives 就 AI 使用作 declaration，核心落点是**AI 被用于生成法院拟采信的证据** | `Ayinde / Al-Haroun` 明确：律师对提交给法院的材料仍负专业责任；把 false citations / false material 放进 court documents，即使是 AI 造成、或未充分检查，也会进入 court response 范围 | 已明确存在的法院 powers 包括：public admonition、costs order、wasted costs order、strike-out、regulator referral、contempt，极端情形甚至 police referral；假材料进 court 可能触发 Hamid jurisdiction | 只允许内部 pre-filing QA、citation / fact verifier、draft review；不允许任何 auto-file 或 final court-doc automation |
| 澳大利亚 | Federal Court 当前仍在形成最终 position；2025-06-13 consultation 已结束，AI Project Group 正在 review submissions。Queensland 已给出更具体的 public guidance 和 practice directions | Federal Court 现阶段强调：parties 对 tendered material 继续负责；如 Judge / Registrar 要求，则应 disclose AI use。Queensland 则把 “accuracy of references” 拉到 practice directions 层 | Queensland 明确提醒：GenAI 会 make up fake cases / citations / quotes、refer to non-existent texts、get facts wrong；使用 AI 起草 affidavit / witness statement 时，最终文本必须准确反映当事人自己的 knowledge and words | Queensland 公开写明：如果带着 fake citations 或 inaccurate AI-generated information 进 court 并导致 hearing delay，**可能被下 costs order** | 澳大利亚继续按“碎片化 court rules”处理：只允许单法院 / 单工作流的内部 QA，不允许全国统一 court automation |

## 5. 需要重点盯的 court-facing 触发点

以下事件出现时，不应该只记进一般性监管 tracker，而应直接回写本文件：

- 新的 court guide / practice direction / registrar circular 明确 AI filing、AI disclosure、AI certification
- 新 judgment 直接处理 fake citations、fabricated facts、AI-generated witness material
- 法院首次明确要求：
  - mandatory disclosure
  - affidavit / witness statement 特别规则
  - expert report 使用 AI 的 leave requirement
  - citation 或 authority 逐项核验要求
- 法院或监管机构开始把 AI misuse 上升到：
  - wasted costs
  - strike-out
  - regulator referral
  - contempt

## 6. 对产品和交付的直接含义

如果产品要碰 court-facing workflow，当前最小可接受要求至少包括：

- `citation verifier`：每条 authority 必须回链到 primary source
- `fact verifier checklist`：事实、日期、金额、当事人、程序状态都要人工确认
- `document history`：保留 prompt、检索结果、输出、编辑痕迹和 sign-off
- `no auto-file`：任何 filing 只能由人类最终提交
- `role-based sign-off`：律师 / 法务 / court user 对最终文本具名负责
- `evidence boundary`：不得让 AI fabricate、embellish、strengthen、dilute evidence
- `disclosure readiness`：法院或 registrar 一旦要求 disclose，产品和团队要能立即说明 AI 在哪一步被用到

## 7. 一旦命中，默认按 L3 处理的红旗

- 出现 fake citation、fake quote、non-existent authority
- court document 中出现 AI 补出来的事实、日期、引述、法律依据
- 团队想把 affidavit / witness statement / expert report 交给 AI 直接起草最终内容
- 团队要求系统直接 auto-file 或生成“可直接提交法院”的 final package
- 法院开始要求 disclosure / certification，但产品和流程没有准备
- 出现代表性 sanctions case，表明 court-facing 风险已从“理论上高”变成“正在被处罚”

## 8. 默认回写哪些文档

| 变化类型 | 默认回写文档 |
| --- | --- |
| 新加坡 court-user guide / circular / sanctions 变化 | `singapore-legal-ai-go-no-go-memo`、`legal-ai-regulatory-monitoring-tracker`、本文件 |
| 香港 Judiciary / Law Society / court-facing 边界变化 | `hong-kong-legal-ai-go-no-go-memo`、`hong-kong-legal-ai-management-brief`、`legal-ai-regulatory-monitoring-tracker`、本文件 |
| 英格兰及威尔士 court-doc AI 规则 / sanctions 变化 | `uk-australia-uae-legal-ai-market-comparison`、`legal-ai-opportunity-risk-matrix`、`legal-ai-regulatory-monitoring-tracker`、本文件 |
| 澳大利亚 court guidance / practice direction / sanctions 变化 | `uk-australia-uae-legal-ai-market-comparison`、`legal-ai-opportunity-risk-matrix`、本文件 |
| 中国 court-facing AI 规则首次明确化 | `china-legal-ai-go-no-go-memo`、`legal-ai-opportunity-risk-matrix`、`legal-ai-regulatory-monitoring-tracker`、本文件 |

## 9. 专项监测节奏与责任分工

### 9.1 周度节奏

每周固定扫一轮下面这些来源：

- 新加坡：Singapore Courts、Registrar’s Circular、相关 judgments / notices
- 香港：Judiciary、HKLII / 公开判决、Law Society 新 guidance
- 英格兰及威尔士：CJC、Judiciary judgments、相关 practice direction / consultation 更新
- 澳大利亚：Federal Court notices、Queensland Courts practice directions / guidance
- 中国：最高法、互联网法院、地方法院公开规则与通报

默认责任人：

- `Research owner`：每周扫源、去重、记录新事件
- `Legal / compliance owner`：判断是否改 filing / disclosure / verification 边界
- `Product owner`：判断是否要冻结 court-facing roadmap、营销表述或 demo 范围

owner-of-record（专项 tracker）：

| 范围 | primary owner of record | secondary owner | 必做留痕 |
| --- | --- | --- | --- |
| 本 tracker 周度 source sweep | `Research owner` | `Legal / compliance owner` | 每周至少新增一条 dated no-change 或 change event |
| filing / disclosure / verification 边界判断 | `Legal / compliance owner` | `Product owner + Research owner` | 命中 `L2 / L3` 时补影响分析并决定是否改默认产品红线 |
| roadmap / demo freeze 决策 | `Product owner` | `Management sponsor` | 命中 `L3` 时同步冻结相关对外表述或 roadmap 项 |
| 仓库 / 知识库归档同步 | `Research owner` | `Product owner` | `L2 / L3` 事件与月度汇总同步到 `legal-ai-research-package-register-2026-03-20` |

### 9.2 月度节奏

每月固定做一次 sanctions / judgments 回看，单独盯：

- fake citation
- fabricated facts
- affidavit / witness statement 风险
- expert report 风险
- court-imposed disclosure / certification / costs / wasted costs / strike-out

### 9.3 季度节奏

每季度至少做一次 court-facing 结论回顾：

- 是否仍维持“只做 internal pre-filing QA，不做 auto-file”
- 是否有某个法域已出现足以改变 roadmap 的正式规则
- 是否需要把某个场景从 `HOLD` 调整为 `NO-GO`，或反过来从观察名单调到可试点

## 10. L2 / L3 触发阈值细化

下面这些变化，默认不按普通 L1 处理：

### 10.1 默认按 L2 处理

- 新 consultation、practice note、registrar circular 明确提到 AI filing / AI disclosure
- 新 judgment 讨论 fake citation、hallucination、fact verification，但未直接出现 sanctions
- 法院或职业团体首次把 affidavit / witness statement / expert report 单独拿出来谈 AI 风险

### 10.2 默认按 L3 处理

- 法院要求 mandatory disclosure、certification 或 affidavit supporting AI use
- 法院或 judgment 明确写出 costs / wasted costs / strike-out / regulator referral / contempt 的可适用后果
- 出现代表性 sanctions case，足以改变某法域的 court-facing 风险判断
- 任一法域发布可直接改变产品边界的正式 practice direction 或等效规则

## 11. 触发后的默认动作

### 11.1 命中 L2 时

- `5` 个工作日内补一段影响分析
- 明确是否需要更新：
  - `legal-ai-opportunity-risk-matrix`
  - 本文件
  - 对应法域 memo / brief
- 检查现有产品表述是否需要更保守

### 11.2 命中 L3 时

- `48` 小时内发起专项复核
- 立即冻结以下任一对外表述或 roadmap 项：
  - court-ready drafting
  - filing automation
  - affidavit / witness statement generation
  - automated citation / fact approval
- 先把相关场景打到 `HOLD`，再决定是否恢复
- 必要时同步更新售前禁区、demo 边界和客户沟通口径

### 11.3 命中 sanctions case 时的默认问题清单

- 这是 fake citation、fake quote、fake fact，还是 disclosure failure？
- 法院处罚的是律师、当事人、机构，还是全部？
- 法院是在“已有规则”下处罚，还是因为新 guidance 已经落地？
- 我们现有产品 / 流程是否会让同类问题重复出现？

## 12. 本轮官方锚点

新加坡：

- Singapore Courts `Guide on the Use of Generative AI Tools by Court Users`
  - `https://www.judiciary.gov.sg/docs/default-source/news-and-resources-docs/guide-on-the-use-of-generative-ai-tools-by-court-users.pdf?sfvrsn=3900c814_1`

香港：

- Hong Kong Judiciary `Guidelines on the Use of Generative Artificial Intelligence`
  - `https://www.judiciary.hk/doc/en/court_services_facilities/guidelines_on_the_use_of_generative_ai.pdf`

英格兰及威尔士：

- Civil Justice Council `Use of AI in preparing court documents`
  - `https://www.judiciary.uk/related-offices-and-bodies/advisory-bodies/cjc/current-work/use-of-ai-in-preparing-court-documents/`
- Civil Justice Council `Latest news`
  - `https://www.judiciary.uk/related-offices-and-bodies/advisory-bodies/cjc/latest-news/`
- Civil Justice Council `Interim Report and Consultation - Use of AI for Preparing Court Documents`
  - `https://www.judiciary.uk/wp-content/uploads/2026/03/Interim-Report-and-Consultation-Use-of-AI-for-Preparing-Court-Docume.pdf`
- `Ayinde v London Borough of Haringey; Al-Haroun v Qatar National Bank`
  - `https://www.judiciary.uk/wp-content/uploads/2025/06/Ayinde-v-London-Borough-of-Haringey-and-Al-Haroun-v-Qatar-National-Bank.pdf`

澳大利亚：

- Federal Court of Australia `Notice to the Profession`
  - `https://www.fedcourt.gov.au/news-and-events/29-april-2025`
- Federal Court of Australia Annual Report 2024–25 (`Use of Generative Artificial Intelligence`)
  - `https://www.fedcourt.gov.au/__data/assets/pdf_file/0011/572897/Part-1.pdf`
- Queensland Courts `Using Generative AI`
  - `https://www.courts.qld.gov.au/going-to-court/using-generative-ai`
- Queensland Courts `Practice Direction 4 of 2025: Accuracy of References in Submissions`
  - `https://www.courts.qld.gov.au/__data/assets/pdf_file/0011/882875/lc-pd-4-of-2025-Accuracy-of-References-in-Submissions.pdf`

中国：

- 最高人民法院《最高人民法院关于规范和加强人工智能司法应用的意见》
  - `https://www.court.gov.cn/zixun/xiangqing/382461.html`
- 最高人民法院《推进现代科技与司法审判工作深度融合 最高法发布“法信法律基座大模型”研发成果》
  - `https://www.court.gov.cn/zixun/xiangqing/447711.html`
- 最高人民法院官网
  - `https://www.court.gov.cn/`
- 最高人民法院知识产权法庭官网
  - `https://ipc.court.gov.cn/`

当前这组中国侧官方材料，更像法院内部 AI 应用规范、智能审判 / 诉讼服务建设与涉 AI 裁判规则来源，而不是面向 court users 的单独 filing / disclosure / verification guide。

## 13. 下次刷新优先页面清单

| 法域 | 优先页面 | 本轮核到的关键信号 | 下次刷新最该看什么 | 默认频率 |
| --- | --- | --- | --- | --- |
| 新加坡 | Singapore Courts `Guide on the Use of Generative AI Tools by Court Users` | court user 可使用 GenAI，但仍负独立核验和提交责任；默认不要求预先主动声明；法院可在有疑问时要求说明是否用了 AI 以及如何核验 | 是否新增 disclosure / certification 要求；是否新增与 affidavits、witnesses、experts 相关的补充规则 | 每周 |
| 香港 | Hong Kong Judiciary `Guidelines on the Use of Generative Artificial Intelligence` | 强调可能出现 fictitious cases / citations / quotes、factual errors；在无 proven confidentiality 与 adequate verification 前，legal analysis 不推荐；法官可要求律师或 litigant 说明核验情况 | 是否扩展到 court users / filing materials；是否新增更明确的 disclosure、verification 或 sanctions 信号 | 每周 |
| 英格兰及威尔士 | Civil Justice Council `Use of AI in preparing court documents` + `Latest news` + interim consultation paper | 当前 consultation 仍在进行；current-work page 显示 eight-week consultation closing on `2026-04-14`，latest-news page 进一步写明截止到 `2026-04-14 23:59`；interim paper 已提出在特定情形下作 AI-use declaration，核心是 AI 被用于生成法院拟采信的证据；范围明确覆盖 pleadings、witness statements、expert reports | consultation 是否结束并转 final report；是否出现 CPR / practice direction / court-document-specific disclosure 要求 | 每周 |
| 英格兰及威尔士 | `Ayinde / Al-Haroun` judgment | sanctions levers 已较清楚，足以改变对 court-facing drafting 的默认风险判断 | 是否有后续同类案件把 sanctions ladder 进一步固化或扩张 | 每周 |
| 澳大利亚 | Federal Court `Notice to the Profession` | Court 正在形成 Guideline 或 Practice Note；parties 继续对 tendered material 负责；若 Judge / Registrar 要求则应 disclose AI use | consultation 后是否落地正式 Guideline / Practice Note；是否出现更明确的 disclosure 义务 | 每周 |
| 澳大利亚 | Queensland Courts `Using Generative AI` + `Accuracy of References in Submissions` practice directions | 明确提醒 fake citations / quotes / facts 风险；不准把 affidavit / witness statement 弄成不反映本人 knowledge and words 的材料；出现 delay 可触发 costs order | 是否新增其他法院层级或更多子流程规则；是否把 AI-related accuracy issue 继续写进 practice directions | 每周 |
| 中国 | 最高法 / 互联网法院 / 地方法院公开规则与公告 | 当前更容易看到的是法院内部 AI 应用规范、诉讼服务 / 审判辅助建设材料和涉 AI 裁判规则；本轮 source set 里仍未形成单独全国 court-user AI filing guide | 是否首次出现 court-facing AI 提交、核验、披露或制裁的正式规则文本 | 每周 |

## 14. 监测事件记录模板

每次命中 court-facing 事件，建议至少按下面这张表记录一次：

| 日期 | 法域 | 来源页面 | 变化类型 | 触发等级 | 这次变化说了什么 | 会不会改变当前边界 | 需要更新哪些文档 | owner | 截止时间 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `YYYY-MM-DD` | 中国 / 新加坡 / 香港 / 英格兰及威尔士 / 澳大利亚 | 官方链接 | disclosure / verification / sanctions / filing / evidence | `L1 / L2 / L3` | 用一句话描述新增规则或案件 | `不会 / 可能 / 会` | `matrix / memo / brief / 本文件` | `Research / Legal / Product` | `YYYY-MM-DD` |

最低填写要求：

- 必须写清这是**规则更新、判例、practice direction、registrar circular 还是 consultation**
- 必须写清这次变化影响的是**filing、citation、fact verification、evidence、disclosure 还是 sanction**
- 必须写清默认动作：**记录、重看、专项复核、先转 HOLD**

## 15. 本次实时刷新记录（2026-03-20 UTC）

| 日期 | 法域 | 来源页面 | source access summary | 变化类型 | 触发等级 | 这次变化说了什么 | 会不会改变当前边界 | 需要更新哪些文档 | owner | 截止时间 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2026-03-20` | 新加坡 | Singapore Courts guide | Guide：`direct` | verification / disclosure | `L1` | 本次实时复核未见新 court-user disclosure 义务；仍是不要求预先主动声明，但法院可要求说明 AI 使用与核验方式 | `不会` | `本文件` | `Research` | `2026-03-27` |
| `2026-03-20` | 香港 | Hong Kong Judiciary guidance | Guidance：`direct` | verification / filing | `L1` | 本次实时复核未见单独的 public court-user filing guide；当前仍以核验、保密和对 legal analysis 的谨慎态度为主 | `不会` | `本文件` | `Research` | `2026-03-27` |
| `2026-03-20` | 中国 | 最高法 AI 司法应用意见 + 最高法官网 / 知识产权法庭官网 source sweep | `SPC` AI 司法应用意见：`source unavailable (automation)`，`court.gov.cn` 当前 shell 抓取返回 `403`；法信材料：`source unavailable (automation)`，同类 `SPC` 官方页当前 shell 抓取返回 `403`，后续默认转人工浏览器核验 | filing / verification | `L1` | 本次实时复核看到的仍是法院内部 AI 应用规范、智能审判 / 诉讼服务建设和涉 AI 裁判规则来源；在当前官方 source set 中，仍未见单独全国 court-user AI filing / disclosure / verification guide | `不会` | `本文件` | `Research` | `2026-03-27` |
| `2026-03-20` | 英格兰及威尔士 | CJC current-work page + latest-news page + interim report | current-work：`direct`；latest-news：`direct`；interim report：`direct` | disclosure / evidence | `L2` | current-work page 仍显示 eight-week consultation 正在进行，latest-news page 进一步写明 consultation 截止到 `2026-04-14 23:59`；interim paper 的初步 proposal 仍指向：在特定情形下要求 legal representatives 作 AI-use declaration，核心是 AI 被用于生成法院拟采信的证据 | `可能` | `uk-australia-uae-legal-ai-market-comparison` / `legal-ai-regulatory-monitoring-tracker` / `本文件` | `Research + Legal` | `已提前完成 2026-03-25 L2 分析；下次看 2026-04-14 23:59` |
| `2026-03-20` | 澳大利亚 | Federal Court AI notice / annual report + Queensland guidance / practice direction | `Federal Court` 官方 notice / annual-report 页面：`source unavailable (automation)`，`fedcourt.gov.au` 当前 shell 抓取返回 `403` challenge；Queensland guidance：`direct`；Queensland practice direction：`direct` | disclosure / sanctions | `L1` | 本次实时复核未见 Federal Court 已落地最终 guideline / practice note；Queensland 的 fake citations、accuracy 与 costs-risk 信号保持有效 | `不会` | `本文件` | `Research` | `2026-03-27` |

### 15.1 首次 court-facing sweep 的逐锚点判断（按 section 17.1 / 17.3 补齐）

为了避免首轮 `2026-03-20` court-facing 刷新只有法域级摘要、却没有逐锚点 `no-change / change` 判断，现按后续周度 sweep 的最低留痕格式补齐如下：

| 日期 | 法域 | 本轮检查过的官方锚点 | source access / fallback used | 每个锚点的 `no-change / change` 判断 | impact type | meaningful-change 结论 | 会不会改变当前统一边界 | 需要回写哪些文档 | owner | 下次动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2026-03-20` | 新加坡 | `Singapore Courts` court-user guide | Guide：`direct` | Guide：`no-change`，仍明确法院不禁止使用 generative AI 准备 court documents；除非法院特别要求，预先主动声明 AI 使用并非默认义务；court user 仍须独立核验并不得用 AI 生成拟向法院依赖的证据 | `verification / disclosure / evidence` | `不是，仍按 L1 no-change` | `不会` | `无` | `Research` | `2026-03-27` |
| `2026-03-20` | 香港 | `Judiciary` generative AI guidance | Guidance：`direct` | Guidance：`no-change`，当前公开锚点仍是面向 Judges / Judicial Officers / support staff 的内部使用原则，并未形成单独 public court-user filing / disclosure guide；因此仍不足以改写香港 court-user 边界判断 | `verification / filing` | `不是，仍按 L1 no-change` | `不会` | `无` | `Research` | `2026-03-27` |
| `2026-03-20` | 中国 | `SPC` AI 司法应用意见；`SPC` / 法信公开材料 | 意见：`source unavailable (automation)`，`court.gov.cn` 官方页在本轮 shell 抓取中返回 `403`；法信材料：`source unavailable (automation)`，同类 `SPC` 官方页在本轮 shell 抓取中返回 `403`，后续如需复核默认转人工浏览器核验 | 意见：`no-change`，仍是法院侧 AI 应用治理与辅助审判定位；法信材料：`no-change`，仍是法律大模型基础设施和法院侧能力建设信号，不构成全国 court-user filing / disclosure / verification 规则 | `filing / verification` | `不是，仍按 L1 no-change` | `不会` | `无` | `Research` | `2026-03-27` |
| `2026-03-20` | 英格兰及威尔士 | `CJC current-work` page；`CJC latest-news` page；`CJC` interim report / consultation paper | current-work：`direct`；latest-news：`direct`；interim report：`direct` | current-work：`no-change`，仍是针对 pleadings、witness statements、expert reports 的规则咨询并于 `2026-04-14` 截止；latest-news：`no-change`，仍把截止时间写到 `2026-04-14 23:59`；interim report：`no-change`，仍将“AI 用于生成法院拟采信的证据时可能需要 declaration”作为当前核心 proposal | `disclosure / evidence` | `是，按 L2` | `可能` | `uk-australia-uae-legal-ai-market-comparison` / `legal-ai-regulatory-monitoring-tracker` / `本文件` | `Research + Legal` | `已提前完成 2026-03-25 L2 分析；下次看 2026-04-14 23:59` |
| `2026-03-20` | 澳大利亚 | `Federal Court` AI notice；`Queensland Courts` generative AI guidance；`Queensland` accuracy-of-references practice direction | Federal Court：`source unavailable (automation)`，`fedcourt.gov.au` 官方页在本轮 shell 抓取中返回 `403` challenge；Queensland guide：`direct`；Queensland practice direction：`direct` | Federal Court：`no-change`，`2025-04-29` notice 仍表示 Court 正在考虑 guideline / practice note，现阶段仍以既有义务和法官 / registrar 要求下的 disclosure 为主；Queensland guide：`no-change`，仍强调 affidavit / witness statement 必须反映当事人本人知识与表达，且 fake citations 可能带来 costs risk；Queensland practice direction：`no-change`，仍将 AI 失准、虚构来源和 responsible person 识别作为当前控制点 | `disclosure / verification / sanctions` | `不是，仍按 L1 no-change` | `不会` | `无` | `Research` | `2026-03-27` |

### 15.2 提前完成 `2026-03-25` 的英格兰及威尔士 `CJC` `L2` 影响分析

基于 `CJC current-work` page、`latest-news` page、interim report 与 consultation cover sheet，本轮把原排队到 `2026-03-25` 的 `L2` 影响分析提前完成，结论如下：

- 当前变化**足以上调英格兰及威尔士 court-facing evidence / disclosure 风险描述的精度**，但**还不足以改写当前统一边界**。
- 近端风险并不是“所有 court documents 都要统一 disclosure”，而是 `CJC` consultation 已把最可能收紧的点收窄到 evidence-stage 文档：
  - `trial witness statements`：方向是要求 legal representatives 作声明，确认 AI 没有被用于生成、改写、加强、弱化或重述证人证据
  - `expert reports`：方向是要求 experts 识别并说明被用于报告的 AI（纯行政用途除外）
  - `skeleton arguments / advocacy documents / disclosure lists and statements`：当前 consultation 反而倾向认为**暂不需要额外 court rule**
- 对研究包的直接影响：
  - `NO-GO / no auto-file / no court-ready final output` 结论不变
  - 英格兰及威尔士 court-facing 风险应更明确地区分 `evidence-stage` 与一般 drafting / research：前者更接近 future declaration territory，后者目前仍主要落在既有 court duties + human verification
  - 如果未来要做 England-and-Wales court-adjacent workflow，至少要补 `document-type gating`、`evidence-chain provenance log`、`disclosure readiness pack`
  - 暂不回写 `legal-ai-opportunity-risk-matrix`，因为法域排序与统一 go / no-go 边界未变
- 因此，原 `2026-03-25` checkpoint 视为已提前完成；下一次英格兰及威尔士官方节点保持 `2026-04-14 23:59`
- 同日 live recheck 还确认：`CJC current-work` page 当前暴露的 consultation PDF 已切换到 `/2026/03/` official path；这只需要刷新 source anchor，不构成新的 substantive change，也不需要重新开启 `L2` 分析。

## 16. 中国 court-facing 监测分层规则

为了避免中国侧每次刷新都重复争论“这算不算真正的 court-facing 信号”，默认按下面三层处理：

| 证据层级 | 典型来源 | 默认等级 | 默认动作 |
| --- | --- | --- | --- |
| 法院内部 AI 应用 / 建设层 | 最高法关于 AI 司法应用的意见、智慧法院 / 法信 / 模型发布、审判辅助 / 诉讼服务建设稿件 | `L1` | 记录到本文件；说明这是 court-side governance / infrastructure，而不是 court-user filing rule；不改变当前 `NO-GO / 不进入 filing chain` |
| 面向诉讼参与人或律师的流程层 | 立案平台公告、诉讼服务中心规则、互联网法院操作说明、地方法院给 litigants / lawyers 的 AI 使用要求 | `L2` | `5` 个工作日内补影响分析；判断是否已出现 disclosure / verification / certification 信号；必要时回写中国 memo 和矩阵 |
| 全国性或高位阶 court-user 规则 / 制裁层 | 最高法正式 notice / 司法解释 / 全国诉讼服务规则、明确要求 AI disclosure / certification 的全国性文本、代表性 sanctions case | `L3` | `48` 小时内专项复核；先把任何 court-facing roadmap 维持在 `HOLD / NO-GO`；同步回写中国 memo、矩阵和总 tracker |

中国侧只有在第二层或第三层材料出现时，才应认真考虑是否把“目前没有单独全国 court-user filing guide”的判断改掉。

## 17. 当前开放监测队列

为了避免 section 15 的 refresh 记录写完后没人继续追踪，当前默认开放队列如下：

| 截止日期 | 法域 | 必做动作 | 默认 owner | 触发后默认回写 |
| --- | --- | --- | --- | --- |
| `2026-03-27` | 中国 / 新加坡 / 香港 / 澳大利亚 | 完成下一轮周度 source sweep，并用 section 14 模板至少记录一次 no-change 或 change event | `Research` | `本文件`，必要时回写对应 memo / tracker |
| `2026-04-14 23:59` | 英格兰及威尔士 | 在 CJC consultation closing time 当天复核 consultation page、latest-news page 和 interim paper，判断是否从 `L2` 升到更明确的规则变更判断 | `Research + Legal` | `本文件`、`legal-ai-regulatory-monitoring-tracker`、`uk-australia-uae-legal-ai-market-comparison`、必要时 `legal-ai-opportunity-risk-matrix` |

### 17.1 下次 court-facing sweep 的最低留痕包

为了避免后续 court-facing 周度刷新只留下“看过了 / 没变化”而无法复核，后续 `no-change` 或 `change` 事件至少要带上下面这些留痕项：

- 检查日期（UTC）和执行 owner
- 本轮至少检查过的官方锚点
  - 新加坡 `Singapore Courts` court-user guide
  - 香港 `Judiciary` generative AI guidance
  - 英格兰及威尔士 `CJC current-work` page
  - 英格兰及威尔士 `CJC latest-news` page
  - 英格兰及威尔士 relevant consultation / interim or final report page
  - 澳大利亚 `Federal Court` court-facing AI notice / annual-report entry
  - 澳大利亚 `Queensland Courts` guidance / practice direction
  - 中国 `SPC` AI 司法应用 / 法院公开规则源
- 对每个锚点补一条 source access 状态：
  - `direct`
  - `redirected`
  - `timeout`
  - `source unavailable`
  - `source unavailable (automation)`
- 如果原定官方 URL 重定向、超时、反爬挑战或暂时不可达：
  - 不得直接记为 `no-change`
  - 必须写明 `source unavailable` 或 `source unavailable (automation)`
  - 如果使用 fallback official page，必须补记具体页面
  - 如果自动抓取被 challenge / `403` 拦截，必须把人工浏览器复核写入 `下次动作`
  - 如果没有找到可替代的官方页面，必须把该锚点标为“本轮未完成核查”
- 对每个锚点写一句 `no-change / change` 判断
- 如果判断为 `change`，必须写明影响的是：
  - filing
  - disclosure
  - verification
  - evidence
  - sanctions
- 必须写明会不会改变当前 court-facing 统一边界：
  - `不会`
  - `可能`
  - `会`
- 如果答案是 `可能` 或 `会`，必须同步指定要不要回写：
  - `legal-ai-opportunity-risk-matrix`
  - 对应法域 memo / brief
  - `legal-ai-regulatory-monitoring-tracker`
  - `本文件`
- 最后用 section `17.2` 的规则判断：这次变化到底只是 `L1` 留痕，还是已经构成需要升级分析、冻结路线或改默认产品红线的 meaningful change

### 17.2 court-facing sweep 的 meaningful-change 判定

为了避免把所有 court-facing 新材料都误判成需要重写整包，默认按下面几类问题判断什么才算值得升级处理的 meaningful change：

- `L1 no-change`
  - 只是重复强化既有核验、保密、职责或 accuracy 要求
  - 只是法院内部 AI 应用 / 建设 / 治理材料，没有新增 court-user filing / disclosure / certification 规则
  - consultation / guidance 仍维持既有方向，没有把要求推进到新的正式规则层级
  - 对英格兰及威尔士 `CJC` 事项，如果 `current-work`、`latest-news` 与相关 consultation / interim material 只是继续确认 consultation 仍 open、scope 仍覆盖 pleadings / witness statements / expert reports，且 evidence-stage proposal 没有实质推进，默认只按 tracker-level `L1 no-change` 记为 status verification；在 `2026-04-14 23:59` closing-time recheck 之前，不重复开启新的 `L2` 分析或 memo 回写
- 官方源可达性 / 替代页面
  - 如果只是 court-facing 官方页在本轮自动抓取中重定向、超时、`403` challenge 或暂时不可达，但已有官方替代页面或人工浏览器复核仍支撑相同结论，默认不算 substantive meaningful change；应按 `L1` 记录 `source unavailable / source unavailable (automation)` 与 fallback official page used
  - 如果关键官方锚点在本轮既无法自动访问，也找不到可替代的官方页面，默认仍不算规则实质变化，但不得写成“已完成 no-change”；必须把该锚点记为未完成核查，并把人工复核或补刷写入 `下次动作`
- `L2 meaningful change`
  - 新 consultation、registrar circular、guidance、practice note 或 judgment 可能改变某个子流程的 filing / disclosure / verification / evidence 风险
  - 新材料开始把 pleadings、witness statements、expert reports、authorities、disclosure review 等子流程单独拿出来谈 AI 规则
  - 新材料虽然尚未形成正式强制义务，但已经足以要求补影响分析并判断是否需要上调风险或更新 memo / matrix
- `L3 meaningful change`
  - 出现 mandatory disclosure、certification、leave requirement、practice direction、正式 court-user filing rule、代表性 sanctions case，或其他足以改变默认产品边界的高位阶材料
  - 任一法域把 fake citation、fabricated facts、AI-generated evidence、court-user misuse 直接推到 costs / wasted costs / strike-out / regulator referral / contempt 的明确适用层
  - 中国出现全国性或高位阶的 court-user AI filing / disclosure / verification 正式规则文本

只要命中下面任一结果，就应认定为 meaningful change，而不是普通留痕：

- 会改变当前 `no auto-file / no court-ready final product` 的统一红线
- 会改变 affidavits、witness statements、expert reports、citation verifier、fact verifier 的默认允许范围
- 会改变 disclosure readiness、role-based sign-off 或 evidence boundary 的最低要求
- 会改变 `legal-ai-opportunity-risk-matrix` 里的 go / no-go、优先级或法域进入顺序
- 会要求冻结现有 court-facing roadmap、demo 范围或对外表述

如果新材料只是重复强化既有要求，没有改变上述任一边界或控制项，默认保留在 `L1 no-change`，只需按 section `17.1` 留下可复核证据，并按 section `14` 记录 dated event，不必重写 memo / matrix。

### 17.3 court-facing 周度标准输出模板

为了避免不同执行人留下的 court-facing dated update 颗粒度不一致，后续周度 sweep 默认至少按下面模板输出一次，哪怕结论是 `no-change` 也一样：

| 日期 | 法域 | 本轮检查过的官方锚点 | source access / fallback used | 每个锚点的 `no-change / change` 判断 | impact type | meaningful-change 结论 | 会不会改变当前统一边界 | 需要回写哪些文档 | owner | 下次动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `YYYY-MM-DD` | 中国 / 新加坡 / 香港 / 英格兰及威尔士 / 澳大利亚 | 列出本轮实际检查过的官方页面 | 对每个锚点写 `direct / redirected / timeout / source unavailable / source unavailable (automation)`；如使用 fallback official page 则补记具体页面 | 至少一句话写清每个锚点是 `no-change` 还是 `change` | `filing / disclosure / verification / evidence / sanctions` | `不是` / `是，按 L2` / `是，按 L3` | `不会 / 可能 / 会` | `matrix / memo / brief / regulatory tracker / 本文件 / 无` | `Research / Legal / Product` | `YYYY-MM-DD` |

最低填写要求：

- 如果结论是 `不是 meaningful change`，也必须写明为什么仍是 `L1 no-change`
- `source access / fallback used` 这一列不能留空；如果没有 fallback，也要明确写 `direct`、`redirected`、`timeout`、`source unavailable` 或 `source unavailable (automation)`
- 如果官方页被 `403` challenge、超时或其他自动抓取限制拦截，必须明确写出 `source unavailable (automation)`，并把人工浏览器复核写入 `下次动作`
- 如果结论是 `是，按 L2` 或 `是，按 L3`，必须写清楚触发点是 filing、disclosure、verification、evidence 还是 sanctions
- 如果决定“不回写任何文档”，也要明确写 `无`，避免事后无法判断是“无需回写”还是“漏写”
- 如果本轮新增了 section `12` 之外的新官方 court-facing 锚点，应把新源补进 section `12` 或在本轮记录中说明为什么可以替代既有锚点
