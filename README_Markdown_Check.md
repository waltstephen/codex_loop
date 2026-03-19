# ArgusBot Markdown 检查方案 - 执行摘要

## 项目目标

为 ArgusBot 飞书消息推送提供完整的 Markdown 格式检查和修复能力，确保消息在飞书中正确渲染。

## 实施方案

### 1. 工具整合架构

```
┌─────────────────────────────────────────────────────────────┐
│                  ArgusBot Markdown 检查流程                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  输入 Markdown 文本                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────┐    ┌──────────────────────┐           │
│  │  markdownlint   │    │  飞书自定义验证器     │           │
│  │  (mdl 标准规则)  │    │  (平台特定检查)       │           │
│  └─────────────────┘    └──────────────────────┘           │
│         │                       │                           │
│         └───────────┬───────────┘                           │
│                     ▼                                       │
│          ┌─────────────────────┐                            │
│          │   问题汇总与修复    │                            │
│          └─────────────────────┘                            │
│                     │                                       │
│                     ▼                                       │
│          输出：修复后的 Markdown + 检查报告                    │
└─────────────────────────────────────────────────────────────┘
```

### 2. 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| 飞书验证器 | `feishu_markdown_validator.py` | 修复未闭合代码块、标题换行、列表格式 |
| Markdown 检查器 | `md_checker.py` | 整合 markdownlint 和飞书验证 |
| 风格配置 | `.argusbot/mdl_style.rb` | 定义 Markdown 风格规则 |
| 测试套件 | `test_*.py` | 54 个测试用例 |

### 3. 检查规则

#### markdownlint 标准规则 (40+ 条)
- MD001: 标题级别递增
- MD022: 标题前后空行
- MD031: 代码块前后空行
- MD040: 代码块指定语言
- MD013: 行长度限制

#### 飞书自定义规则 (5 条)
- FEISHU-MD001: 未闭合代码块 (error)
- FEISHU-MD002: 表格语法不支持 (warning)
- FEISHU-MD003: 脚注语法不支持 (warning)
- FEISHU-MD004: 空内容 (error)
- FEISHU-MD005: 标题后缺空行 (warning)

### 4. 使用方法

#### Python API
```python
from codex_autoloop.md_checker import check_markdown, quick_fix_for_feishu

# 快速修复
fixed = quick_fix_for_feishu(markdown_text)

# 完整检查
result = check_markdown(
    text=markdown_text,
    style_file=Path(".argusbot/mdl_style.rb"),
    check_feishu=True,
    auto_fix=True,
)

print(f"飞书就绪：{result.feishu_ready}")
print(f"问题：{result.issues}")
```

#### 命令行
```bash
# 检查文件
python -m codex_autoloop.md_checker README.md

# 输出 JSON 报告
python -m codex_autoloop.md_checker README.md --json
```

### 5. 集成点

#### FeishuNotifier.send_message()
```python
from .md_checker import quick_fix_for_feishu

def send_message(self, message: str) -> bool:
    fixed_message = quick_fix_for_feishu(message)
    # 发送修复后的消息
    ...
```

#### CI/CD 集成
```yaml
# .github/workflows/markdown-check.yml
- name: Check Markdown
  run: mdl -s .argusbot/mdl_style.rb $(git ls-files '*.md')
```

## 测试结果

```
============================== 81 passed in 0.07s ==============================
```

- `test_feishu_markdown_validator.py`: 39 测试 ✅
- `test_md_checker.py`: 15 测试 ✅
- `test_feishu_adapter.py`: 27 测试 ✅

## 安装要求

### 必需
- Python 3.10+

### 可选（完整检查）
```bash
# Ruby 版本
gem install mdl

# 或 Node.js 版本
npm install -g markdownlint-cli
```

## 文件结构

```
ArgusBot/
├── codex_autoloop/
│   ├── md_checker.py              # Markdown 检查器
│   ├── feishu_markdown_validator.py  # 飞书验证器
│   └── feishu_adapter.py          # 飞书适配器 (已修改)
├── .argusbot/
│   └── mdl_style.rb               # 风格配置
├── tests/
│   ├── test_feishu_markdown_validator.py
│   └── test_md_checker.py
├── Markdown_Check_Scheme.md       # 完整方案文档
└── Markdown_Fix_Report.md         # 修复报告
```

## 下一步建议

1. **可选安装 markdownlint**: 在服务器上安装 `mdl` 工具以获得完整检查
2. **配置 CI 检查**: 在 PR 流程中添加 Markdown 检查
3. **监控渲染效果**: 观察飞书消息的实际渲染效果
4. **扩展规则**: 根据实际需求添加自定义规则

## 参考文档

- [完整方案文档](Markdown_Check_Scheme.md)
- [修复报告](Markdown_Fix_Report.md)
- [markdownlint 规则](/Users/halllo/projects/local/markdownlint/docs/RULES.md)
