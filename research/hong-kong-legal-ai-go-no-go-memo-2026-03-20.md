# 香港法域法律 AI go / no-go 决策备忘录

日期：2026-03-20

目的：基于现有《法律 LLM / AI 与法律交叉调研》《法律 AI 机会 / 风险矩阵（可执行版）》以及新加坡与香港的对比段落，补一份**香港单独法域**的 go / no-go 备忘录，避免香港继续只作为比较段落存在。本备忘录聚焦 2 个更适合香港起步的高价值法律 AI 场景，明确目标用户、服务模式、合规边界、必要 safeguard、证据缺口和进入优先级。

这不是法律意见，而是 `2026-03-20` 的产品、合规和市场进入研究快照。

## 1. 结论先行

- 目标司法辖区：**香港**
- 评估场景 1：**企业内法律 / 合规 copilot**
- 评估场景 2：**香港法双语 Legal RAG / citation-aware drafting**
- 总体建议：
  - 场景 1：**GO（P0）**
  - 场景 2：**CONDITIONAL GO（P1）**
- 当前明确不建议优先切入：
  - **面向公众的开放式法律意见 bot**
  - **直接进入法院提交链路或诉讼材料定稿链路的自动化工具**

一句话判断：

- 如果把香港第一站产品定义为**企业内、可审计、强权限控制、强人工复核**的法律 / 合规工作流工具，可以推进。
- 如果把香港第一站产品定义为**对公众直接给法律结论**，或**替代律师 / 法务直接完成法院或正式法律分析**，不应推进。

## 2. 为什么香港值得单独做一份 memo

香港并不是“风险更低”的法域，但它有三层值得单独判断的结构：

- **AI / 隐私治理框架相对明确**：
  - PCPD 已经发布 `AI: Model Personal Data Protection Framework`
  - PCPD 之后又发布员工使用生成式 AI 的清单式指南
  - 说明香港对组织内部使用 AI 的治理重点，已经聚焦到风险评估、人类监督、允许输入什么、输出如何留存、如何做 incident response
- **法律行业数字化和 LawTech 推动是真实存在的**：
  - DoJ 已把 LawTech（包括 AI / Gen AI）写进正式政策推动文件
  - DoJ 还把 `Legal Knowledge Engineers` 纳入人才清单，说明法律科技与 AI 已经被当成法律服务能力建设的一部分
- **法院链路反而给了更强的“不要过早外扩”信号**：
  - 香港 Judiciary 的第一套生成式 AI 指南是给 judges、judicial officers 和 support staff 的
  - 其中明确写到：如果没有已证明的 confidential / restricted / private information 保护能力和足够的核验机制，使用 generative AI 做 legal analysis **不推荐**

这三点合起来意味着：

- 香港很适合先做**组织内部工具**
- 但不适合把第一站押在**对外法律意见**或**court-facing automation**

## 3. 目标用户与服务模式

### 场景 1：企业内法律 / 合规 copilot

目标用户：

- 大中型企业法务团队
- 合规团队
- 金融、保险、平台、医疗、零售、物流等强监管行业的区域合规或业务法务团队
- 有跨境合同、双语材料和内部政策映射需求的团队

建议服务模式：

- **企业内闭环辅助工具**
- 优先 `tenant-isolated SaaS`、专属实例、VPC 或其他强隔离部署
- 只做条款比对、风险提示、义务映射、政策一致性检查、审批前预筛查
- 不做自动审批，不做自动对外签发

### 场景 2：香港法双语 Legal RAG / citation-aware drafting

目标用户：

- 律所研究 / 起草团队
- 企业法务研究与知识管理团队
- 仲裁 / 争议解决支持团队

建议服务模式：

- **专业人士内部 research / drafting assistant**
- 默认“先检索、再生成”
- 每次输出都带来源、日期、法域和引用
- 优先做内部 research memo、法规 / 判例检索、双语摘要和 citation-aware drafting

## 4. 决策摘要

| 场景 | 决策 | 进入优先级 | 推荐服务模式 | 当前不建议的做法 |
| --- | --- | --- | --- | --- |
| 企业内法律 / 合规 copilot | GO | P0 | 企业内、受控、可审计的 workflow copilot，先服务企业法务 / 合规团队 | 自动审批；面向公众开放；跨客户 / 跨 matter 混用数据；默认共享训练 |
| 香港法双语 Legal RAG / citation-aware drafting | CONDITIONAL GO | P1 | 专业人士内部 research / drafting assistant，必须带来源和人工复核 | 无来源裸答；对公众输出个案化法律意见；未经强复核直接用于法院 / 正式法律分析 |

## 5. 场景 1：企业内法律 / 合规 copilot

### 5.1 为什么是 GO

这是我认为香港最适合作为第一落地场景的原因：

- PCPD 的 `Model Framework` 和员工使用 GenAI 指南，都更像是在告诉组织**如何受控使用 AI**，而不是鼓励开放式对外输出。
- DoJ 的 `Promoting LawTech` paper 说明，香港政府正在推动法律和争议解决行业采用 LawTech，包括 AI / Gen AI，并计划继续补 ethical 和 security 指南。
- 香港企业法务和合规场景天然更容易放进：
  - 权限管理
  - 日志留存
  - 人工复核
  - 双语文件处理
  - 采购与信息安全审查

换句话说，香港现阶段更适合做**in-house legal / compliance software with AI controls**，而不是面向公众的“法律答案机器人”。

### 5.2 合规边界

可以做：

- 合同 intake 和 triage
- 条款提取、模板比对、红线提示
- 内部政策与监管义务映射
- 审批前预筛查
- 双语合同摘要和结构化要点提取

不要做：

- 自动批准高风险合同
- 自动给客户 / 业务方形成正式法律结论
- 把客户材料默认输入开放公众模型
- 用同一共享上下文处理多个客户或多个敏感 matter

### 5.3 必要 safeguard

- 部署与数据：
  - tenant isolation
  - matter / document / business-unit 级权限控制
  - retention、deletion、training、sub-processor 条款清晰
- 输出与流程：
  - 风险提示可回链到条款、模板、政策或规则来源
  - 高风险项目必须进入人工 review queue
  - 输出明确标记为内部辅助结果，而非最终签发文本
- 组织治理：
  - 内部 AI policy
  - permitted tools list
  - incident response
  - 员工培训与反馈机制

### 5.4 证据缺口

- 香港客户到底更偏好：
  - tenant-isolated SaaS
  - 专属实例
  - VPC
  - 本地 hosting
- 至少 3 家目标客户访谈：
  - 企业法务
  - 合规团队
  - 强监管行业业务 owner
- 一套香港场景 benchmark：
  - 双语条款抽取
  - 风险提示
  - 义务映射
  - 升级命中率

### 5.5 go / no-go 触发条件

保持 GO 的条件：

- 能明确限制为企业内工具
- 有强权限隔离和日志方案
- 高风险输出必须人工复核
- 供应商条款能说清 retention / deletion / training

转为 NO-GO 的条件：

- 客户要求自动审批
- 无法做租户或 matter 隔离
- 供应商默认保留或再训练客户数据
- 无法交代 incident response 和 data handling policy

## 6. 场景 2：香港法双语 Legal RAG / citation-aware drafting

### 6.1 为什么是 CONDITIONAL GO

这个场景价值很高，但我把它放在 `P1` 而不是 `P0`，原因不是商业价值不足，而是香港目前给出的官方信号更偏“审慎采用”：

- 香港 Judiciary 的 AI 指南明确提示：
  - generative AI chatbots 受日期范围、法域覆盖和可访问法律材料类型限制
  - 如果没有 proven confidentiality protection 和足够核验机制，using generative AI for legal analysis **is not recommended**
- Law Society 的 AI position paper 明确强调：
  - hallucinations 风险
  - data protection / data governance
  - transparency / disclosure
  - proper human oversight

这意味着香港法 Legal RAG 不是不能做，而是必须做成：

- **source-grounded**
- **bilingual aware**
- **human-reviewed**
- **not court-ready by default**

### 6.2 合规边界

可以做：

- 香港法规、判例、practice materials 的检索增强问答
- 内部 research memo 草稿
- 双语摘要、翻译辅助、citation-aware drafting
- 监管更新监测和知识管理

不要做：

- 对公众输出个案化法律意见
- 无来源裸答
- 未经律师 / 法务核验直接用于法院、仲裁或正式外部法律分析
- 把模型输出包装成“完整 legal analysis substitute”

### 6.3 必要 safeguard

- 检索与引用：
  - source pinning
  - 日期过滤
  - 法域过滤
  - citation verifier
- 数据与权限：
  - confidential / privileged / restricted information 不进未批准工具
  - 按 matter / client 做隔离
- 输出控制：
  - draft / internal use 标记
  - 不支持无来源输出
  - 高风险问题走升级或拒答
- 人工复核：
  - 研究 memo、客户交付件、仲裁 / 法院材料必须人工签发

### 6.4 证据缺口

- 一套香港法专用评测集：
  - 引用准确率
  - 过期 / 失效材料识别
  - bilingual retrieval
  - jurisdiction mix-up 错误率
- 语料策略：
  - primary law
  - case law
  - regulatory materials
  - practice materials
  - 中英双语覆盖
- 用户证据：
  - 律师 / 法务是否真的点击来源
  - 双语呈现是否真有提效
  - 输出是否能被接受为“draft aid”而非“final answer”

### 6.5 go / no-go 触发条件

保持 CONDITIONAL GO 的条件：

- 输出稳定回链来源
- 有 citation 和 date filter
- confidential 数据不进开放工具
- 所有正式对外交付都保留人工签发

转为 NO-GO 的条件：

- 只能做无来源裸答
- 无法说明语料来源和更新机制
- 用户坚持把输出当成最终法律分析
- 产品被要求直接进入法院 / 仲裁提交链路

## 7. 香港法域下的统一 no-go 边界

当前阶段，不建议优先做：

- 面向公众的开放式法律意见 bot
- 直接进入法院提交链路的自动化工具
- 未经强复核的 litigation / arbitration drafting automation
- 默认把客户 / matter 数据送入开放公众模型

原因不是“香港不能做 legal AI”，而是：

- 官方材料当前更支持**受控组织内部使用**
- 法院侧已经给出“legal analysis 不宜轻率交给 GenAI”的明确信号
- Law Society 的已有材料也把 human oversight、transparency、data governance 放在核心位置

## 8. 如果从香港内部进入顺序来排，我会这样做

1. **企业内法律 / 合规 copilot**
2. **香港法双语 Legal RAG / citation-aware drafting**
3. **双语文档摘要 / 翻译辅助**
4. **争议解决前置 research assistant**

最后才考虑：

- 面向公众的法律问答
- 法院 / 仲裁提交链路自动化

## 9. 本备忘录依赖的当前规则和市场锚点

香港：

- PCPD《Artificial Intelligence: Model Personal Data Protection Framework》
  - 强调 risk assessment、human oversight、customisation and AI model management、communication and engagement
  - 官方链接：https://www.pcpd.org.hk/english/resources_centre/publications/files/ai_protection_framework.pdf
- PCPD《Checklist on Guidelines for the Use of Generative AI by Employees》
  - 要求组织明确 permitted tools、input / output 边界、lawful and ethical use、bias prevention、data security、incident response、training 和 feedback mechanism
  - 官方链接：https://www.pcpd.org.hk/english/resources_centre/publications/files/guidelines_ai_employees.pdf
- PCPD `2025-05-08` AI compliance checks
  - 说明 PCPD 已对 `60` 家机构开展 AI 相关 compliance checks，不是只停留在原则性倡议
  - 官方链接：https://www.pcpd.org.hk/english/news_events/media_statements/press_20250508.html
- Hong Kong Judiciary《Guidelines on the Use of Generative Artificial Intelligence》
  - 明确指出如无 proven confidentiality protection 和 adequate checking / verification mechanism，using generative AI for legal analysis is not recommended
  - 官方链接：https://www.judiciary.hk/doc/en/court_services_facilities/guidelines_on_the_use_of_generative_ai.pdf
- DoJ《Promoting LawTech》
  - 说明香港政府正推动 legal and dispute resolution sector 采用 LawTech（包括 AI / Gen AI），并计划补 ethical 与 security 指南
  - 官方链接：https://www.doj.gov.hk/en/legco/pdf/ajls20250602e1.pdf
- DoJ `2025-05-07` press release
  - 说明 `Legal Knowledge Engineers` 已被纳入人才清单，反映香港对法律 AI / legaltech 能力建设的政策支持
  - 官方链接：https://www.doj.gov.hk/en/community_engagement/press/20250507_pr1.html
- The Law Society of Hong Kong《The Impact of Artificial Intelligence on the Legal Profession》
  - 强调 hallucination、data protection、data governance、transparency、disclosure 和 human oversight
  - 官方链接：https://www.hklawsoc.org.hk/-/media/HKLS/Home/News/2024/LSHK-Position-Paper_AI_EN.pdf

## 10. 最终判断

如果现在要决定“香港能不能作为法律 AI 的单独扩张法域进入”，我的判断是：

- **能做**
- **但先做企业内、可审计、强权限控制、强人工复核的工具**
- **不把香港第一站押在公众法律意见或法院链路自动化上**

更具体一点：

- 第一优先级：**企业内法律 / 合规 copilot**
- 第二优先级：**香港法双语 Legal RAG / citation-aware drafting**

如果这两类场景能做到：

- secure deployment
- source-grounded output
- human sign-off
- clear data handling policy

那么香港值得作为新加坡之后的下一阶段法域推进。
