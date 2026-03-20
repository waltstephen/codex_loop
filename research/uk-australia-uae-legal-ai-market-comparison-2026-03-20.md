# 英格兰及威尔士 / 澳大利亚 / 阿联酋 common-law hubs 法律 AI 扩张市场对比备忘录

日期：2026-03-20

目的：在现有中国、新加坡、香港判断基础上，补一轮**香港、新加坡之外**的潜在扩张市场对比。本轮只看更适合复制“专业人士内部工具 / 企业内受控工具”路线的法域，不把公众法律意见 bot 或自动进入法院提交链路当成首发模式。

这不是法律意见，而是 `2026-03-20` 的产品、合规和市场进入研究快照。

## 1. 结论先行

- 本轮对比法域：
  - **英格兰及威尔士**
  - **澳大利亚**
  - **阿联酋 common-law hubs（DIFC / ADGM）**
- 推荐进入顺序：
  1. **英格兰及威尔士：GO（P0）**
  2. **澳大利亚：CONDITIONAL GO（P1）**
  3. **阿联酋 common-law hubs（DIFC / ADGM）：CONDITIONAL GO（P2 / 观察名单）**
- 最适合先复制的场景：
  - **Legal RAG / citation-safe drafting**
  - 其次才是**企业合同 / 合规 copilot**
- 当前不建议优先复制的场景：
  - 面向公众的开放式法律意见 bot
  - 未经强复核的法院提交链路自动化
  - 默认把客户数据送入共享训练池的“通用助手”

## 2. 横向比较：为什么这样排序

| 法域 | 官方材料成熟度 | 执业边界清晰度 | 更适合先做的第一种服务模式 | 当前不应先做 | 当前判断 | 关键原因 |
| --- | --- | --- | --- | --- | --- | --- |
| 英格兰及威尔士 | 高 | 高 | England & Wales Legal RAG、citation-safe drafting、受监管的人类签发 drafting assistant | 面向公众的开放式法律意见 bot、自动进入 court filing 链路 | GO（P0） | 有 Law Society、SRA、Judiciary、Civil Justice Council 四层材料；既能看到 professional-internal 路线，也能看到 court-facing 责任边界 |
| 澳大利亚 | 中高 | 中 | professional-internal Legal RAG、合同 / 合规 copilot、due diligence / drafting assistant | 跨州一把梭的 court-facing automation、公众结论型 bot | CONDITIONAL GO（P1） | 职业团体和法院都在出材料，但联邦 / 州法院协议和执业材料更碎片化，适合先在单州或单工作流切入 |
| 阿联酋 common-law hubs（DIFC / ADGM） | 中 | 中低 | 双语 regulatory / knowledge assistant、企业内合同 / 合规 copilot、争议解决前置 research assistant | 面向 onshore 大众的一般法律意见 bot、全国统一 court automation | CONDITIONAL GO（P2 / 观察名单） | AI 治理和 common-law hub 基础设施强，但 legal services licensing、court guidance、数据与执业边界更依赖 DIFC / ADGM 等具体区域，不是单一全国框架 |

## 3. 为什么英格兰及威尔士排第一

### 3.1 这轮最强的信号

- **Law Society** 已经把 generative AI 放进清晰的执业治理框架：要求遵守 SRA 规则、复核供应商数据管理、处理 confidentiality / data governance / liability / insurance，并明确输出要做准确性校验。
- **SRA** 已经批准首家 AI-driven law firm，但批准条件不是“放开做”，而是：
  - 不是 autonomous 模式
  - 客户批准后才会推进步骤
  - 有 supervision 和 monitoring
  - named regulated solicitors 对系统输出和后果承担最终责任
  - regulated law firms 仍需维持最低保险
- **Judiciary / Civil Justice Council** 已经把“AI 用于 court documents”放到明确的规则讨论轨道上；而且 `2026-03-20` 本轮刷新看到，`CJC` current-work page 显示 eight-week consultation 正在进行，`latest-news` page 进一步写明截止到 `2026-04-14 23:59`，而 interim report 的初步 proposal 已经开始触及**在特定情形下就 AI 使用作 declaration**，核心落点是 AI 被用于生成法院拟采信的证据，说明 court-facing 边界正在从“原则提醒”往更具体规则推进。

### 3.1.1 提前完成 `2026-03-25` 的 `CJC` `L2` 影响分析

- 当前 `CJC` consultation 的近端风险并不是“所有 court documents 都要统一 disclosure”，而是把最可能落地的变化收窄到了 evidence-stage 文档。
- 当前最值得按 potential formal-declaration 方向看待的是：
  - `trial witness statements`：方向是要求 legal representatives 声明 AI 没有被用于生成、改写、加强、弱化或重述证人证据
  - `expert reports`：方向是要求 experts 识别并说明被用于报告的 AI（纯行政用途除外）
- 对 `skeleton arguments / advocacy documents / disclosure lists and statements`，当前 consultation 反而没有 pressing case 增加额外 court rule。
- 这意味着英格兰及威尔士仍然是 **professional-internal P0**，但 court-adjacent 产品必须更明确地把 `evidence-stage workflows` 单独打成高风险红线，而不是只写成泛化的“人工复核更强”。
- 同日 live recheck 还确认：`CJC current-work` page 当前挂出的 consultation PDF 已切换到 `/2026/03/` official path；这只是 source-anchor refresh，不改变上面的 evidence-stage judgement、`P0` 排序或 court-facing 红线。

### 3.2 更适合先做什么

- **England & Wales Legal RAG / citation-safe drafting**
- 面向律所研究岗、起草岗、知识管理团队和大型企业法务
- 默认“先检索、再生成”，每次输出都带：
  - 来源
  - 日期
  - 法域
  - citation

### 3.3 这里的执业边界是什么

可以先做：

- 内部 research memo 草稿
- citation-safe drafting
- 法规 / 判例更新提醒
- firm-approved 或 in-house-approved 的内部工具

不要先做：

- 公众开放式个案法律意见 bot
- 无来源裸答
- 未经律师逐项核验直接进入 pleadings、witness statements、expert reports 的自动化流程
- 任何会生成、改写、加强、弱化或重述 `trial witness evidence` 的 workflow
- 任何没有 `AI-use disclosure readiness` 的 expert-report drafting / review workflow
- 默认用客户数据测试、模板化或再训练

### 3.4 必须守住的最低 safeguards

- England & Wales jurisdiction filter
- source pinning + citation verifier
- client / matter / document 级权限隔离
- 不默认用客户数据再训练
- 人类最终签发
- 输出、引用、模型版本和审批日志可追溯
- 对 court-facing 文档默认加更高一级复核，而不是自动提交
- `document-type gating`：把一般 drafting / research 与 `trial witness statements`、`expert reports`、其他 evidence-stage 文档分开；后者默认关闭或只保留 checklists / verifier
- `evidence-chain provenance log`：保留输入材料范围、AI 使用位置、引用来源、人工修改和 sign-off
- `disclosure readiness pack`：如法院、对方或 expert-governance 规则要求说明 AI 使用，团队应能快速说明用途、范围、人工核验与最终责任人

### 3.5 当前还缺什么证据

- England & Wales 法域专用 benchmark：
  - case citation accuracy
  - statute / regulation pinning
  - overruled / outdated authority 识别
- 至少 3 家目标客户访谈：
  - 中型律所
  - 大型律所知识管理团队
  - 企业法务
- 采购和合规证据：
  - client-data reuse 是否一票否决
  - 是否要求 VPC / dedicated tenant
  - 保险和责任条款如何落合同

## 4. 为什么澳大利亚排第二

### 4.1 这轮看到的关键信号

- **Law Council of Australia** 已经把 AI 放进全国职业议程，并维护一个汇总各州 / 各团体资源的 portal。
- **Federal Court of Australia** 明确表示：
  - AI 使用需要与既有对法院和对方当事人的义务一致
  - 如法官或 Registrar 要求，party / practitioner 应披露 AI 使用
  - 法院在继续考虑是否需要 Guidelines 或 Practice Note
- **Queensland Courts** 已经把“references in submissions 的准确性”写进 Practice Direction，并要求**具体负责的个人法律从业者**具名、核验来源，否则可能面临 costs 或监管转介。
- **OAIC** 对 generative AI 训练和微调的隐私义务写得很清楚：如果涉及个人信息，不能只写模糊的“research”，需要明确说明是否用于 AI 训练。

### 4.2 更适合先做什么

- professional-internal Legal RAG
- 单州或单联邦工作流下的 drafting assistant
- 企业法务 / 合规团队的合同 / 合规 copilot

更现实的进入方式不是“一上来就做全澳通用法院机器人”，而是：

- 先选一条 jurisdiction slice
- 先选一类 professional-internal workflow
- 先在 strong human review 模式下证明价值

### 4.3 这里的执业边界是什么

可以先做：

- 内部 research / drafting
- 合同条款抽取与风险提示
- 合规义务映射
- due diligence / data room 摘要

不要先做：

- 跨州 / 跨法院一把梭的 court-facing automation
- 面向公众的结论型法律意见 bot
- 把 confidential / privileged 数据送进公众模型
- 不做法域切片就输出“澳大利亚法”统一答案

### 4.4 必须守住的最低 safeguards

- Federal / state / territory jurisdiction filter
- 引用校验和日期过滤
- matter / 客户 / 文档级隔离
- public tool 禁止处理 confidential / privileged 材料
- training、retention、notification 条款前置核清
- 法院链路默认人工确认和具名负责

### 4.5 当前还缺什么证据

- 先从哪个州 / 哪个法院体系切入：
  - NSW
  - Victoria
  - Queensland
  - Federal Court
- 哪些客户更愿意先买：
  - 企业法务
  - 中大型律所
  - ALSP / litigation support
- 澳大利亚本地 benchmark：
  - 州 / 联邦法律混用错误率
  - citation 准确率
  - public / secure tool 边界下的用户采纳率

## 5. 为什么阿联酋 common-law hubs 先放观察名单

### 5.1 先说明范围

这轮不是在评估“整个阿联酋 onshore 法律服务市场”。

我这轮只把**DIFC / ADGM 这类 common-law hubs**当作潜在扩张入口，因为我能核到的官方材料主要集中在这里：

- **DIFC Courts** 对 AI 在诉讼中的使用有明确 guidance
- **ADGM** 对 legal service providers、English common law、数据保护和治理要求更清晰
- **UAE Cabinet / UAE Legislation** 在更高层面释放出 AI-native regulation 和 regulatory intelligence 的治理信号

### 5.2 为什么它值得看，但不排第一

值得看，是因为：

- ADGM 直接适用 English common law，法律系统对国际法律科技产品更熟悉
- DIFC Courts 已经明确：
  - proceedings 中使用 AI 要尽早披露
  - 问题最好在 CMC 前解决
  - witness statements 仍应是证人自己的话
- ADGM 对 legal service providers 的 licence 条件更明确，要求：
  - managing partner 资历
  - professional indemnity insurance
  - annual return
  - defined principles
- ADGM 的 DPIA 指南已经把 AI、machine learning、automated decision making 列为高风险处理触发条件之一
- UAE 2026 年的 regulatory intelligence whitepaper 说明这里对“AI + regulation / law”有明显的政策推动意愿

不排第一，是因为：

- 更适合进入的是 **DIFC / ADGM 这类特定 common-law hub**
- 不是一个“全国统一、执业边界完全明确”的法律 AI 市场
- free zone / onshore、英语 / 阿语、court / non-court、regulated legal services / enterprise tooling 之间边界更复杂

### 5.3 更适合先做什么

- 双语 regulatory / knowledge assistant
- 企业内合同 / 合规 copilot
- 争议解决前置 research / drafting assistant

也就是说，更像：

- 国际律所或区域总部内部工具
- DIFC / ADGM 工作流周边工具

而不像：

- 面向阿联酋大众的全国统一法律意见 bot

### 5.4 这里的执业边界是什么

可以先做：

- bilingual research / drafting
- internal compliance / regulatory monitoring
- dispute-support research

不要先做：

- onshore 大众法律意见机器人
- 未经披露和复核的 court-facing automation
- 不区分 DIFC / ADGM / onshore 边界的统一“UAE legal AI”

### 5.5 必须守住的最低 safeguards

- DIFC / ADGM / onshore jurisdiction gating
- Arabic + English source grounding
- 对 AI / 新技术 / 高风险个人数据处理先做 DPIA
- 不默认用客户数据再训练
- local counsel / local regulated partner 参与
- proceedings 相关使用默认提前披露、强日志和人工签发

### 5.6 当前还缺什么证据

- 先走 DIFC 还是 ADGM
- 本地执业伙伴如何配置
- 双语语料授权能否拿到
- 企业客户更关心 privacy / hosting，还是更关心执业责任 / insurance
- 哪些场景能留在 internal tooling，哪些会被视为 regulated legal services

## 6. 建议的扩张顺序

如果香港、新加坡之后要继续往外走，我会这样排：

1. **英格兰及威尔士**
2. **澳大利亚**
3. **阿联酋 common-law hubs（DIFC / ADGM）**

背后的逻辑是：

- 先去**职业规则、法院边界、供应商治理要求都更清楚**的市场
- 先做**professional-internal** 工具，再碰面向公众或法院提交链路
- 先选**单一法域更清晰**的市场，再进**多层边界并存**的市场

## 7. 跨市场统一的 no-go 边界

下面这些边界，在这三组法域里都不适合作为早期进入方式：

- 面向公众的开放式个案法律意见 bot
- 自动进入法院 / 仲裁 / 监管提交链路
- 无来源、无引用、无人工签发的法律起草
- 默认把客户数据送入共享训练池
- 无法解释 retention、deletion、sub-processor、logs 的工具

## 8. 如果继续推进，下一步最值得做什么

- 为英格兰及威尔士做一份单独 go / no-go memo
- 为澳大利亚做一份“单州切入”备忘录，而不是先做全国版本
- 为 DIFC / ADGM 做一张“free zone / onshore / court / legal-services licensing”边界图
- 给这三组法域分别补 benchmark 规范和客户访谈提纲

## 9. 本轮用到的核心官方锚点

英格兰及威尔士：

- Law Society《Generative AI – the essentials》  
  https://www.lawsociety.org.uk/en/Topics/AI-and-lawtech/Guides/Generative-AI-the-essentials
- SRA《SRA approves first AI-driven law firm》  
  https://media.sra.org.uk/sra/news/press/garfield-ai-authorised/
- Courts and Tribunals Judiciary《Artificial Intelligence (AI) – Judicial Guidance (October 2025)》  
  https://www.judiciary.uk/guidance-and-resources/artificial-intelligence-ai-judicial-guidance-october-2025/
- Civil Justice Council《Use of AI in preparing court documents》  
  https://www.judiciary.uk/related-offices-and-bodies/advisory-bodies/cjc/current-work/use-of-ai-in-preparing-court-documents/
- Civil Justice Council《Latest news from the Civil Justice Council》  
  https://www.judiciary.uk/related-offices-and-bodies/advisory-bodies/cjc/latest-news/
- Civil Justice Council《Interim Report and Consultation - Use of AI for Preparing Court Documents》  
  https://www.judiciary.uk/wp-content/uploads/2026/03/Interim-Report-and-Consultation-Use-of-AI-for-Preparing-Court-Docume.pdf

澳大利亚：

- Law Council of Australia《Artificial Intelligence and the Legal Profession》  
  https://lawcouncil.au/policy-agenda/advancing-the-profession/artificial-intelligence-and-the-legal-profession
- Federal Court of Australia《Notice to the Profession: Artificial intelligence use in the Federal Court of Australia》  
  https://www.fedcourt.gov.au/news-and-events/29-april-2025
- Queensland Courts《Practice Direction 4 of 2025 - Accuracy of References in Submissions》  
  https://www.courts.qld.gov.au/__data/assets/pdf_file/0011/882875/lc-pd-4-of-2025-Accuracy-of-References-in-Submissions.pdf
- Queensland Courts《Guidelines for Responsible Use of Generative AI by Non-Lawyers》  
  https://www.courts.qld.gov.au/going-to-court/using-generative-ai
- OAIC《Guidance on privacy and developing and training generative AI models》  
  https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models

阿联酋 common-law hubs：

- DIFC Courts《Practical Guidance Note No. 2 of 2023 Guidelines on the use of large language models and generative AI in proceedings before the DIFC Courts》  
  https://www.difccourts.ae/rules-decisions/practice-directions/practical-guidance-note-no-2-2023-guidelines-use-large-language-models-and-generative-ai-proceedings-difc-courts
- ADGM《The ADGM Legal Framework》  
  https://www.adgm.com/legal-framework
- ADGM《English Common Law》  
  https://www.adgm.com/adgm-courts/english-common-law
- ADGM《Enhanced Controls for Legal, Tax and Company Service Providers》  
  https://www.adgm.com/media/announcements/adgm-registration-authority-publishes-enhanced-controls-for-legal-tax-and-company-service-providers
- ADGM ODP《How to Conduct a Data Protection Impact Assessment (DPIA)》  
  https://assets.adgm.com/download/assets/ADGM%2B-%2BHow%2Bto%2BConduct%2Ba%2BData%2BProtection%2BImpact%2BAssessment%2B%28DPIA%29%2B%28Explainer%29.pdf/16a7bedc58ad11efa80cb2570a3a6e3c
- UAE Legislation《Federal Decree by Law No. (45) of 2021 Concerning the Protection of Personal Data》  
  https://uaelegislation.gov.ae/en/legislations/1972
- UAE Cabinet / UAE Legislation《UAE Government launches its 1st Whitepaper on shaping future of regulatory intelligence》  
  https://uaelegislation.gov.ae/en/news/uae-government-launches-at-world-economic-forum-in-davos-its-1st-whitepaper-on-shaping-future-of-regulatory-intelligence
