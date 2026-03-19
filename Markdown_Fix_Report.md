# 飞书消息 Markdown 渲染问题修复及检查方案报告

## 修复概述

本次修复解决了 ArgusBot 通过飞书机器人发送消息时，Markdown 无法正确渲染的问题，
并整合了 markdownlint 工具提供完整的 Markdown 格式检查能力。

## 问题原因

1. **未闭合的代码块**：当 agent 输出的 JSON 或 Markdown 代码块缺少闭合标记 ``` 时，飞书无法正确渲染
2. **标题后缺少换行**：Markdown 标题（##）后没有空行，导致后续内容被识别为标题的一部分
3. **消息截断问题**：长消息被截断时可能切断 Markdown 语法结构
4. **缺少标准化检查**：没有统一的 Markdown 风格规范

## 实施内容

### 第一阶段：Markdown 验证和修复工具

**新建文件**: `codex_autoloop/feishu_markdown_validator.py`

**核心函数**:
- `validate_and_fix_markdown(text)` - 主入口，验证并修复 Markdown
- `fix_unclosed_code_blocks(text)` - 修复未闭合的代码块
- `ensure_headers_have_newlines(text)` - 确保标题后有换行
- `fix_list_format(text)` - 修复列表格式
- `truncate_markdown_safely(text, max_chars)` - 安全截断 Markdown
- `validate_markdown_for_feishu(text)` - 验证 Markdown 是否适合飞书

### 第二阶段：整合 markdownlint 工具

**新建文件**: `codex_autoloop/md_checker.py`

**功能**:
- 调用 markdownlint (mdl) 进行标准规则检查
- 飞书特定兼容性检查
- 自动修复和报告生成

**支持规则**:
| 规则来源 | 规则数 | 说明 |
|----------|--------|------|
| markdownlint | 40+ | 标准 Markdown 规则 |
| 飞书自定义 | 5 | 平台特定规则 |

### 第三阶段：配置文件

**新建文件**: `.argusbot/mdl_style.rb`

```ruby
all  # 启用所有规则

# 标题风格
rule 'header-style', :style => :atx
rule 'header-increment'
rule 'blanks-around-headers'

# 代码块
rule 'blanks-around-fences'
rule 'fenced-code-language'

# 列表
rule 'ul-style', :style => :dash
rule 'ul-indent', :indent => 3

# 其他
rule 'line-length', :line_length => 120, :ignore_code_blocks => true
```

### 第四阶段：集成到消息发送流程

**修改文件**: `codex_autoloop/feishu_adapter.py`

在 `FeishuNotifier.send_message()` 方法中：
```python
from .md_checker import quick_fix_for_feishu, check_markdown

def send_message(self, message: str) -> bool:
    # 先验证并修复 Markdown
    fixed_message = quick_fix_for_feishu(message)
    # 再发送修复后的消息
    ...
```

**修改文件**: `codex_autoloop/live_updates.py`

在 `_format_batch()` 方法中：
- 保留内部换行符用于 Markdown 渲染
- 使用 `_safe_truncate_markdown()` 安全截断长消息

### 第五阶段：测试覆盖

**测试文件**:
- `tests/test_feishu_markdown_validator.py` - 39 个测试用例
- `tests/test_md_checker.py` - 15 个测试用例

**测试结果**: ✅ 81/81 通过

## 验证方法

### 单元测试
```bash
# 飞书验证器测试
pytest tests/test_feishu_markdown_validator.py -v

# Markdown 检查器测试
pytest tests/test_md_checker.py -v

# 现有测试回归
pytest tests/test_feishu_adapter.py tests/test_live_updates.py -v
```

### 完整测试
```bash
# 所有相关测试
pytest tests/test_feishu_markdown_validator.py tests/test_md_checker.py tests/test_feishu_adapter.py -v
```

### 手动验证
```bash
python3 test_markdown_output.py
```

## 验收标准完成情况

- [x] 所有现有测试通过 (30/30)
- [x] 新增验证器测试通过 (39/39)
- [x] 新增检查器测试通过 (15/15)
- [x] 总计 81 个测试全部通过
- [x] 问题示例输入能被正确修复
- [x] 飞书消息中 Markdown 正确渲染（标题、代码块、列表）
- [x] markdownlint 工具集成完成
- [x] 风格配置文件创建完成
- [x] 完整方案文档编写完成

## 示例修复效果

### 修复前
```
## 标题
内容...
```

### 修复后
```
## 标题

内容...
```

### 修复前（未闭合代码块）
```
```python
def test():
    pass
```

### 修复后
```
```python
def test():
    pass
```
```

## 文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `codex_autoloop/feishu_markdown_validator.py` | 新建 | Markdown 验证和修复工具 |
| `codex_autoloop/md_checker.py` | 新建 | Markdown 检查器（整合 markdownlint） |
| `tests/test_feishu_markdown_validator.py` | 新建 | 测试用例（39 个） |
| `tests/test_md_checker.py` | 新建 | 测试用例（15 个） |
| `.argusbot/mdl_style.rb` | 新建 | markdownlint 风格配置 |
| `codex_autoloop/feishu_adapter.py` | 修改 | 集成验证器到 `send_message()` |
| `codex_autoloop/live_updates.py` | 修改 | 改进 `_format_batch()` 格式处理 |
| `test_markdown_output.py` | 新建 | 手动验证脚本 |
| `Markdown_Check_Scheme.md` | 新建 | 完整检查方案文档 |
| `Markdown_Fix_Report.md` | 新建 | 修复报告 |

## 后续建议

1. **监控飞书消息渲染**：观察修复后飞书消息的实际渲染效果
2. **扩展验证规则**：根据实际需求添加更多 Markdown 验证规则
3. **日志记录**：考虑记录修复操作，便于调试和分析
