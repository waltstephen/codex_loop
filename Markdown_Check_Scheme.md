# ArgusBot Markdown 代码检查方案

## 概述

本方案整合了 [markdownlint](https://github.com/markdownlint/markdownlint) 工具和自定义飞书验证器，为 ArgusBot 提供完整的 Markdown 格式检查能力。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Markdown 检查流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  输入 Markdown 文本                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────┐    ┌──────────────────────┐           │
│  │  markdownlint   │    │  飞书自定义验证器     │           │
│  │  (标准规则检查)  │    │  (平台特定检查)       │           │
│  │                 │    │                      │           │
│  │ - MD001~MD047   │    │ - FEISHU-MD001       │           │
│  │ - 标题/列表/代码│    │ - 未闭合代码块        │           │
│  │ - 空白/缩进     │    │ - 不支持的语法        │           │
│  └─────────────────┘    └──────────────────────┘           │
│         │                       │                           │
│         └───────────┬───────────┘                           │
│                     ▼                                       │
│          ┌─────────────────────┐                            │
│          │   问题汇总与修复    │                            │
│          │ - 合并问题列表      │                            │
│          │ - 自动修复可行问题  │                            │
│          │ - 生成检查报告      │                            │
│          └─────────────────────┘                            │
│                     │                                       │
│                     ▼                                       │
│          输出：修复后的 Markdown                             │
│              + 检查报告                                      │
└─────────────────────────────────────────────────────────────┘
```

## 文件结构

```
codex_autoloop/
├── md_checker.py              # Markdown 检查器主模块
├── feishu_markdown_validator.py  # 飞书 Markdown 验证器
└── ...

.argusbot/
├── mdl_style.rb               # markdownlint 风格配置
└── ...

tests/
├── test_md_checker.py         # 检查器测试
└── test_feishu_markdown_validator.py  # 验证器测试
```

## 核心组件

### 1. markdownlint 集成 (`md_checker.py`)

**功能**：
- 调用 `mdl` 工具进行标准 Markdown 规则检查
- 支持自定义风格文件 (`.mdl_style.rb`)
- 输出结构化问题报告

**检查规则示例**：
| 规则 ID | 说明 | 严重性 |
|---------|------|--------|
| MD001 | 标题级别跳跃 | warning |
| MD022 | 标题前后空行 | warning |
| MD031 | 代码块前后空行 | warning |
| MD040 | 代码块指定语言 | warning |

### 2. 飞书自定义验证器 (`feishu_markdown_validator.py`)

**功能**：
- 检测未闭合代码块
- 检测不支持的语法（表格、脚注）
- 自动修复常见格式问题
- 安全截断长文本

**检查规则**：
| 规则 ID | 说明 | 严重性 |
|---------|------|--------|
| FEISHU-MD001 | 未闭合代码块 | error |
| FEISHU-MD002 | 表格语法 | warning |
| FEISHU-MD003 | 脚注语法 | warning |
| FEISHU-MD004 | 空内容 | error |
| FEISHU-MD005 | 标题后缺空行 | warning |

### 3. 风格配置文件 (`.argusbot/mdl_style.rb`)

```ruby
# 启用所有规则
all

# 标题风格：ATX (# ## ###)
rule 'header-style', :style => :atx

# 列表风格：使用短横线 (-)
rule 'ul-style', :style => :dash

# 代码块前后空行
rule 'blanks-around-fences'

# 行长度限制（忽略代码块）
rule 'line-length', :line_length => 120, :ignore_code_blocks => true
```

## 使用方法

### Python API

```python
from codex_autoloop.md_checker import check_markdown, quick_fix_for_feishu

# 完整检查
result = check_markdown(
    text="# 标题\n内容",
    style_file=Path(".argusbot/mdl_style.rb"),
    check_feishu=True,
    auto_fix=True,
)

print(f"有效：{result.is_valid}")
print(f"飞书就绪：{result.feishu_ready}")
print(f"问题：{result.issues}")
print(f"修复后：{result.fixed_content}")

# 快速修复
fixed = quick_fix_for_feishu(problematic_text)
```

### 命令行

```bash
# 检查单个文件
python -m codex_autoloop.md_checker README.md

# 检查并输出 JSON 报告
python -m codex_autoloop.md_checker README.md --json
```

### 集成到消息发送流程

```python
# feishu_adapter.py
from .md_checker import quick_fix_for_feishu

def send_message(self, message: str) -> bool:
    # 1. 快速修复 Markdown
    fixed_message = quick_fix_for_feishu(message)

    # 2. 发送修复后的消息
    # ...
```

## 安装要求

### 必需
- Python 3.10+

### 可选（用于完整检查）
```bash
# Ruby 版本 (推荐)
gem install mdl

# 或 Node.js 版本
npm install -g markdownlint-cli
```

## 配置选项

### 风格文件位置

```python
# 项目级别
style_file = Path(".argusbot/mdl_style.rb")

# 用户级别
style_file = Path.home() / ".mdlrc"
```

### 规则自定义

在 `mdl_style.rb` 中：

```ruby
# 启用规则
rule 'MD013', :line_length => 100

# 禁用规则
exclude_rule 'MD024'  # 允许相同标题

# 使用预设风格
style 'relaxed'  # 或 'default', 'cirosantilli'
```

## 检查报告格式

### 文本格式
```
Markdown 检查：未通过
飞书就绪：否
问题数：2

问题详情:
  [错误] FEISHU-MD001: 代码块在第 5 行开始但未闭合
  [警告] FEISHU-MD005 (第 1 行): 标题后缺少空行
```

### Markdown 格式
```markdown
# Markdown 检查报告

**状态:** 未通过
**飞书就绪:** 否
**问题数:** 2

## 问题列表

- ❌ **FEISHU-MD001**: 代码块在第 5 行开始但未闭合
- ⚠️ **FEISHU-MD005** (第 1 行): 标题后缺少空行
```

### JSON 格式
```json
{
  "is_valid": false,
  "feishu_ready": false,
  "issues": [
    {
      "rule_id": "FEISHU-MD001",
      "description": "代码块在第 5 行开始但未闭合",
      "severity": "error"
    }
  ]
}
```

## 与现有代码集成

### 1. FeishuNotifier 集成点

```python
# codex_autoloop/feishu_adapter.py
from .md_checker import check_markdown

def send_message(self, message: str) -> bool:
    # 可选：在发送前进行检查
    result = check_markdown(message, check_feishu=True)

    if not result.feishu_ready:
        # 记录警告或自动修复
        logger.warning(f"Markdown 问题：{result.issues}")
        message = result.fixed_content or message

    # 继续发送...
```

### 2. CI/CD 集成

```yaml
# .github/workflows/markdown-check.yml
name: Markdown Check
on: [push, pull_request]
jobs:
  markdown-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install mdl
        run: gem install mdl
      - name: Check Markdown
        run: mdl -s .argusbot/mdl_style.rb $(git ls-files '*.md')
```

### 3. Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/markdownlint/markdownlint
    rev: v0.12.0
    hooks:
      - id: markdownlint
        args: ["-s", ".argusbot/mdl_style.rb"]
```

## 最佳实践

### 1. 消息生成时检查

在 agent/Reviewer/Planner 输出时实时检查：

```python
def generate_review(decision: ReviewDecision) -> str:
    markdown = format_as_markdown(decision)
    fixed = quick_fix_for_feishu(markdown)
    return fixed
```

### 2. 批量检查

定期检查项目中的所有 Markdown 文件：

```bash
# 每日检查
find . -name "*.md" -exec python -m codex_autoloop.md_checker {} \;
```

### 3. 问题优先级

| 优先级 | 处理 |
|--------|------|
| error (FEISHU-*) | 必须修复，否则不发送 |
| warning (FEISHU-*) | 建议修复，可发送 |
| error/warning (MD***) | 根据项目配置决定 |

## 扩展开发

### 添加自定义规则

```python
# 在 md_checker.py 中添加
def check_custom_rule(text: str) -> list[MarkdownIssue]:
    issues = []
    # 检测特定模式
    if re.search(r'pattern', text):
        issues.append(MarkdownIssue(
            rule_id="CUSTOM-001",
            description="发现不推荐的模式",
            severity="warning",
        ))
    return issues
```

### 添加新的输出格式

```python
def format_html_report(result: MarkdownCheckResult) -> str:
    html = ["<div class='markdown-report'>"]
    for issue in result.issues:
        html.append(f"<div class='issue {issue.severity}'>")
        html.append(f"  <span class='rule'>{issue.rule_id}</span>")
        html.append(f"  <span class='desc'>{issue.description}</span>")
        html.append("</div>")
    html.append("</div>")
    return "\n".join(html)
```

## 故障排查

### mdl 未安装

```
问题：检查返回 "未找到 mdl 工具"
解决：gem install mdl 或 pip install markdownlint-cli
```

### 风格文件未找到

```
问题：风格文件加载失败
解决：使用绝对路径或相对于项目根目录的路径
```

### 编码问题

```
问题：非 UTF-8 文件读取失败
解决：在 check_file() 中指定 encoding 参数
```

## 参考资源

- [markdownlint 官方文档](https://github.com/markdownlint/markdownlint)
- [markdownlint 规则说明](docs/RULES.md)
- [飞书消息卡片文档](https://open.feishu.cn/document/ukTMukTMukTM/uEjNwUjLxYDM14SM2ATN)
