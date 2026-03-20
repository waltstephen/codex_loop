# 香港法律 AI 管理层决策 brief

日期：2026-03-20

适用对象：管理层、产品负责人、法务负责人、合规负责人、安全负责人

目的：把现有 `research/` 研究包压缩成一份 1-2 页管理层 brief，聚焦**香港法域**的首轮进入判断，明确目标客户、服务模式、go / no-go gate、必要 safeguards、证据缺口、停机条件与未来 90 天监测触发器。

这不是法律意见，而是 `2026-03-20` 的产品、合规和市场进入研究快照。

## 1. 一句话结论

建议：**可以推进香港法域，但第一站只做企业内法律 / 合规 copilot，记为 `GO（P0）`。**

同时保留一个受限的第二优先级：

- **香港法双语 Legal RAG / citation-aware drafting：`CONDITIONAL GO（P1）`**

当前明确不建议推进：

- 面向公众的开放式法律意见 bot
- 直接进入法院 / 仲裁提交链路的自动化工具
- 未经强复核的 litigation / arbitration drafting automation

如果这些边界守不住，应转 `NO-GO` 或至少 `HOLD`。

## 2. 为什么香港值得做，但不能激进做

管理层层面的核心逻辑：

- **治理信号明确**：`PCPD` 的 AI / 隐私治理框架和员工使用 GenAI 指南，都更支持组织内部、可审计、有人类监督的采用方式。
- **政策推动真实存在**：`DoJ` 已把 LawTech 和 AI 纳入正式推动路径，说明香港不是“完全没有市场基础设施”的观察名单。
- **法院边界反而更保守**：`Judiciary` 已明确给出对 legal analysis 的谨慎信号，不适合把香港第一站押在 court-facing automation 上。
- **市场切口更现实**：企业法务 / 合规团队、双语文档和跨境流程，是更容易落进权限、日志、人工签发和采购审查体系的场景。

所以，香港适合做的是：

- 企业内、可审计、强权限控制、强人工复核的工具

而不是：

- 对公众直接给法律结论
- 替代律师 / 法务做最终法律分析
- 直接进入法院 / 仲裁提交链路

## 3. 目标客户与服务模式

### 3.1 目标客户

优先客户：

- 大中型企业法务团队
- 合规团队
- 金融、保险、平台、医疗、零售、物流等强监管行业的区域法务 / 合规团队
- 有双语材料、跨境合同和内部政策映射需求的团队

### 3.2 推荐服务模式

| 项目 | 建议 |
| --- | --- |
| 首发场景 | 企业内法律 / 合规 copilot |
| 第二阶段场景 | 香港法双语 Legal RAG / citation-aware drafting |
| 产品定位 | 企业内闭环辅助工具 / 专业人士内部 research assistant |
| 部署方式 | `tenant-isolated SaaS`、专属实例、`VPC` 或其他强隔离部署 |
| 首阶段范围 | 条款比对、风险提示、义务映射、审批前预筛查、双语摘要 |
| 输出定位 | 风险提示、候选 redline、内部 research / drafting 草稿 |
| 人机边界 | 人工最终确认；不自动审批；不自动对外签发；不默认 court-ready |

## 4. go / no-go gate

| Gate | 管理层要问的问题 | 必须具备 | 不满足时的处理 |
| --- | --- | --- | --- |
| Gate 0：场景边界 | 这是企业内受控工具，而不是公众法律服务吗？ | 明确目标团队、明确使用边界、客户接受人工签发 | 不推进 |
| Gate 1：部署 / 数据 | 能否说清部署、权限、日志、retention / deletion / training policy？ | 强隔离部署、matter / document 级权限、数据处理条款清晰 | 不进真实数据或不进采购 |
| Gate 2：输出 / 控制 | 输出能否回链来源，且高风险问题可升级或拒答？ | source-grounded output、review queue、human sign-off | 不开 pilot；保持离线验证 |
| Gate 3：pilot 证据 | 有没有访谈、benchmark、失败用例和真实使用反馈？ | 客户访谈、香港法评测集、失败用例库、日志抽查 | 缩 scope 或转 `HOLD` |
| Gate 4：扩张判断 | 是否仍是 internal-only 模式，且没有滑向法院 / 公众服务边界？ | 内部工具定位稳定、控制可复用、监测项无重大变化 | 不扩张；保持试点或转 `NO-GO` |

## 5. 必须守住的最低 safeguards

| 控制域 | 最低要求 |
| --- | --- |
| 部署 | `tenant isolation`、专属实例 / `VPC` 或其他强隔离方案 |
| 权限 | matter / client / document / business-unit 级权限控制 |
| 数据 | confidential / privileged / restricted information 不进未批准工具 |
| 日志与治理 | 保留访问、输出、review、导出日志；有 incident response 和 permitted tools list |
| 输出 | 不支持无来源裸答；高风险问题必须升级、拒答或进入人工 review queue |
| 引用与更新 | `source pinning`、date filter、jurisdiction filter、citation verifier |
| 人机边界 | 客户交付件、正式法律分析、法院 / 仲裁材料必须人工签发 |
| 供应商治理 | retention、deletion、training、sub-processor 条款清晰 |

## 6. 当前证据缺口

管理层当前还缺的，不是更多概念，而是下面几类证据：

- **客户访谈**：至少 3 家目标客户，确认部署偏好、采购关切、人工签发边界和双语工作流真实需求。
- **评测集**：一套香港法专用评测集，覆盖引用准确率、过期 / 失效材料识别、bilingual retrieval、jurisdiction mix-up 错误率。
- **语料策略**：primary law、case law、regulatory materials、practice materials 的中英双语覆盖和更新机制。
- **使用证据**：律师 / 法务是否真的点击来源、是否接受输出只是 draft aid、双语呈现是否带来真实提效。

## 7. 立即停机条件

出现以下任一情况，应立即暂停、降级或转 `NO-GO`：

- 产品被要求转成面向公众的法律意见服务
- 产品被要求直接进入法院 / 仲裁提交链路
- 无法说明或执行 retention、deletion、training、sub-processor、日志策略
- confidential 数据被送入未批准工具
- 输出无法稳定回链来源
- 用户持续把输出当成最终法律分析而非辅助建议
- 客户要求系统直接自动批准高风险合同或直接生成可提交的最终材料

## 8. 未来 90 天监测触发器

未来 90 天，管理层最值得盯的不是所有新闻，而是这些会改结论的触发器：

| 触发器 | 为什么重要 | 触发后动作 |
| --- | --- | --- |
| `PCPD` 发布新的正式 AI / 隐私治理指引、FAQ 或模板 | 会直接改变组织控制、permitted tools、incident response、input / output 边界 | 复核 minimum safeguards、客户条款和部署方案 |
| `PCPD` 的 AI compliance checks 或执法表述命中 data handling / retention / governance 问题 | 会直接影响产品售前禁区和 stop conditions | 更新 stop conditions、数据处理表述和销售边界 |
| `Judiciary` 把 AI guidance 延伸到 court users、提交材料、disclosure 或 sanctions | 会直接影响香港法 Legal RAG 的 `P1` 可做边界 | 复核 `CONDITIONAL GO` 是否仍成立；必要时转 `HOLD` |
| `DoJ` 的 LawTech / AI 推动明显扩大或收紧 | 会改变香港作为扩张法域的进入顺序和服务模式 | 更新香港优先级和目标客户 |
| `Law Society` 发布更正式的 AI 使用规范 | 会抬高 disclosure、supervision、training、human oversight 要求 | 更新 professional-internal 边界和客户沟通要求 |
| 代表性案件或司法公开表态改变 court-facing 风险判断 | 会改变“not court-ready by default”的核心假设 | 复核统一 no-go 边界和 verifier controls |

## 9. 当前管理层建议

如果现在要决定“香港能不能作为法律 AI 的单独扩张法域推进”，我的建议是：

- **能做**
- **但先做企业内法律 / 合规 copilot**
- **并且必须限定为可审计、强权限控制、强人工复核的 internal-only 服务模式**

更直接一点：

- 把香港当成“企业内法律 / 合规软件 + AI 辅助工作流工具”，可以推进。
- 把香港当成“公众法律意见服务或法院链路自动化”的起点，不应推进。

第二阶段才考虑：

- 香港法双语 Legal RAG / citation-aware drafting

前提是：

- source-grounded output 稳定
- human sign-off 能落实
- data handling policy 说得清
- 监测 tracker 没有触发足以改结论的重大变化
