# 法律 AI 监管监测清单（中国 / 新加坡 / 香港 / 英格兰及威尔士）

日期：2026-03-20

目的：基于现有 `research/` 研究包，为**中国、新加坡、香港、英格兰及威尔士**建立一份可执行的法规、执法、判例、法院规则与律师伦理意见监测清单，明确监测对象、刷新频率、触发阈值、责任人和结论更新流程。

适用范围：

- `/home/v-boxiuli/PPT/ArgusBot/research/china-legal-ai-go-no-go-memo-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/china-contract-compliance-copilot-management-memo-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/china-contract-compliance-copilot-ops-checklist-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/china-contract-compliance-copilot-management-brief-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/hong-kong-legal-ai-management-brief-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/hong-kong-legal-ai-go-no-go-memo-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/singapore-legal-ai-go-no-go-memo-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/uk-australia-uae-legal-ai-market-comparison-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/court-facing-ai-rules-sanction-risk-tracker-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/legal-ai-opportunity-risk-matrix-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/legal-llm-law-intersections-2026-03-20.md`
- `/home/v-boxiuli/PPT/ArgusBot/research/legal-ai-research-package-register-2026-03-20.md`

这不是法律意见，而是 `2026-03-20` 的研究运营文档。

## 1. 使用方式

这份 tracker 不是“把所有新闻都收进来”，而是只盯会改变 go / no-go 结论、最低 safeguards、市场进入顺序或 pilot 边界的变化。

统一责任角色：

- `Research owner`：负责每周监测、首轮归类、更新 tracker
- `Legal / compliance owner`：负责判断是否改变合规边界或最低控制要求
- `Product owner`：负责判断是否改变服务模式、默认功能和 stop conditions
- `Market / GTM owner`：负责判断是否改变目标客户、首批法域或对外表述

owner-of-record（总包级）：

| 范围 | primary owner of record | secondary owner | 最低留痕 |
| --- | --- | --- | --- |
| 本 tracker 周度维护 | `Research owner` | `Legal / compliance owner` | 每周至少一条 dated update 或 no-change 记录 |
| 中国法域边界判断 | `Legal / compliance owner` | `Research owner + Product owner` | 命中 `L2 / L3` 时同步回写中国 memo 家族 |
| 市场进入顺序与对外表述 | `Market / GTM owner` | `Product owner + Research owner` | 影响法域优先级时回写矩阵和总览 |
| 仓库 / 知识库登记同步 | `Research owner` | `Product owner` | `L2 / L3` 事件与月度汇总同步到 `legal-ai-research-package-register-2026-03-20` |

统一刷新节奏：

- `每周`：法规公告、监管执法、法院公告、职业团体更新
- `每月`：判例扫描、研究包结论回看、监测项去重
- `每季度`：对相关 memo / matrix 做一次全量刷新判断

## 2. 统一触发等级

| 等级 | 含义 | 典型触发 | 默认动作 |
| --- | --- | --- | --- |
| L1：记录 | 有新材料，但暂不改变边界 | 新演讲、新非约束性说明、同方向重复公告 | 记录到 tracker，月度汇总 |
| L2：重看 | 可能改变某个控制项或优先级 | 新指引、咨询文件、法院新 circular、行业组织新 AI 指引、单个代表性案件 | `5` 个工作日内补分析；`10` 个工作日内决定是否改 memo |
| L3：立即更新 | 已足以改变现有 go / no-go 或上线边界 | 新法 / 新规生效、正式 practice direction、监管处罚、备案 / 登记要求变化、明确纪律处分或高位阶判例 | `48` 小时内发起专项复核；必要时先把相关场景打到 `HOLD` |

## 3. 中国法域监测清单

当前研究包中，中国法域最敏感的是：企业内工具与面向境内公众服务的边界、标识义务、备案 / 登记口径、个人信息与日志处理、以及涉 AI 司法裁判规则。就 court-facing 风险而言，`2026-03-20` 本轮刷新看到的中国侧官方材料仍以**法院内部 AI 应用规范、智能审判 / 诉讼服务建设和涉 AI 裁判规则来源**为主，而不是单独全国 court-user filing / disclosure guide。

对中国 court-facing 监测，默认再加一条分层规则：

- 法院内部 AI 应用 / 建设材料：默认按 `L1` 记录，不改变“不直接进入法院提交链路”的边界
- 面向诉讼参与人或律师的立案 / 提交 / 核验 / 说明要求：默认按 `L2` 处理，补影响分析
- 全国性或高位阶的 court-user filing / disclosure / certification 规则，或代表性 sanctions case：默认按 `L3` 处理并专项复核

| 监测条线 | 主要来源 | 盯什么 | 刷新频率 | 触发阈值 | 责任人 | 触发后要改什么 |
| --- | --- | --- | --- | --- | --- | --- |
| 法规与部门规章 | 国家网信办、工信部、中国政府网、全国人大网 | 《生成式人工智能服务管理暂行办法》、`PIPL`、新 AI 立法草案、相关配套规则 | 每周 | 任何影响“是否属于面向境内公众服务”的新解释，或任何影响输入、日志、训练数据、删除义务的新规则 | Research owner + Legal / compliance owner | 更新中国 memo 的统一 no-go 边界、部署和数据条款 |
| 标识与传播治理 | 国家网信办、中国政府网 | 《人工智能生成合成内容标识办法》、配套标准、导出 / 元数据 / 协议 / 平台核验要求 | 每周 | 新的强制标准、执法通报、平台侧核验要求收紧 | Legal / compliance owner + Product owner | 更新中国 memo、ops checklist、management brief 的标识、导出、日志要求 |
| 备案 / 登记与产品边界 | 国家网信办备案 / 登记公告 | 备案数量、登记口径、显著位置公示要求、API 调用应用的登记要求 | 每周 | 出现新的备案 / 登记适用口径，或现有企业内工具可能被重新归入备案 / 登记范围 | Legal / compliance owner + Market / GTM owner | 复核中国场景仍是否保持 `企业内闭环工具` 定位 |
| 执法与处罚 | 国家网信办、地方网信办、工信系统 | 针对标识、备案、个人信息、内容治理的执法通报 | 每周 | 任一处罚直接命中当前产品控制域，例如标识、导出、日志、用户声明、输入信息留存 | Legal / compliance owner | 更新 safeguards、停机条件和售前禁区 |
| 判例与司法政策 | 最高人民法院、最高法知识产权法庭、互联网法院公开渠道 | 训练数据版权、平台责任、AI 生成内容标识、AI 生成物保护、平台注意义务 | 每月 | 出现能重写平台责任边界、训练数据合法性判断或输出责任边界的代表性案件 / 政策文件 | Research owner + Legal / compliance owner | 更新总览文档、矩阵、中国 memo 的规则锚点 |
| 法院 / 公共法律服务规则 | 最高人民法院、法信、地方法院、司法行政系统、`12348` 中国法律服务网 | 法院是否发布 AI 提交 / 审核 / 辅助办案规则；公共法律服务 AI 使用边界；`12348` 或地方公共法律服务体系是否开始对 AI 助手、智能问答、拟人化互动或用户说明义务给出专门规则 | 每月 | 出现正式 court-facing 或 public-facing AI 规则，影响当前“不直接进入法院提交链路”的结论 | Legal / compliance owner + Product owner | 复核中国场景进入顺序和统一 no-go 边界 |
| 律师行业伦理与处分 | 司法部律师工作条线、中华全国律师协会、地方律协 | 律师使用 AI 的业务指引、纪律处分、保密与执业边界提示，以及在 `CAC` 专业领域条款出现后是否跟进发布法律服务领域 AI 规范 | 每月 | 发布全国性律师 AI 指引，或出现具有示范效应的处分 / 通报 | Legal / compliance owner | 更新中国 memo 的人工复核、签发和培训要求 |

建议的中国重点源清单：

- `https://www.miit.gov.cn/zcfg/qtl/art/2023/art_f4e8f71ae1dc43b0980b962907b7738f.html`
- `https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm`
- `https://www.cac.gov.cn/2025-03/14/c_1743654685896173.htm`
- `https://www.cac.gov.cn/2026-01/09/c_1769688009588554.htm`
- `https://www.cac.gov.cn/2025-11/25/c_1765795550841819.htm`
- `https://www.cac.gov.cn/2025-12/27/c_1768571207311996.htm`
- `https://www.cma.gov.cn/zfxxgk/zc/gz/202504/W020250429613208378185.pdf`
- `https://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html`
- `https://www.court.gov.cn/zixun/xiangqing/382461.html`
- `https://www.court.gov.cn/zixun/xiangqing/447711.html`
- `https://www.court.gov.cn/`
- `https://ipc.court.gov.cn/`
- `https://www.moj.gov.cn/fzgz/fzgzggflfwx/fzgzlsgz/`
- `https://www.moj.gov.cn/fzgz/fzgzggflfwx/fzgzggflfw/`
- `https://www.moj.gov.cn/pub/sfbgw/fzgz/fzgzggflfwx/fzgzlsgz/202505/t20250515_519403.html`
- `https://www.moj.gov.cn/pub/sfbgw/fzgz/fzgzggflfwx/fzgzggflfw/202509/t20250910_524914.html`
- `https://www.moj.gov.cn/pub/sfbgwapp/fzgzapp/ggfzfwapp/lsgzapp/202601/t20260129_531169.html`
- `https://www.moj.gov.cn/pub/sfbgwapp/fzgzapp/ggfzfwapp/ggfzfwapp2/202503/t20250321_516166.html`
- `https://www.12348.gov.cn/`
- `https://www.acla.org.cn/`

其中，`2026-01-09` 的 `CAC` 公告默认作为备案 / 登记锚点，`2025-11-25` 的 `CAC` 通报默认作为标识执法锚点，`2025-12-27` 的 `CAC` 拟人化互动服务管理征求意见稿默认作为**拟人化互动 / 专业领域附加义务**锚点；如果后续问题落到法律服务行业自身规范，默认再补扫 `司法部律师工作条线`、`司法部公共法律服务条线`、`12348` 与 `中华全国律师协会`。

如 `司法部` 两个法律服务栏目根路径继续自循环重定向，默认仍先记录根路径的 `source access` 状态，再按同域 fallback official page 使用顺序补扫：

- `司法部律师工作条线`：优先使用 `https://www.moj.gov.cn/pub/sfbgw/fzgz/fzgzggflfwx/fzgzlsgz/YYYYMM/tYYYYMMDD_*.html` 这一 article-page family
- `司法部公共法律服务条线`：优先使用 `https://www.moj.gov.cn/pub/sfbgw/fzgz/fzgzggflfwx/fzgzggflfw/YYYYMM/tYYYYMMDD_*.html` 这一 article-page family
- 如 `pub/sfbgw/...` article-page family 也无法直接定位或仍然抓取失败，再补扫同域 `pub/sfbgwapp/...` article-page family
- 如以上 `MOJ` 根路径与两类 article-page family 在自动抓取中都仍失败，必须把该锚点记为 `source unavailable (automation)`，并安排人工浏览器复核同域官方页面；在人工复核完成前不得写成“已完成 no-change”
- 如仍未拿到可复核的同域官方页面，再补记同域站内检索结果页或主管部门首页下的同主题官方页面

首次中国 dated update 的最小官方锚点见 section `11.1`，后续每次中国 `L1 / L2 / L3` 更新至少应回链到其中一项或新增同级别官方源。

## 4. 新加坡法域监测清单

当前研究包中，新加坡法域最敏感的是：法律行业 GenAI 指南是否更新、法院用户规则是否变化、专业责任与 disclosure 边界是否收紧，以及 secure tool / client confidentiality / auditability 的要求是否变化。

| 监测条线 | 主要来源 | 盯什么 | 刷新频率 | 触发阈值 | 责任人 | 触发后要改什么 |
| --- | --- | --- | --- | --- | --- | --- |
| 法律行业指导 | Ministry of Law | `Guide for Using Generative AI in the Legal Sector` 的更新、附录和案例扩充、风险分级和 due diligence 变化 | 每周 | 最终版更新，或新增与 confidentiality、tool due diligence、client disclosure、human oversight 直接相关的要求 | Research owner + Legal / compliance owner | 更新新加坡 memo 的 safeguards、evidence gaps、服务模式 |
| 法院规则与 circulars | Singapore Courts、Supreme Court、State Courts、Family Justice Courts | `Guide on the Use of Generative AI Tools by Court Users`、Registrar’s Circular、提交材料验证和 disclosure 要求 | 每周 | 法院改为强制披露、强制 affidavit、禁止某类 AI 使用，或新增 sanctions / costs 风险说明 | Legal / compliance owner + Product owner | 复核 Legal RAG / drafting 是否仍是 `GO (P0)` |
| 律师伦理 / 专业行为 | MinLaw 指南中对 PCR / SCCA Code 的引用，Law Society / SAL 正式资源 | competence、confidentiality、honesty、client disclosure、opt-out、approved tools | 每月 | 发布新的正式行业指引、协会正式 AI 使用规范，或对 existing guide 的重大修订 | Legal / compliance owner | 更新新加坡 memo 的 professional-internal 边界和客户条款 |
| 判例与 sanctions | Singapore Courts judgments、法院通报 | AI citation、hallucination、confidentiality breach、court submission verification 的案件 | 每月 | 出现代表性判例或 sanctions，明确律师 / court user 在 AI 使用上的责任后果 | Research owner + Legal / compliance owner | 更新新加坡 memo 的 no-go 边界和 stop conditions |
| 行业基础设施与实际落地 | MinLaw、SAL、LawNet / LTP 官方发布 | LawNet AI、LTP + Copilot、行业 adoption 项目、secure legal workflow infrastructure | 每月 | 官方基础设施调整导致市场进入方式发生变化，例如 secure tool 路线明显加强或收缩 | Product owner + Market / GTM owner | 更新进入顺序、目标客户和部署建议 |

建议的新加坡重点源清单：

- `https://www.mlaw.gov.sg/files/Guide_for_using_Generative_AI_in_the_Legal_Sector__Published_on_6_Mar_2026_.pdf`
- `https://www.judiciary.gov.sg/docs/default-source/news-and-resources-docs/guide-on-the-use-of-generative-ai-tools-by-court-users.pdf?sfvrsn=3900c814_1`
- `https://www.mlaw.gov.sg/driving-the-next-stage-of-digitalisation-through-lift/`
- `https://www.mlaw.gov.sg/enhanced-productivity-for-law-firms-in-singapore-with-the-legal-technology-platform/`
- `https://sal.org.sg/technology/`
- `https://www.judiciary.gov.sg/`

## 5. 香港法域监测清单

当前研究包中，香港法域最敏感的是：`PCPD` 的 AI / 隐私治理框架是否升级为更具体的执行要求、`Judiciary` 是否把当前偏内部治理的 AI 指引延伸到 court-facing 使用边界、`DoJ` 的 LawTech 推动是否进入更明确的行业规范，以及 `Law Society` 是否进一步细化律师使用 AI 的 human oversight、transparency 和 data governance 要求。

| 监测条线 | 主要来源 | 盯什么 | 刷新频率 | 触发阈值 | 责任人 | 触发后要改什么 |
| --- | --- | --- | --- | --- | --- | --- |
| AI / 隐私治理框架 | PCPD | `AI: Model Personal Data Protection Framework`、员工使用 GenAI 指南、后续 FAQ / 指南 / 模板 | 每周 | 发布新的正式指引、把原则要求改成更具体的组织控制要求，或对 permitted tools、input / output、incident response 提出更高门槛 | Research owner + Legal / compliance owner | 更新香港 memo 的 minimum safeguards、部署要求和客户条款 |
| 执法与合规检查 | PCPD | AI compliance checks、调查、执法通报、行业提醒 | 每周 | 出现直接命中当前产品控制域的检查结果或执法表述，例如 data handling、employee use、retention、governance failure | Legal / compliance owner + Product owner | 更新 stop conditions、售前禁区和数据处理表述 |
| 法院规则与司法指导 | Hong Kong Judiciary | generative AI guidance、法院公告、court-facing AI 使用边界、confidentiality / verification 要求 | 每周 | `Judiciary` 把当前内部 guidance 扩展到 court users、提交材料、disclosure 或 sanctions，或新增更明确的 litigation / legal analysis 限制 | Legal / compliance owner + Product owner | 复核香港场景中 Legal RAG / drafting 是否仍保持 `CONDITIONAL GO (P1)`，并更新统一 no-go 边界 |
| 法律科技政策与市场基础设施 | DoJ | `Promoting LawTech`、`Legal Knowledge Engineers`、法律科技资助 / 人才 / 行业项目 | 每月 | 官方政策把 AI / LawTech 支持范围显著扩大或收紧，足以改变香港作为扩张法域的进入顺序 | Product owner + Market / GTM owner | 更新矩阵中的香港定位、服务模式和扩张优先级 |
| 律师伦理与专业行为 | The Law Society of Hong Kong | AI position paper、practice guidance、confidentiality、hallucination、transparency、human oversight | 每月 | 发布新的正式 AI 指引，或对 disclosure、supervision、training、client communication 的要求显著提高 | Legal / compliance owner | 更新香港 memo 的 professional-internal 边界、人工复核和客户沟通要求 |
| 判例与司法态度 | Judiciary judgments、HKLII 等公开裁判来源 | AI hallucination、citation error、confidentiality、professional competence、court misuse | 每月 | 出现足以改变 court-facing 风险判断的代表性案件或司法公开表态 | Research owner + Legal / compliance owner | 更新香港 memo 的 no-go 边界、required verifier controls 和风险描述 |

建议的香港重点源清单：

- `https://www.pcpd.org.hk/english/resources_centre/publications/files/ai_protection_framework.pdf`
- `https://www.pcpd.org.hk/english/resources_centre/publications/files/guidelines_ai_employees.pdf`
- `https://www.pcpd.org.hk/english/news_events/media_statements/press_20250508.html`
- `https://www.judiciary.hk/doc/en/court_services_facilities/guidelines_on_the_use_of_generative_ai.pdf`
- `https://www.doj.gov.hk/en/legco/pdf/ajls20250602e1.pdf`
- `https://www.doj.gov.hk/en/community_engagement/press/20250507_pr1.html`
- `https://www.hklawsoc.org.hk/-/media/HKLS/Home/News/2024/LSHK-Position-Paper_AI_EN.pdf`

## 6. 英格兰及威尔士监测清单

当前研究包中，英格兰及威尔士最敏感的是：受监管 AI 法律服务的新案例、法院对 AI court documents 的正式规则、职业团体和监管机构对 hallucination / confidentiality / supervision 的要求，以及高位阶案件是否改变“先做 professional-internal 工具”的判断。就 `2026-03-20` 本轮刷新而言，最值得盯的 live signal 是：`CJC` 的 current-work page 仍显示 eight-week consultation 正在进行，latest-news page 进一步写明截止到 `2026-04-14 23:59`，而 interim report 已经把讨论推进到更具体的 proposal，开始触及**AI 用于生成法院拟采信证据时的 declaration 义务**。

### 6.1 提前完成 `2026-03-25` 的 `CJC` `L2` 影响分析

- 当前 `CJC` signal 已足以把英格兰及威尔士的 court-facing 风险，从泛化的“AI disclosure / evidence 可能收紧”，收窄成更具体的 `evidence-stage gating` 判断。
- 按当前 consultation paper / cover sheet，最接近 future formal declaration 的是：
  - `trial witness statements`：方向是要求声明 AI 没有被用于生成、改写、加强、弱化或重述证人证据
  - `expert reports`：方向是要求识别并说明被用于报告的 AI（纯行政用途除外）
  - `skeleton arguments / advocacy documents / disclosure lists and statements`：当前反而没有 pressing case 去增加额外 court rule
- 这不会改变本包把英格兰及威尔士放在 `P0` 的 professional-internal 进入顺序，也不会放松 court-facing `NO-GO`；相反，它更明确说明任何 witness / expert evidence generation or reshaping 都应继续排除在默认产品范围之外。
- 因此本次回写需要更新 `court-facing` tracker 与 `uk-australia-uae` memo 的 evidence / disclosure 描述，但暂不改 `legal-ai-opportunity-risk-matrix`，因为法域排序与统一 go / no-go 边界未变。
- 在 `2026-04-14 23:59` consultation closing time 之前，如果 `CJC current-work`、`latest-news` 和相关 consultation / interim material 只是继续确认 consultation 仍 open、scope 仍覆盖 pleadings / witness statements / expert reports，且 evidence-stage proposal 没有实质推进，默认只记为 tracker-level `L1 no-change` status verification；除非出现新的 official material、closing-time 变化、final report / practice direction，或 proposal 明显改变当前 evidence-stage judgement，否则不重复开启新的 `L2` 回写。
- 同日 live recheck 还确认：`CJC current-work` page 当前暴露的 consultation PDF 已切换到 `/2026/03/` official path，但这只属于 source-anchor refresh，不改变上述 `L2` 判断、统一 `NO-GO` 边界或英格兰及威尔士的进入顺序。

| 监测条线 | 主要来源 | 盯什么 | 刷新频率 | 触发阈值 | 责任人 | 触发后要改什么 |
| --- | --- | --- | --- | --- | --- | --- |
| 律师监管与创新准入 | SRA | AI-driven law firm 授权、监管声明、Risk Outlook、纪律处分、consumer protection 条件 | 每周 | 新的 AI firm 授权模式、正式纪律处分、或 SRA 对 client confidentiality / supervision / insurance 的新要求 | Research owner + Legal / compliance owner | 更新英格兰及威尔士在扩张排序中的位置和可做场景 |
| 法院规则与司法指导 | Courts and Tribunals Judiciary、Civil Justice Council | `AI Judicial Guidance`、CJC current-work / latest-news / interim report / final report、practice directions、court documents 规则、AI-generated evidence declaration 走向 | 每周 | consultation 进入 final report、practice direction 生效、court filing AI disclosure 义务正式落地，或 interim proposal 明显收紧到具体 evidence / declaration 要求 | Legal / compliance owner + Product owner | 更新“不要先做 court filing automation”的边界，以及 court-facing evidence / disclosure 控制项 |
| 判例与 sanctions | Judiciary judgments、National Archives judgments | fake citations、AI misuse、professional competence、costs / contempt / referral | 每周 | 出现新的高位阶或高传播案件，足以改变对 legal research / drafting 风险的判断 | Research owner + Legal / compliance owner | 更新 memo 中的 case-law risk 和 required verifier controls |
| 律师伦理与行业指引 | Law Society、Bar Council、BSB | generative AI guidance、confidentiality、privilege、verification、court duties、training expectations | 每月 | 行业指引重大更新，或 profession-wide training / supervision expectation 被明确提高 | Legal / compliance owner | 更新 minimum safeguards、training、review requirement |
| 法院链路细分场景 | Civil / Family / Tribunal 相关官方规则 | pleadings、witness statements、expert reports、disclosure review 等子流程规则 | 每月 | 某一子流程单独发布更严格 AI 规则，例如 disclosure、expert evidence、family bundles | Product owner + Legal / compliance owner | 把英格兰及威尔士场景从泛 Legal RAG 拆成更细的 workflow gating |

建议的英格兰及威尔士重点源清单：

- `https://media.sra.org.uk/sra/news/press/garfield-ai-authorised/`
- `https://www.sra.org.uk/sra/research-publications/artificial-intelligence-legal-market/`
- `https://www.lawsociety.org.uk/Topics/AI-and-lawtech/Guides/Generative-AI-the-essentials`
- `https://www.judiciary.uk/guidance-and-resources/artificial-intelligence-ai-judicial-guidance-october-2025/`
- `https://www.judiciary.uk/related-offices-and-bodies/advisory-bodies/cjc/current-work/use-of-ai-in-preparing-court-documents/`
- `https://www.judiciary.uk/related-offices-and-bodies/advisory-bodies/cjc/latest-news/`
- `https://www.judiciary.uk/wp-content/uploads/2026/03/Interim-Report-and-Consultation-Use-of-AI-for-Preparing-Court-Docume.pdf`
- `https://www.judiciary.uk/wp-content/uploads/2025/06/Ayinde-v-London-Borough-of-Haringey-and-Al-Haroun-v-Qatar-National-Bank.pdf`
- `https://www.barcouncil.org.uk/resource/updated-guidance-on-generative-ai-for-the-bar.html`

## 7. 结论更新流程

### 7.1 周度流程

1. `Research owner` 每周固定扫一次四组法域的官方源。
2. 新材料统一按 `L1 / L2 / L3` 分级。
3. 同一周内出现多条同主题材料时，合并成一个监测事件，不重复刷屏。

### 7.2 触发后动作

| 触发等级 | 必做动作 | 时限 |
| --- | --- | --- |
| L1 | 记录到 tracker，附一句影响判断 | 当周完成 |
| L2 | 输出 1 段“影响现有结论吗”的分析，并指定要不要改某份 memo / matrix | `5` 个工作日内 |
| L3 | 发起专项复核；必要时先把相关场景改成 `HOLD` 或冻结对外表述 | `48` 小时内 |

### 7.3 文档更新映射

| 变化发生在哪个法域 | 默认要回写的文档 |
| --- | --- |
| 中国 | `china-legal-ai-go-no-go-memo`、`china-contract-compliance-copilot-management-memo`、`china-contract-compliance-copilot-ops-checklist`、`china-contract-compliance-copilot-management-brief`、`legal-ai-opportunity-risk-matrix` |
| 新加坡 | `singapore-legal-ai-go-no-go-memo`、`legal-ai-opportunity-risk-matrix` |
| 香港 | `hong-kong-legal-ai-go-no-go-memo`、`hong-kong-legal-ai-management-brief`、`legal-ai-opportunity-risk-matrix` |
| 英格兰及威尔士 | `uk-australia-uae-legal-ai-market-comparison`、`legal-ai-opportunity-risk-matrix` |
| 跨法域共性变化 | `legal-llm-law-intersections`、`legal-ai-opportunity-risk-matrix`、`court-facing-ai-rules-sanction-risk-tracker`，必要时再回写各法域 memo |

## 8. 当前建议的首轮监测重点

如果只选最值得优先盯的监测项，我会先盯下面这些：

- 中国：
  - 备案 / 登记公告口径是否继续收紧
  - 标识办法执法是否开始进入常态化处罚
  - 最高法 / 互联网法院是否继续输出涉 AI 版权、平台责任、训练数据相关裁判规则
  - 是否首次从法院内部 AI 应用规范 / 建设材料，转向更明确的 court-user filing / disclosure / verification 正式规则文本
- 新加坡：
  - MinLaw 法律行业 GenAI 指南是否继续更新附录、样例、尽调要求
  - Singapore Courts 是否把 disclosure 或 affidavit 要求收紧
  - 是否出现代表性 AI citation / confidentiality 案件
- 香港：
  - PCPD 是否继续把 AI / 隐私治理框架往更具体的组织控制要求推进
  - Judiciary 是否把当前 AI guidance 延伸到 court users、提交材料或更明确的 litigation 边界
  - Law Society 是否把 human oversight、transparency、data governance 进一步写成更具体的律师使用要求
- 英格兰及威尔士：
  - CJC interim report 中关于 AI-generated evidence declaration 的 proposal 是否变成正式规则或 CPR / practice direction
  - SRA 是否继续批准新一类 AI legal service model
  - 是否出现更多像 `Ayinde` 这类直接影响律师 competence / supervision 的判决

## 9. 维护原则

- 只记录会影响产品边界、合规边界、对外表述、go / no-go 或 pilot 控制要求的变化。
- 先看官方源，再看行业组织；媒体报道只能作为线索，不能替代一手材料。
- 新材料如果只强化旧结论，不必重写所有文档，但要在 tracker 里留下时间戳和一句判断。
- 任何涉及法院提交、监管申报、公众服务边界的变化，默认按 `L3` 处理，先复核，再决定是否继续推进。

## 10. 当前开放 court-facing 监测动作

这部分只列已经进入明确截止日期管理的 court-facing 事项，避免它们只留在专项 tracker 里、却没有回到总包级别的跟踪视图。

| 截止日期 | 法域 | 事件 / 动作 | 默认 owner | 默认回写 |
| --- | --- | --- | --- | --- |
| `2026-03-27` | 中国 / 新加坡 / 香港 / 澳大利亚 | 完成下一轮 court-facing 周度 source sweep，并至少记录一次 no-change 或 change event | `Research owner` | `court-facing-ai-rules-sanction-risk-tracker`，必要时回写对应 memo |
| `2026-04-14 23:59` | 英格兰及威尔士 | 在 `CJC` consultation closing time 当天复核 current-work page、latest-news page 和 interim paper，判断是否从 `L2` 升到更明确的规则变化结论 | `Research + Legal / compliance owner` | `court-facing-ai-rules-sanction-risk-tracker`、`uk-australia-uae-legal-ai-market-comparison`，必要时 `legal-ai-opportunity-risk-matrix` |

## 11. 首次 dated monitoring update（2026-03-20 UTC）

为了让这份 tracker 从“有节奏的研究清单”变成真正可审计的运营资产，首轮基线刷源结果至少按下面方式留痕：

| 日期 | 法域 | 主题 | 来源页面 | source access summary | 触发等级 | 这次变化 / 核查结论 | 会不会改变当前边界 | owner | 下次动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2026-03-20` | 中国 | 标识治理 | `CAC` 标识办法发布页 + 答记者问 + `2025-11-25` 标识违法违规集中查处通报 | 标识办法发布页：`direct`；答记者问：`direct`；执法通报：`direct` | `L1` | 当前应继续按“显式标识 + 文件元数据隐式标识 + 平台上架核验 + 用户协议说明”理解中国标识要求；`2025-11-25` 的集中查处通报进一步说明标识要求已经进入实际执法与下架处置层面。对研究包而言，这强化了导出、协议、日志和提示语设计的重要性，但没有改变既有产品边界 | `不会` | `Research + Legal / compliance owner` | `2026-03-27` 复核是否出现新的实施通报、执法或配套标准变化 |
| `2026-03-20` | 中国 | 备案 / 登记与产品边界 | `CAC` `2025` 年生成式人工智能服务已备案信息公告 | 备案 / 登记公告：`direct` | `L1` | 当前备案 / 登记口径仍围绕具有舆论属性或者社会动员能力的生成式 AI 服务；已上线应用或功能仍需公示模型名称、备案号或上线编号。这进一步支持研究包把中国 legal AI 首发边界放在 `企业内闭环工具`，同时继续盯 API / 应用层登记口径是否外溢 | `不会` | `Research + Legal / compliance owner + Market / GTM owner` | `2026-03-27` 复核后续备案 / 登记公告是否改变企业内工具边界 |
| `2026-03-20` | 中国 | 行业专项与 court-facing | `人工智能气象应用服务办法` + 最高法 AI 司法应用 / 法信材料 | 气象办法：`direct`；`SPC` AI 司法应用意见：`source unavailable (automation)`，当前 `court.gov.cn` shell 抓取返回 `403`；法信材料：`source unavailable (automation)`，同类 `SPC` 官方页当前 shell 抓取返回 `403` | `L1` | 当前可确认两点：一是中国 AI 合规要求已开始出现行业专项办法，说明部分垂直场景会有额外备案、算法与安全义务；二是当前最高法公开材料仍主要是法院内部 AI 应用规范、智能审判 / 诉讼服务建设和法律模型基础设施，而不是单独全国 court-user filing / disclosure guide | `不会` | `Research + Legal / compliance owner + Product owner` | `2026-03-27` 继续复核是否出现其他行业专项办法或全国 court-user 规则文本 |
| `2026-03-20` | 中国 | 拟人化互动与专业领域附加义务 | `CAC` 《人工智能拟人化互动服务管理暂行办法（征求意见稿）》 + `司法部律师工作条线` / `司法部公共法律服务条线` / `12348` / `中华全国律师协会` follow-on source sweep | 征求意见稿：`direct`；`司法部律师工作条线`栏目根路径：`source unavailable (automation)`，当前 shell 抓取自循环重定向；律师工作 `pub/sfbgw/...` fallback article：`source unavailable (automation)`，同轮 shell 抓取仍自循环重定向；`司法部公共法律服务条线`栏目根路径：`source unavailable (automation)`，当前 shell 抓取自循环重定向；公共法律服务 `pub/sfbgw/...` fallback article：`source unavailable (automation)`，同轮 shell 抓取仍自循环重定向；`12348` 首页：`direct`；`中华全国律师协会` 首页：`direct` | `L2` | 该征求意见稿显示中国 AI 治理已经从通用生成式 AI 规则进一步延伸到具体应用形态：要求显著提示用户正在与人工智能交互、限制用户交互数据对外提供和用于模型训练、触发条件下开展安全评估，并要求应用分发平台核验安全评估和备案情况；同时明确卫生健康、金融、法律等专业领域服务还需同时符合主管部门规定。对本研究包而言，它强化了**不要把中国 legal AI 做成面向公众的拟人化互动服务**这一边界判断，但暂不改变当前以企业内闭环工具为主的统一边界。同日复核 `CAC` 官方页仍写明意见反馈截止时间为 `2026-01-25`，且第三十二条仍保留 `本办法自2026年 月 日起施行`，因此本轮仍按 draft-stage signal 处理，而不是已定稿规则。同日 follow-on 补扫显示：`MOJ` 两个法律服务栏目根路径及当前记录的 `pub/sfbgw/...` fallback article 在自动抓取里仍是 source-access 问题，而不是规则变化；同日 official-domain search 下 `MOJ` 可见的 AI 相关页面仍主要是地方司法行政实践、律所数字化经验或公共法律服务建设稿件，例如 `当律师遇上AI，会擦出怎样的火花`，应继续按 `signal-only / L1 no-change` 处理；`中华全国律师协会` 官方域当前可见的 AI 相关页面仍主要是行业动态或业务进阶内容，例如 `律师如何借助人工智能开展法律业务` 这类 `业务进阶` 页面，默认也只按 `signal-only / L1 no-change` 处理，而不是全国性法律行业 AI 正式指引；`12348` 与 `中华全国律师协会` 当前可直接访问，但本轮未看到足以改写当前边界的全国性法律行业 AI 正式指引或配套规范 | `不会` | `Research + Legal / compliance owner + Product owner` | `2026-03-27` 复核是否出现正式稿、补充答记者问或面向法律等专业领域的配套要求 |

### 11.1 本次中国 dated update 的最小官方锚点

- `关于印发〈人工智能生成合成内容标识办法〉的通知`
  - `https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm`
- `《人工智能生成合成内容标识办法》答记者问`
  - `https://www.cac.gov.cn/2025-03/14/c_1743654685896173.htm`
- `网信部门依法集中查处一批存在人工智能生成合成内容标识违法违规问题的移动互联网应用程序`
  - `https://www.cac.gov.cn/2025-11/25/c_1765795550841819.htm`
- `国家互联网信息办公室关于发布2025年生成式人工智能服务已备案信息的公告`
  - `https://www.cac.gov.cn/2026-01/09/c_1769688009588554.htm`
- `国家互联网信息办公室关于《人工智能拟人化互动服务管理暂行办法（征求意见稿）》公开征求意见的通知`
  - `https://www.cac.gov.cn/2025-12/27/c_1768571207311996.htm`
- `司法部` official-domain `signal-only` example page：`当律师遇上AI，会擦出怎样的火花`
  - `https://www.moj.gov.cn/pub/sfbgw/fzgz/fzgzggflfwx/fzgzlsgz/202504/t20250410_517208.html`
- `中华全国律师协会` official-domain `signal-only` example page：`律师如何借助人工智能开展法律业务`
  - `https://www.acla.org.cn/info/f6e55c6cc22f4f88917ca31970f01663`
- `人工智能气象应用服务办法`
  - `https://www.cma.gov.cn/zfxxgk/zc/gz/202504/W020250429613208378185.pdf`
- `《最高人民法院关于规范和加强人工智能司法应用的意见》全文（中英文版）`
  - `https://www.court.gov.cn/zixun/xiangqing/382461.html`
- `推进现代科技与司法审判工作深度融合 最高法发布“法信法律基座大模型”研发成果`
  - `https://www.court.gov.cn/zixun/xiangqing/447711.html`

### 11.2 首次中国 sweep 的逐锚点判断（按 section 12.1 / 12.3 补齐）

为了避免首轮 `2026-03-20` 记录只有主题级摘要、却没有逐锚点 `no-change / change` 判断，现按后续中国周度 sweep 的最低留痕格式补齐如下：

| 日期 | 主题 | 本轮检查过的官方锚点 | source access / fallback used | 每个锚点的 `no-change / change` 判断 | meaningful-change 结论 | 会不会改变当前统一边界 | 需要回写哪些文档 | owner | 下次动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2026-03-20` | 标识治理 | `CAC` 标识办法通知；`CAC` 标识办法答记者问；`2025-11-25` `CAC` 标识执法通报 | 通知：`direct`；答记者问：`direct`；执法通报：`direct` | 通知：`no-change`，显式标识、隐式标识、导出文件标识、平台核验、用户协议和日志要求仍是当前基线；答记者问：`no-change`，仍是对既有标识机制的解释性补充；执法通报：`no-change`，仍主要说明显式标识、隐式标识、平台核验和用户声明功能已经进入执法重点 | `不是，仍按 L1 no-change` | `不会` | `无（维持 section 11 摘要即可）` | `Research + Legal / compliance owner` | `2026-03-27` |
| `2026-03-20` | 备案 / 登记 | `2026-01-09` `CAC` 备案 / 登记公告 | 公告：`direct` | 公告：`no-change`，仍以具有舆论属性或者社会动员能力的生成式 AI 服务为主要备案 / 登记对象，应用或功能显著位置公示模型名称、备案号或上线编号的要求未改变当前企业内闭环工具边界 | `不是，仍按 L1 no-change` | `不会` | `无（维持 section 11 摘要即可）` | `Research + Legal / compliance owner + Market / GTM owner` | `2026-03-27` |
| `2026-03-20` | 行业专项规则 | `人工智能气象应用服务办法` | 办法：`direct` | 办法：`no-change`，当前仍主要说明中国 AI 合规已进入纵向部门专项治理，并出现可迁移关注的数据身份标识、数据管理和部门协同思路，但尚未形成直接面向法律服务的专项边界 | `不是，仍按 L1 no-change` | `不会` | `无（维持 section 11 摘要即可）` | `Research + Legal / compliance owner + Product owner` | `2026-04-03` |
| `2026-03-20` | 拟人化互动 / 专业领域附加义务 | `2025-12-27` `CAC` 拟人化互动服务管理征求意见稿；`司法部律师工作条线`栏目根路径；律师工作 `pub/sfbgw/...` fallback article；`司法部公共法律服务条线`栏目根路径；公共法律服务 `pub/sfbgw/...` fallback article；`12348` 中国法律服务网首页；`中华全国律师协会` 首页 | 征求意见稿：`direct`；律师工作栏目根路径：`source unavailable (automation)`，当前 shell 抓取自循环重定向；律师工作 `pub/sfbgw/...` fallback article：`source unavailable (automation)`，同轮 shell 抓取仍自循环重定向；公共法律服务栏目根路径：`source unavailable (automation)`，当前 shell 抓取自循环重定向；公共法律服务 `pub/sfbgw/...` fallback article：`source unavailable (automation)`，同轮 shell 抓取仍自循环重定向；`12348` 首页：`direct`；`中华全国律师协会` 首页：`direct` | 征求意见稿：`change`，新增拟人化互动服务单独治理框架，要求显著提示用户正在与人工智能交互、限制用户交互数据对外提供与训练使用、在特定情形下开展安全评估，并要求应用分发平台核验安全评估和备案情况；第三十一条还明确卫生健康、金融、法律等专业领域服务需同时符合主管部门规定。这对任何面向公众的拟人化 legal AI 都是更高约束，但未改变当前企业内闭环工具边界；同日复核该官方页可见意见反馈截止时间仍为 `2026-01-25`，第三十二条仍留空正式生效日期，因此本轮仍按 draft-stage signal 处理，而不是已定稿规则；律师工作栏目根路径 / fallback article：`no-change`，当前只确认 `MOJ` 官方栏目在自动抓取中仍不可达，应继续按 `source unavailable (automation)` + fallback / 人工复核规则处理，不能把这类 source-access 问题当作已有法律行业 AI 指引；公共法律服务栏目根路径 / fallback article：`no-change`，同上；`12348` 首页：`no-change`，当前可直接访问，但同域 AI / 智能法律服务可见材料仍主要是地方公共法律服务或智能服务实践，应按 `signal-only / L1 no-change` 处理，本轮未见全国性公共法律服务 AI 助手专门规范；`中华全国律师协会` 首页：`no-change`，当前可直接访问；同日 official-domain example page 仍以 `律师如何借助人工智能开展法律业务` 这类 `业务进阶` 页面为主，应按 `signal-only / L1 no-change` 处理，本轮未见全国性律师使用 AI 正式指引或纪律规范更新；同日 official-domain search 下 `MOJ` 可见的 AI 相关页面仍以 `当律师遇上AI，会擦出怎样的火花` 这类律师业务 / 律所数智化报道为主，也应按 `signal-only / L1 no-change` 处理，不构成全国性正式规范 | `是，按 L2` | `不会` | `无（维持 section 11 摘要即可；待正式稿或法律行业主管部门正式规范再决定是否回写 memo / matrix）` | `Research + Legal / compliance owner + Product owner` | `2026-03-27` |
| `2026-03-20` | 法院 / 公共法律服务边界 | `SPC` AI 司法应用意见；`SPC` 法信法律基座大模型材料 | 意见：`source unavailable (automation)`，当前 `court.gov.cn` shell 抓取返回 `403`，边界判断沿用已纳入本包的官方文本；法信材料：`source unavailable (automation)`，同类 `SPC` 官方页当前 shell 抓取返回 `403`，后续默认转人工浏览器核验 | 意见：`no-change`，仍是法院侧 AI 司法应用治理与辅助审判定位；法信材料：`no-change`，仍是法律大模型基础设施与 court-side capability 建设信号，不是面向 court users 或 public-facing legal AI 的全国提交 / 披露规则 | `不是，仍按 L1 no-change` | `不会` | `无（维持 section 11 摘要即可）` | `Research + Legal / compliance owner + Product owner` | `2026-04-03` |

## 12. 中国法域当前开放监测队列

为了让中国侧的治理、标识、备案 / 登记和行业专项规则变化进入明确的截止日期管理，当前默认开放队列如下：

| 截止日期 | 主题 | 必做动作 | 默认 owner | 触发后默认回写 |
| --- | --- | --- | --- | --- |
| `2026-03-27` | 标识治理 | 复核 `CAC` 标识办法是否出现新的答记者问、实施说明、配套标准解释或执法通报 | `Research + Legal / compliance owner` | `china-legal-ai-go-no-go-memo`、`china-contract-compliance-copilot-ops-checklist`、必要时 `legal-ai-opportunity-risk-matrix` |
| `2026-03-27` | 备案 / 登记口径 | 复核 `CAC` 是否发布新的备案 / 登记公告，重点看 API / 功能级登记口径和显著位置公示要求是否变化 | `Research + Legal / compliance owner + Market / GTM owner` | `china-legal-ai-go-no-go-memo`、`china-contract-compliance-copilot-management-memo`、必要时 `legal-ai-opportunity-risk-matrix` |
| `2026-03-27` | 拟人化互动 / 专业领域附加义务 | 复核 `CAC` 拟人化互动服务管理征求意见稿是否出现正式稿、答记者问或补充说明，并同步补扫 `司法部律师工作条线`、`司法部公共法律服务条线`、`12348` 和 `中华全国律师协会`，重点看法律等专业领域条款、用户交互数据限制、安全评估、应用分发平台核验与算法备案要求是否进一步收紧；如 `司法部` 栏目页出现自循环重定向、超时或暂时不可达，必须记录 `source unavailable` 并改查同域官方文章页或站内检索结果页，避免把抓取失败误记为 `no-change` | `Research + Legal / compliance owner + Product owner` | `china-legal-ai-go-no-go-memo`、`legal-ai-opportunity-risk-matrix`，必要时回写中国 memo 家族 |
| `2026-04-03` | 行业专项规则 | 补扫是否出现更多类似 `人工智能气象应用服务办法` 的部门规章或专项规范，并判断法律 AI 是否会受跨行业控制思路影响 | `Research + Legal / compliance owner + Product owner` | `legal-llm-law-intersections`、`legal-ai-opportunity-risk-matrix`，必要时回写中国 memo 家族 |
| `2026-04-03` | 法院 / 公共法律服务规则 | 继续复核最高法、法信、地方法院和司法行政系统，确认是否出现面向 court users 或 public-facing legal AI 的新规则文本 | `Research + Legal / compliance owner + Product owner` | `china-legal-ai-go-no-go-memo`、`court-facing-ai-rules-sanction-risk-tracker`、必要时 `legal-ai-opportunity-risk-matrix` |

### 12.1 下次中国 sweep 的最低留痕包

为了避免后续周度刷新只留下“看过了 / 没变化”这种无法复核的记录，后续中国 `no-change` 或 `change` 事件至少要带上下面这些留痕项：

- 检查日期（UTC）和执行 owner
- 本轮至少检查过的官方锚点
  - `CAC` 标识办法通知
  - `CAC` 标识办法答记者问
  - `CAC` 已纳入本包的最新标识执法通报
  - 最新一轮 `CAC` 备案 / 登记公告
  - 已纳入本包的拟人化互动 / 专业领域附加义务锚点
  - 已纳入本包的行业专项规则锚点
  - `SPC` AI 司法应用 / 法信材料
  - 如果本轮主题触及法律等专业领域服务，至少再检查：
    - `司法部律师工作条线`
    - `司法部公共法律服务条线`
    - `12348` 中国法律服务网
    - `中华全国律师协会`
- 对每个锚点补一条 source access 状态：
  - `direct`
  - `redirected`
  - `timeout`
  - `source unavailable`
- 如果原定官方 URL 自循环重定向、超时或暂时不可达：
  - 不得直接记为 `no-change`
  - 必须写明 `source unavailable`
  - 必须补记 fallback official page used，例如同域官方文章页、站内检索结果页或主管部门首页下的同主题官方页面
  - 对 `司法部律师工作条线` 与 `司法部公共法律服务条线`，默认 fallback 顺序是：栏目根路径 -> 同域 `pub/sfbgw/...` article-page family -> 同域 `pub/sfbgwapp/...` article-page family -> 同域站内检索结果页
  - 如果以上 `MOJ` 自动抓取路径都失败，必须额外写明 `source unavailable (automation)` 并安排人工浏览器复核
  - 如果没有找到可替代的同域官方页面，必须把该锚点标为“本轮未完成核查”，并在 `下次动作` 中指定补刷日期
- 对每个锚点写一句 `no-change / change` 判断
- 如果判断为 `change`，必须写明影响的是：
  - 标识
  - 备案 / 登记
  - 拟人化互动 / 专业领域附加义务
  - 行业专项
  - 法院 / 公共法律服务边界
- 必须写明会不会改变当前统一边界：
  - `不会`
  - `可能`
  - `会`
- 如果答案是 `可能` 或 `会`，必须同步指定要不要回写：
  - `china-legal-ai-go-no-go-memo`
  - `china-contract-compliance-copilot-management-memo`
  - `china-contract-compliance-copilot-ops-checklist`
  - `legal-ai-opportunity-risk-matrix`
  - `court-facing-ai-rules-sanction-risk-tracker`
- 最后用 section `12.2` 的规则判断：这次变化到底只是 `L1` 留痕，还是已经构成需要升级分析或改边界的 meaningful change

### 12.2 中国 sweep 的 meaningful-change 判定

为了避免后续中国周度刷新把所有“新公告 / 新通报 / 新表述”都误判成需要重写整包，默认按下面四类问题判断什么才算值得升级处理的 meaningful change：

- 标识治理
  - 如果新材料改变了显式标识位置、隐式标识字段、平台核验要求、用户声明 / 协议责任、导出文件处理或留痕要求，至少按 `L2` 处理
  - 如果执法通报直接命中本包当前控制域，例如导出无显式标识、元数据字段缺失、平台未核验、用户声明功能缺失，且足以改写现有 safeguard 设计，按 `L2`
  - 如果全国性规则、强制标准或高频执法信号已经足以改变当前默认产品边界，按 `L3`
- 备案 / 登记
  - 如果新公告或地方实践改变了 API / 应用 / 功能级调用是否需要登记、公示模型名称 / 备案号 / 上线编号的要求，至少按 `L2`
  - 如果现有“企业内闭环工具”边界可能被重新纳入备案 / 登记口径，按 `L3`
- 拟人化互动 / 专业领域附加义务
  - 如果新材料只是确认 `CAC` 征求意见稿仍在原有方向推进，但未出现正式稿、未新增法律服务领域主管部门配套规范，默认可保留在 `L1` 或维持已记录的 `L2` 待跟踪状态
  - 如果正式稿、答记者问、配套说明或行业主管部门规则收紧了用户交互数据处理、显著提示、安全评估、平台核验或算法备案要求，至少按 `L2`
  - 如果 `司法部`、`12348` 或 `中华全国律师协会` 发布了直接面向法律服务 AI、律师使用 AI、公共法律服务 AI 助手或拟人化互动 legal AI 的全国性正式规则 / 指引，至少按 `L2`
  - 如果 `司法部`、`12348` 或 `中华全国律师协会` 官方域名下新出现的 AI 相关材料只是地方实践报道、业务进阶文章、行业动态或项目宣传，而不是全国性正式规则 / 指引 / 纪律规范，默认按 `L1 no-change` 记录为 signal-only，不单独据此改写当前统一边界
  - 如果这些法律服务领域规则足以改变当前 `企业内闭环工具` 边界，或把面向公众的 legal AI / public-legal-service AI 明确推向更高合规门槛或 `NO-GO`，按 `L3`
- 官方源可达性 / 替代页面
  - 如果只是 `司法部 / 12348 / 中华全国律师协会` 某个栏目页临时重定向、超时或不可达，但同域官方替代页面仍能支撑相同结论，默认不算 substantive meaningful change；应按 `L1` 记录 `source unavailable + fallback official page used`
  - 如果 `MOJ` 根路径与两类同域 article-page family 在本轮自动抓取中都失败，默认仍不算规则实质变化，但必须按 `L1` 记录 `source unavailable (automation)`，并把人工浏览器复核列为下次动作
  - 如果关键官方锚点在本轮既无法直接访问，也找不到可替代的同域官方页面，默认仍不算规则实质变化，但不得写成“已完成 no-change”；必须把该锚点记为未完成核查，并在 `下次动作` 中安排补刷
- 行业专项规则
  - 如果新的部门规章或专项规范只是证明“AI 合规开始向垂直行业细分”，但尚未改变法律 AI 当前边界，可按 `L1` 记录
  - 如果专项规则开始出现可迁移到法律 AI 的明确控制逻辑，例如额外的质量评估、模型 / 算法管理、数据身份标识、日志或安全义务，至少按 `L2`
  - 如果出现直接面向法律服务、合规服务、公共法律服务或相邻高敏场景的专项 AI 规则，按 `L3`
- 法院 / 公共法律服务边界
  - 如果仍然只是法院内部 AI 应用规范、智能审判 / 诉讼服务建设或法律模型基础设施材料，默认按 `L1`
  - 如果出现面向律师、诉讼参与人、法院用户或公共法律服务用户的 AI 提交 / 核验 / 披露要求，至少按 `L2`
  - 如果出现全国性或高位阶的 court-user / public-facing legal AI 正式规则文本，默认按 `L3`

只要命中下面任一结果，就应认定为 meaningful change，而不是普通留痕：

- 会改变 `企业内闭环工具` 的统一边界
- 会改变拟人化互动 legal AI、公共法律服务 AI 助手或律师使用 AI 的最低控制要求
- 会改变标识、导出、日志、用户声明、人工复核等最低 safeguard
- 会改变 API / 应用 / 功能级备案或登记的判断
- 会改变当前 `NO-GO / HOLD` 的 court-facing 结论
- 会改变 `legal-ai-opportunity-risk-matrix` 中的 go / no-go、优先级或法域切入顺序

如果新材料只是重复强化既有要求，没有改变上述任一边界或控制项，默认保留在 `L1 no-change`，只需按 section `12.1` 留下可复核证据，不必重写 memo / matrix / 总览。

### 12.3 中国 sweep 的标准输出模板

为了避免不同执行人留下的 dated update 颗粒度不一致，后续中国周度 sweep 默认至少按下面模板输出一次，哪怕结论是 `no-change` 也一样：

| 日期 | 主题 | 本轮检查过的官方锚点 | source access / fallback used | 每个锚点的 `no-change / change` 判断 | meaningful-change 结论 | 会不会改变当前统一边界 | 需要回写哪些文档 | owner | 下次动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `YYYY-MM-DD` | 标识 / 备案登记 / 拟人化互动或专业领域附加义务 / 行业专项 / 法院或公共法律服务 | 列出本轮实际检查过的 `CAC / CMA / SPC / 司法部 / 12348 / 律协` 等官方页面 | 对每个锚点写 `direct / redirected / timeout / source unavailable`，如使用 fallback 则补记具体 official page；如 `MOJ` 自动抓取失败则写 `source unavailable (automation)` + `manual browser verification` | 至少一句话写清每个锚点是 `no-change` 还是 `change` | `不是` / `是，按 L2` / `是，按 L3` | `不会` / `可能` / `会` | `memo / checklist / matrix / court-facing tracker / 无` | `Research / Legal / Product` | `YYYY-MM-DD` |

最低填写要求：

- 如果结论是 `不是 meaningful change`，也必须写明为什么仍是 `L1 no-change`
- 如果任一锚点出现重定向、超时或不可达，必须在“本轮检查过的官方锚点”或“每个锚点的判断”中明确写出 `source unavailable` 与 fallback official page used；如果没有 fallback，同样要写明并把补刷日期放进 `下次动作`
- 如果 `司法部律师工作条线` 或 `司法部公共法律服务条线` 使用了 fallback official page，还应同时记下栏目根路径和实际采用的 `pub/sfbgw/...` 或 `pub/sfbgwapp/...` 页面，避免后续执行人无法复核替代路径是否一致
- 如果 `MOJ` 根路径和两类 article-page family 都无法在自动抓取中打开，必须明确写出 `source unavailable (automation)`，并把人工浏览器复核写入 `下次动作`
- 最低表格粒度要求是：`source access / fallback used` 这一列不能留空；如果本轮没有 fallback，也要明确写 `direct` 或 `redirected`
- 如果 `MOJ`、`12348` 或 `中华全国律师协会` 官方域名下本轮新增的 AI 相关材料只是地方实践报道、业务进阶文章、行业动态或项目宣传，必须在“每个锚点的判断”里明确写出 `signal-only / L1 no-change`，避免把 official-domain article 误记为全国性正式规则
- 如果 `MOJ`、`12348` 或 `中华全国律师协会` 的 `signal-only / L1 no-change` 判断来自 official-domain article example，至少要记下一条具体页名或路径，避免只有抽象口径却无法复核
- 如果结论是 `是，按 L2` 或 `是，按 L3`，必须写明触发点属于：
  - 标识
  - 备案 / 登记
  - 拟人化互动 / 专业领域附加义务
  - 行业专项
  - 法院 / 公共法律服务边界
- 如果决定“不回写任何文档”，也要明确写 `无`，避免事后无法判断是“无需回写”还是“漏写”
- 如果本轮只检查了 `11.1` 以外的新官方源，必须把新源补进 `11.1` 或在本轮记录中说明为什么可以替代既有锚点
