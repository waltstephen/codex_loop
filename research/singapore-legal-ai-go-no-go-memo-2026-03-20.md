# 新加坡法域法律 AI go / no-go 决策备忘录

日期：2026-03-20

目的：基于现有《法律 LLM / AI 与法律交叉调研》和《法律 AI 机会 / 风险矩阵（可执行版）》，在中国之后补一份更适合亚洲扩张判断的法域备忘录。本备忘录对比本轮额外检查的**新加坡**与**香港**官方材料，选定一个更适合优先进入的目标司法辖区，并对 2 个高价值法律 AI 场景给出 go / no-go 判断、目标用户、服务模式、合规边界、必要 safeguard、证据缺口和进入优先级。

结论先行：

- 本轮对比的潜在扩张法域：**新加坡**、**香港**
- 本轮选定的目标司法辖区：**新加坡**
- 评估场景 1：**Singapore-law Legal RAG / citation-safe drafting**
- 评估场景 2：**企业合同 / matter workflow copilot（先做企业内法务 / 合规团队）**
- 总体建议：
  - 场景 1：**GO（P0）**
  - 场景 2：**CONDITIONAL GO（P1）**
  - 当前明确不建议优先切入：**面向公众的开放式法律意见 bot**、**直接进入法院提交链路的自动化工具**

这不是法律意见，而是 `2026-03-20` 的产品、合规和市场进入研究快照。

## 1. 为什么这轮先选新加坡，而不是香港

本轮两地都值得继续跟，但如果只能先选一个作为中国之后的近邻扩张法域，我会先选**新加坡**。

| 法域 | 本轮额外检查到的官方 / 行业材料 | 更适合的第一种服务模式 | 当前判断 |
| --- | --- | --- | --- |
| 新加坡 | Ministry of Law 最终版《Guide for Using Generative AI in the Legal Sector》、Singapore Courts《Guide on the Use of Generative AI Tools by Court Users》、LawNet AI / GPT-Legal、LTP + Copilot for SG law firms | 专业人士内部工具、source-grounded research / drafting、受控合同 / workflow copilot | **先进入** |
| 香港 | PCPD《Model Personal Data Protection Framework》、PCPD 员工使用 GenAI 指南、Judiciary 内部生成式 AI 指南 | 企业内、可审计、强权限控制的文档 / 合规工具 | **下一站候选法域** |

为什么先做新加坡：

- 我本轮看到的新加坡官方材料更直接覆盖了**法律行业使用 GenAI**、**法院用户如何使用 GenAI**、以及**法律工作流数字化基础设施**三层。
- 这意味着产品更容易被定义成“专业人士内部工作流工具”，而不是模糊的公开 AI 助手。
- 香港并不是不值得做，而是我本轮读到的官方材料更偏**AI / 数据治理框架**和**员工使用规范**，更适合后续作为第二阶段扩张法域，特别是双语文档处理、跨境合规和仲裁周边场景。

## 2. 目标用户与服务模式

### 场景 1：Singapore-law Legal RAG / citation-safe drafting

目标用户：

- 新加坡律所的研究 / 起草团队
- 企业法务研究和知识管理团队
- 区域总部的法务 / 合规团队

建议服务模式：

- **专业人士内部工具**，而不是面向公众开放
- 优先 `tenant-isolated SaaS`、专属实例或 VPC
- 默认“先检索、再生成”，每次输出都带**来源、日期、法域和引用**
- 只用于研究、备忘录草稿、内部问答和监管变化跟踪

### 场景 2：企业合同 / matter workflow copilot

目标用户：

- 新加坡区域总部的企业法务 / 合规团队
- 中大型企业的合同管理和审批团队
- 第二阶段再考虑小中型律所

建议服务模式：

- **企业内 workflow copilot**
- 嵌入 CLM、DMS、matter 管理或审批系统
- 优先 firm / company-approved secure tool，而不是开放式公众模型
- 先做 intake、条款比对、风险提示、审批前预筛查，不做自动批准

## 3. 决策摘要

| 场景 | 决策 | 进入优先级 | 推荐服务模式 | 当前不建议的做法 |
| --- | --- | --- | --- | --- |
| Singapore-law Legal RAG / citation-safe drafting | GO | P0 | 专业人士内部 research / drafting assistant，必须回链来源并保留人工复核 | 无来源裸答；对公众直接输出个案化法律意见；未经律师 / 法务核验直接用于法院或监管提交 |
| 企业合同 / matter workflow copilot | CONDITIONAL GO | P1 | 企业内、受控、可审计的 workflow copilot，先接企业法务 / 合规团队 | 自动批准合同；跨客户 / 跨 matter 混用数据；用公众模型直接处理 confidential / highly confidential 信息 |

## 4. 场景 1：Singapore-law Legal RAG / citation-safe drafting

### 4.1 为什么是 GO

这是新加坡最适合作为第一落地场景的原因：

- 新加坡 Ministry of Law 的最终版法律行业 GenAI 指南，已经把**legal research、document drafting、contract review**等任务放入明确的法律行业使用场景。
- Singapore Courts 已明确给法院用户一套可执行的使用边界：并不禁止使用 GenAI，但使用者仍然要对事实、引文、法律依据和提交内容负责。
- LawNet AI / GPT-Legal 说明新加坡本地法律检索和 source-grounded AI 已经进入真实法律工作流，市场教育成本比很多法域更低。

### 4.2 合规边界

可以做：

- 新加坡法律、判例、法规和监管材料的检索增强问答
- research memo 草稿
- 内部监管监测和变化摘要
- 引用插入、出处回链、版本和日期标注

不要做：

- 面向公众提供开放式、结论型、个案化法律意见
- 输出无来源裸答
- 未经律师 / 法务审查直接进入法院或监管提交链路
- 把生成结果包装成“权威结论”而不暴露检索来源

### 4.3 必要 safeguard

- 检索和引用：
  - 只从可授权、可追溯的新加坡法律语料中检索
  - 默认显示来源、日期、法域和 citation
  - 校验引用是否真实存在，并尽可能检查相关判例是否仍是 good law
- 人工复核：
  - 研究 memo、客户交付件、法院材料一律人工签发
  - 输出标记为 draft / internal use unless reviewed
- 供应商与数据：
  - 评估 retention、training、sub-processor 和删除策略
  - confidential / highly confidential 数据只进入 approved secure tools
- 过程与留痕：
  - 查询、检索结果、模型版本和审批结果都留日志
  - 可回放关键草稿的来源与修改历史

### 4.4 证据缺口

- 需要一套**新加坡法域专用 benchmark**：
  - 判例和法规定位
  - 引用准确率
  - 过期 / 失效材料识别
  - jurisdiction mix-up 误差
- 需要明确语料方案：
  - 是直接接入已授权法律数据库，还是自建受许可语料层
  - 覆盖 primary law、subordinate legislation、监管材料和实践指引到什么程度
- 需要 pilot 证据：
  - 用户是否真的点击来源
  - 引用展示是否足够快
  - 研究岗和起草岗是否愿意把它放进日常工作流

### 4.5 go / no-go 触发条件

保持 GO 的条件：

- 能稳定回链到新加坡权威来源
- 有 citation verifier、日期过滤和法域过滤
- 高风险输出必须进入律师 / 法务复核
- confidential / highly confidential 数据不落到未批准工具

转为 NO-GO 的条件：

- 只能做无来源裸答
- 无法说明知识来源是否可授权、可更新、可追溯
- 产品被定位成公众法律意见机器人
- 计划直接进入法院提交链路而不做逐项核验

## 5. 场景 2：企业合同 / matter workflow copilot

### 5.1 为什么是 CONDITIONAL GO

这个场景价值很高，但比场景 1 更依赖部署、集成和数据治理，所以我把它放在 `P1`。

原因：

- 新加坡法律行业 GenAI 指南已经把 practice management、matter / case management、contract lifecycle management、document review、contract analysis / review 列为明确使用场景。
- 但一旦进入合同和 matter 工作流，数据敏感度、客户保密、审批责任和供应商尽调要求都会显著上升。
- Ministry of Law 指南对 confidential / highly confidential 数据的工具边界更明确，这使得“能不能做 secure deployment”变成 go / no-go 的关键。

### 5.2 合规边界

可以做：

- 合同 intake 和 triage
- 条款提取、模板比对、风险提示
- matter 级任务分派、状态跟踪和审批前预筛查
- 内部政策与合同条款的一致性检查

不要做：

- 自动批准合同
- 自动替代律师 / 法务做最终签发
- 用公众模型直接处理 confidential / highly confidential 信息
- 跨客户、跨 matter 混合上下文

### 5.3 必要 safeguard

- 部署：
  - confidential 数据仅使用 firm / company-approved secure GenAI tools
  - 高敏感场景优先专属实例、VPC 或本地受控环境
- 权限与隔离：
  - matter / 客户 / 业务单元级权限隔离
  - least-privilege access
  - information barrier 和 DLP
- 输出与流程：
  - 所有风险提示都可回链到条款、模板、政策或规则来源
  - 版本历史、审批日志和 reviewer identity 全量留存
  - 高风险合同必须升级到人工复核
- 供应商治理：
  - 合同明确 retention、training、删除、事故通报和子处理商
  - 评估模型对 confidential / highly confidential 数据的适用边界

### 5.4 证据缺口

- 需要客户级 / matter 级隔离是否可落地的技术验证
- 需要至少一套面向新加坡和区域总部场景的合同评测集：
  - 条款提取
  - deviation detection
  - fallback clause suggestion
  - 升级命中率
- 需要产品侧证据：
  - 审批流怎么接
  - review queue 怎么设计
  - 人工是否真的愿意采纳风险提示
- 需要法律和采购侧证据：
  - 客户 / 内部业务方是否接受 GenAI 参与合同流程
  - 是否需要 client opt-out 或额外披露

### 5.5 go / no-go 触发条件

保持 CONDITIONAL GO 并进入 pilot 的条件：

- 能做到 approved secure tool + 数据隔离 + 审批流接入
- 风险提示可以被人工复核和回退
- 供应商可明确承诺 retention / training / deletion 边界

转为 NO-GO 的条件：

- 客户或业务方要求“自动批准”
- 无法证明 matter / 客户隔离
- 供应商默认保留或再训练 confidential 数据
- 无法保留版本历史、审批日志和 reviewer 痕迹

## 6. 新加坡法域下的统一 no-go 边界

在当前阶段，不建议优先做：

- 面向公众的开放式法律意见 bot
- 直接进入法院提交链路的自动化工具
- 无来源、无引用、无人工签发的法律起草工具
- 默认把客户 / matter 数据送入未批准的公众模型

原因不是“新加坡不能做 legal AI”，而是：

- 新加坡官方材料已经把责任明确压回使用者和专业人士
- 这使得“source-grounded + human-reviewed + secure deployment”成为更自然的第一进入方式
- 任何跳过这些基础控制的产品，都会更早撞上责任、信任和采购门槛

## 7. 如果从亚洲扩张进入顺序来排，我会这样做

1. **中国：企业合同 / 合规 copilot**
2. **中国：中文 Legal RAG / citation-safe drafting**
3. **新加坡：Singapore-law Legal RAG / citation-safe drafting**
4. **新加坡：企业合同 / matter workflow copilot**
5. **香港：企业内合规 / 文档工作流工具**

判断逻辑：

- 先做内部专业人士工具，再做公众工具
- 先做 source-grounded research / drafting，再做更高敏感的数据工作流
- 在新加坡先做 professional-internal 模式，再把香港作为第二阶段的 common law + bilingual 扩张法域

## 8. 本备忘录依赖的当前规则和市场锚点

新加坡：

- Ministry of Law《Guide for Using Generative AI in the Legal Sector》：
  - 面向法律从业者、law firms、in-house teams 和其他相关组织
  - 明确列出 legal research、document drafting、contract review、matter / case management 等使用场景
  - 强调人类验证、专业责任、保密和工具尽调
  - 官方链接：https://www.mlaw.gov.sg/files/Guide_for_using_Generative_AI_in_the_Legal_Sector__Published_on_6_Mar_2026_.pdf
- Singapore Courts《Guide on the Use of Generative AI Tools by Court Users》：
  - 使用者仍须对提交内容、法律依据、引文、引述和事实负责
  - 官方链接：https://www.judiciary.gov.sg/docs/default-source/news-and-resources-docs/guide-on-the-use-of-generative-ai-tools-by-court-users.pdf?sfvrsn=3900c814_1
- Ministry of Law / Legal Technology Platform with Copilot：
  - 说明新加坡 law firms 已有更贴近真实工作流的 legaltech 进入路径
  - 官方链接：https://www.mlaw.gov.sg/enhanced-productivity-for-law-firms-in-singapore-with-the-legal-technology-platform/
- Singapore Academy of Law / LawNet AI and GPT-Legal：
  - 说明新加坡法域的 AI 检索和 source-grounded 入口已经进入真实使用场景
  - 官方链接：https://sal.org.sg/articles/singapore-academy-of-law-signs-global-content-partnerships-to-expand-worldwide-access-of-singapore-law-and-unveils-ai-powered-lawnet-4-0-at-techlaw-fest-2025/

香港：

- PCPD《Artificial Intelligence: Model Personal Data Protection Framework》
  - 官方链接：https://www.pcpd.org.hk/english/resources_centre/publications/files/ai_protection_framework.pdf
- PCPD《Checklist on Guidelines for the Use of Generative AI by Employees》
  - 官方链接：https://www.pcpd.org.hk/english/resources_centre/publications/files/guidelines_ai_employees.pdf
- Hong Kong Judiciary《Guidelines on the Use of Generative Artificial Intelligence》
  - 官方链接：https://www.judiciary.hk/doc/en/court_services_facilities/guidelines_on_the_use_of_generative_ai.pdf

## 9. 最终判断

如果中国之后只选一个近邻法域继续扩张，我会先选**新加坡**。

如果在新加坡只选两个高价值场景起步，我的建议是：

- **先做：Singapore-law Legal RAG / citation-safe drafting**
- **再做：企业合同 / matter workflow copilot**

原因不是新加坡风险更低，而是：

- 法律行业使用边界更清楚
- 法院用户责任边界更明确
- legaltech 基础设施更成熟
- 更适合把产品限定在**专业人士内部、source-grounded、可审计、可人工签发**的服务模式

香港仍值得继续做，但以本轮看到的官方材料结构，更适合放在新加坡之后，作为第二阶段扩张法域。
