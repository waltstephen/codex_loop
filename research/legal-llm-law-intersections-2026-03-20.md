# 法律 LLM / AI 与法律交叉调研

日期：2026-03-20

## 一句话结论

法律 LLM / AI 和法律的交叉，已经不只是“用 AI 做法律问答”这么简单，而是同时落在四条线：

1. AI 本身被法律规制
2. AI 被律师、法务、法院、监管机构当作工作工具
3. AI 引发新的责任、证据、版权、隐私与职业伦理问题
4. 法律行业反过来推动“可引用、可审计、可追责”的 LLM 技术路线

## 1. 现在这个领域主要怎么和法律交叉

### 1. AI 作为“被监管对象”

- 欧盟 AI Act 已进入分阶段适用期，通用模型（GPAI）义务、AI literacy、禁用场景、高风险系统等要求都在逐步落地。
- 中国已经形成“生成式服务 + 深度合成 + 内容标识 + 数据/网安/个保法衔接”的治理框架。
- 美国没有统一联邦 AI 综合法，但在版权、法院规则、行业伦理、风险管理框架上推进很快。

这意味着：做法律 LLM，不只是做模型能力，还要做合规能力。

### 2. AI 作为“法律服务工具”

目前最成熟的落地方向不是“完全自动给法律意见”，而是辅助型工作流：

- 法律检索
- 合同审查与条款比对
- 尽调
- e-discovery / 文档审阅
- 诉状、备忘录、合规文档起草
- 法规/案例摘要与问答
- 法官画像、诉讼分析、结果预测等 analytics

也就是说，法律行业对 LLM 的真实需求，本质上是“高成本文本劳动自动化 + 可核验结论输出”。

### 3. AI 作为“职业伦理与程序法风险源”

LLM 一旦进入律师、法院或法务流程，就会直接撞上法律职业义务：

- competence：律师是否理解工具能力和边界
- confidentiality：客户信息能不能输入模型，输入后会不会被保留、再训练或泄露
- candor to tribunal：向法院提交的内容是否真实、是否含虚构案例
- supervision：律所如何管理律师、助理和外部 AI 供应商
- reasonable fees：AI 提效后如何收费才合理

这也是为什么法律行业比很多别的行业更强调“human in the loop”。

### 4. AI 作为“知识产权与数据治理问题制造者”

这个方向目前至少有四个高频法问题：

- 训练数据是否涉及版权与许可
- 输出内容是否可版权化
- 生成内容是否需要标识和溯源
- 涉及个人信息、商业秘密、律师保密义务时如何处理

对法律行业来说，这些不是外围问题，而是产品能否上线、能否进入律所/法务采购名单的核心问题。

### 5. AI 进入法院与公共法律服务

法院和司法机构并不是只在“审查 AI”，也开始直接管理或吸收 AI：

- 一些美国法院已经对生成式 AI 参与诉讼材料提出专门规则或认证要求
- 中国在政务与治理场景中已开始推动大模型部署应用，法律服务和治理辅助是典型落地场景之一

所以，这个赛道并非只属于 law firm tech，也在延伸到 court tech、gov tech、reg tech。

## 2. 当前最值得关注的五个子方向

### 1. Legal RAG

相比直接让模型“裸答”，法律场景更强调：

- 基于法规、判例、合同库检索
- 输出时附引用
- 控制上下文污染
- 保证版本与时效

这条路线很可能长期比“纯大模型记忆法律知识”更稳。

### 2. Citation-safe drafting

法律 LLM 不是只要会写，而是要：

- 引用不造假
- 引用可追溯
- 论证链清晰
- 能够被律师/法官快速复核

以后法律 AI 产品的分水岭，很可能就在“能不能安全进入提交法院/监管机关的文档链路”。

### 3. Contract / compliance copilot

企业更愿意为这些场景付费：

- 合同红线比对
- 监管义务抽取
- 内部政策与外部法规映射
- 跨法域合规检查

因为这里 ROI 更明确，也更适合“先辅助、后半自动化”。

### 4. 面向中文法域的 legal LLM

中文法律场景并不只是把英文 legal LLM 翻译过来：

- 法条结构
- 司法解释与指导案例体系
- 裁判文书表达
- 行政监管文本
- 地方法规与部门规章

都要求单独的数据、评测和工作流设计。

### 5. AI governance / audit / provenance

未来法律 AI 不是只有“回答对不对”，还会越来越看重：

- 审计日志
- 模型/版本管理
- 数据来源
- 风险分级
- 输出标识
- 人工复核责任链

这部分实际上就是法律、合规、平台治理和工程系统设计的交叉点。

## 3. 这个方向最难的点

### 1. 法律不是通用问答

- 强 jurisdiction dependence
- 强时效性
- 强程序性
- 强格式约束

同一个问题，在不同法域、不同时间点、不同程序阶段，答案都可能变。

### 2. Benchmark 好，不等于能上生产

公开 benchmark 往往能说明“模型懂不懂法律文本”，但不等于能直接用于：

- 对客户出正式建议
- 向法院提交材料
- 做监管申报
- 处理机密文件

真实落地难点在 workflow，不只在 base model。

### 3. 幻觉在法律场景代价极高

普通行业幻觉可能只是“答错”；
法律场景幻觉可能变成：

- 错误诉讼策略
- 虚构案例引用
- 错误合规建议
- 客户损失
- 律师职业责任风险

### 4. 数据与保密边界很难处理

法律行业的高价值数据通常也是最敏感的数据：

- 客户案卷
- 未公开交易文件
- 内部调查材料
- 个人敏感信息
- 特权 / 保密通信

因此很多 legal AI 产品的核心竞争力其实是部署方式、权限控制、日志和不留痕能力。

## 4. 如果你要继续深挖，可以沿这三条线做

### 路线 A：研究型

- 做中文 legal benchmark
- 做 Legal RAG 评测
- 研究法律推理链和可解释性
- 研究“法规更新 -> 知识库更新 -> 输出纠偏”机制

### 路线 B：产品型

- 面向律所的 citation-safe drafting
- 面向法务的合同/合规 copilot
- 面向公共法律服务的法规问答助手
- 面向法院/监管机构的文档辅助与结构化审查

### 路线 C：治理/合规型

- AI 使用政策
- law firm / in-house AI governance checklist
- 供应商尽调模板
- 敏感数据进入模型前的分类与脱敏机制
- AI 输出标识、审计和责任分配

## 5. 我对这个领域的判断

如果你问“法律 LLM / AI 现在最重要的交叉点是什么”，我的判断是：

不是“模型会不会答法律题”，而是下面这三个问题：

1. 能不能把法律知识检索、引用、更新和审计做成工程系统
2. 能不能把律师伦理、法院要求、版权/隐私/标识义务做进产品设计
3. 能不能在高风险法律场景里，把 AI 从“玩具”变成“可签字、可采购、可追责”的基础设施

## 6. 本次调研用到的一手/核心参考

### 官方/监管

- 欧盟委员会 AI Act 页面与 FAQ
- 美国律师协会（ABA）Formal Opinion 512
- NIST AI Risk Management Framework 1.0
- 美国版权局 Copyright and Artificial Intelligence 项目与分册报告
- 中国《生成式人工智能服务管理暂行办法》
- 中国《人工智能生成合成内容标识办法》及配套标准解读

### 研究/技术

- LegalBench
- LegalBench-RAG
- LawBench
- InternLM-Law
- 2025 年 legal LLM survey（用于看模型、框架、数据、benchmark 全景）

### 可直接继续打开的链接

- 欧盟委员会 AI Act FAQ: https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act
- 欧盟委员会 GPAI obligations: https://digital-strategy.ec.europa.eu/en/faqs/guidelines-obligations-general-purpose-ai-providers
- ABA Formal Opinion 512: https://www.americanbar.org/content/dam/aba/administrative/professional_responsibility/ethics-opinions/aba-formal-opinion-512.pdf
- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- U.S. Copyright Office AI project: https://www.copyright.gov/ai/
- 中国《生成式人工智能服务管理暂行办法》: https://www.miit.gov.cn/zcfg/qtl/art/2023/art_f4e8f71ae1dc43b0980b962907b7738f.html
- 中国《人工智能生成合成内容标识办法》: https://www.gov.cn/zhengce/zhengceku/202503/content_7014286.htm
- LegalBench: https://arxiv.org/abs/2308.11462
- LegalBench-RAG: https://arxiv.org/abs/2408.10343
- InternLM-Law: https://arxiv.org/abs/2406.14887

## 7. 适合下一步继续做的输出

- 做一版“法律 LLM / AI 赛道图谱”PPT
- 做一版“中美欧法律 AI 监管对比表”
- 做一版“给律所/法务团队的 AI 使用清单”
- 做一版“中文法律 RAG 产品架构草图”
