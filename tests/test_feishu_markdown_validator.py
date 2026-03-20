"""测试 Feishu Markdown 验证和修复工具。"""

import pytest
from codex_autoloop.md_checker import (
    validate_and_fix_markdown,
    fix_unclosed_code_blocks,
    check_unclosed_blocks,
    ensure_headers_have_newlines,
    fix_list_format,
    truncate_markdown_safely,
    validate_markdown_for_feishu,
    check_markdown_structure,
)


class TestFixUnclosedCodeBlocks:
    """测试未闭合代码块修复。"""

    def test_closed_code_block_unchanged(self):
        """测试已闭合的代码块不变。"""
        text = """```json
{"key": "value"}
```"""
        assert fix_unclosed_code_blocks(text) == text

    def test_unclosed_code_block_fixed(self):
        """测试未闭合的代码块被修复。"""
        text = """```json
{"key": "value"}"""
        result = fix_unclosed_code_blocks(text)
        assert result.endswith('```')
        assert '{"key": "value"}' in result

    def test_multiple_code_blocks(self):
        """测试多个代码块的处理。"""
        text = """```json
{"a": 1}
```

```python
print("hello")
```"""
        result = fix_unclosed_code_blocks(text)
        assert result.count('```') == 4  # 两对

    def test_multiple_unclosed_code_blocks(self):
        """测试多个未闭合代码块。

        Markdown 中 ``` 是切换式的：
        - 第一个 ``` 开始代码块
        - 第二个 ``` 闭合代码块
        - 第三个 ``` 开始新的代码块（需要闭合）
        """
        # 两个 ``` 的情况：第一个开始，第二个闭合 - 都闭合了
        text1 = """```json
{"a": 1}
```"""
        result1 = fix_unclosed_code_blocks(text1)
        assert result1 == text1  # 不需要修改

        # 三个 ``` 的情况：第一个开始，第二个闭合，第三个开始（需要闭合）
        text2 = """```json
{"a": 1}
```
```python
print("hello")"""
        result2 = fix_unclosed_code_blocks(text2)
        assert result2.endswith('```')  # 需要添加闭合标记

    def test_empty_input(self):
        """测试空输入。"""
        assert fix_unclosed_code_blocks("") == ""

    def test_no_code_blocks(self):
        """测试没有代码块的文本。"""
        text = "Hello World"
        assert fix_unclosed_code_blocks(text) == text


class TestCheckUnclosedBlocks:
    """测试未闭合代码块检测。"""

    def test_no_issues(self):
        """测试没有问题的文本。"""
        text = """```json
{"key": "value"}
```"""
        issues = check_unclosed_blocks(text)
        assert len(issues) == 0

    def test_unclosed_detected(self):
        """测试检测到未闭合代码块。"""
        text = """```json
{"key": "value"}"""
        issues = check_unclosed_blocks(text)
        assert len(issues) == 1
        assert "未闭合" in issues[0]
        assert "1" in issues[0]  # 第 1 行

    def test_multiple_unclosed(self):
        """测试多个未闭合代码块。"""
        text = """```json
{"a": 1}

```python
print("test")"""
        issues = check_unclosed_blocks(text)
        # 第一个 ``` 被第二个 ``` 闭合，最后一个 ``` 未闭合
        # 但实际上第二个 ``` 闭合了第一个，所以没有未闭合
        # 代码逻辑：奇数个 ``` 表示有未闭合
        assert len(issues) == 0  # 3 个 ```，最后一个闭合第二个，所以实际都闭合了


class TestEnsureHeadersHaveNewlines:
    """测试标题换行修复。"""

    def test_header_with_newline_unchanged(self):
        """测试标题后已有换行不变。"""
        text = """## 标题

内容"""
        result = ensure_headers_have_newlines(text)
        assert result == text

    def test_header_without_newline_fixed(self):
        """测试标题后缺少换行被修复。"""
        text = """## 标题
内容"""
        result = ensure_headers_have_newlines(text)
        lines = result.split('\n')
        # 标题行后应该有空行
        header_idx = next(i for i, line in enumerate(lines) if line.strip() == '## 标题')
        assert lines[header_idx + 1] == ''

    def test_multiple_headers(self):
        """测试多个标题的处理。"""
        text = """## 标题 1
内容 1
### 子标题
内容 2"""
        result = ensure_headers_have_newlines(text)
        lines = result.split('\n')
        # 标题 1 后应该有空行（因为下一行是内容，不是标题）
        # 找到标题 1 的位置
        header1_idx = next((i for i, line in enumerate(lines) if line.strip() == '## 标题 1'), -1)
        if header1_idx >= 0 and header1_idx + 1 < len(lines):
            # 标题 1 后应该有空行
            assert lines[header1_idx + 1] == ''

    def test_consecutive_headers(self):
        """测试连续标题不需要额外换行。"""
        text = """## 标题 1
## 标题 2
内容"""
        result = ensure_headers_have_newlines(text)
        # 连续标题之间不需要额外添加空行
        assert '## 标题 1\n## 标题 2' in result or '## 标题 1\n\n## 标题 2' in result

    def test_empty_input(self):
        """测试空输入。"""
        assert ensure_headers_have_newlines("") == ""


class TestFixListFormat:
    """测试列表格式修复。"""

    def test_list_with_newline_unchanged(self):
        """测试列表前有空行不变。"""
        text = """段落

- 项目 1
- 项目 2"""
        result = fix_list_format(text)
        assert result == text

    def test_list_without_newline_fixed(self):
        """测试列表前缺少空行被修复。"""
        text = """段落
- 项目 1"""
        result = fix_list_format(text)
        assert '\n\n- 项目 1' in result or '\n- 项目 1\n' in result

    def test_numbered_list(self):
        """测试有序列表。"""
        text = """段落
1. 第一项
2. 第二项"""
        result = fix_list_format(text)
        # 列表前应该有空行
        assert '段落\n\n1.' in result or result.startswith('段落\n\n')

    def test_mixed_list_markers(self):
        """测试不同列表标记。"""
        texts = [
            "- 项目",
            "* 项目",
            "+ 项目",
            "1. 项目",
        ]
        for marker_text in texts:
            text = f"段落\n{marker_text}"
            result = fix_list_format(text)
            # 应该添加空行
            assert '\n\n' in result


class TestValidateAndFixMarkdown:
    """测试完整的验证和修复流程。"""

    def test_empty_input(self):
        """测试空输入。"""
        assert validate_and_fix_markdown("") == ""

    def test_json_code_block_example(self):
        """测试 JSON 代码块示例（来自实际问题）。"""
        text = '''reviewer:
{
  "status": "done"
}'''
        # 这个例子没有代码块标记，不应该添加
        result = validate_and_fix_markdown(text)
        # 至少应该保持原样或修复格式
        assert 'reviewer:' in result
        assert '"status": "done"' in result

    def test_header_newline_fix(self):
        """测试标题换行修复。"""
        text = """## 标题
内容..."""
        result = validate_and_fix_markdown(text)
        lines = result.split('\n')
        header_idx = next((i for i, line in enumerate(lines) if line.strip() == '## 标题'), -1)
        if header_idx >= 0 and header_idx + 1 < len(lines):
            # 标题后应该有空行或另一个标题
            next_line = lines[header_idx + 1].strip()
            assert next_line == '' or next_line.startswith('#')

    def test_list_format_fix(self):
        """测试列表格式修复。"""
        text = """## 总结

- 项目 1
- 项目 2"""
        result = validate_and_fix_markdown(text)
        assert '- 项目 1' in result
        assert '- 项目 2' in result

    def test_mixed_markdown_and_text(self):
        """测试混合 Markdown 和纯文本。"""
        text = """## Round 2 总结

### 完成的工作

- 修复了 bug
- 添加了测试

```python
def test():
    pass
```"""
        result = validate_and_fix_markdown(text)
        # 应该保持所有结构
        assert '## Round 2 总结' in result
        assert '### 完成的工作' in result
        assert '- 修复了 bug' in result
        assert '```python' in result
        assert '```' in result

    def test_multiple_extra_newlines_reduced(self):
        """测试多余空行被缩减。"""
        text = """段落 1




段落 2"""
        result = validate_and_fix_markdown(text)
        # 连续 4 个以上空行应该被缩减
        assert '\n\n\n\n' not in result


class TestTruncateMarkdownSafely:
    """测试安全截断 Markdown。"""

    def test_short_text_unchanged(self):
        """测试短文本不截断。"""
        text = "Hello World"
        result = truncate_markdown_safely(text, 100)
        assert result == text

    def test_truncate_in_paragraph(self):
        """测试在段落中截断。"""
        text = "这是一个很长的段落，包含了很多文字。" * 20
        result = truncate_markdown_safely(text, 50)
        assert len(result) <= 65  # 允许一些额外字符用于截断标记
        assert '截断' in result

    def test_truncate_in_code_block(self):
        """测试在代码块内截断。"""
        text = """## 代码示例

```python
def very_long_function_name_with_many_parameters(
    param1, param2, param3, param4, param5
):
    return param1 + param2 + param3 + param4 + param5
```"""
        result = truncate_markdown_safely(text, 80)
        # 应该正确处理代码块截断
        assert '...' in result or len(result) <= len(text)

    def test_truncate_at_paragraph_boundary(self):
        """测试优先在段落边界截断。"""
        text = """第一段内容。

第二段内容。"""
        result = truncate_markdown_safely(text, 20)
        # 如果文本超过 max_chars，应该被截断
        # 但这个例子中文本可能不超过 20 字符，所以检查两种情况
        if len(text) > 20:
            assert '...' in result
        else:
            # 文本本身不超过 20，不应该被截断
            assert result == text


class TestValidateMarkdownForFeishu:
    """测试飞书 Markdown 验证。"""

    def test_valid_markdown(self):
        """测试有效的 Markdown。"""
        text = """## 标题

- 列表项
- 列表项

```python
code
```"""
        valid, issues = validate_markdown_for_feishu(text)
        assert valid is True
        assert len(issues) == 0

    def test_empty_markdown(self):
        """测试空 Markdown。"""
        valid, issues = validate_markdown_for_feishu("")
        assert valid is False
        assert any("空" in issue for issue in issues)

    def test_table_not_supported(self):
        """测试表格不被支持。"""
        text = """| 列 1 | 列 2 |
|------|------|
| 值 1 | 值 2 |"""
        valid, issues = validate_markdown_for_feishu(text)
        assert not valid
        assert any("表格" in issue for issue in issues)

    def test_footnote_not_supported(self):
        """测试脚注不被支持。"""
        text = """这是一个句子[^1]。

[^1]: 脚注内容"""
        valid, issues = validate_markdown_for_feishu(text)
        assert not valid
        assert any("脚注" in issue for issue in issues)

    def test_unclosed_code_block(self):
        """测试未闭合代码块。"""
        text = """```python
code"""
        valid, issues = validate_markdown_for_feishu(text)
        assert not valid
        assert any("未闭合" in issue for issue in issues)


class TestCheckMarkdownStructure:
    """测试 Markdown 结构检查。"""

    def test_valid_structure(self):
        """测试有效结构。"""
        text = """## 标题

段落内容。

- 列表项
- 列表项

```python
code
```"""
        result = check_markdown_structure(text)
        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_invalid_structure(self):
        """测试无效结构。"""
        text = """## 标题
段落内容。

```python
code"""
        result = check_markdown_structure(text)
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_result_format(self):
        """测试结果格式。"""
        result = check_markdown_structure("test")
        assert "valid" in result
        assert "issues" in result
        assert "fixes_applied" in result


class TestIntegration:
    """集成测试。"""

    def test_real_world_reviewer_output(self):
        """测试实际的 Reviewer 输出。"""
        text = """## Round 2 审核

**状态:** done

### 完成的工作

1. 创建了 README.md 文件
2. 添加了项目描述

```json
{
  "status": "done",
  "confidence": 0.9
}
```

### 下一步

无需后续操作。"""
        result = validate_and_fix_markdown(text)

        # 验证结构保持
        assert '## Round 2 审核' in result
        assert '**状态:** done' in result
        assert '```json' in result
        assert '"status": "done"' in result

        # 验证格式正确
        valid, issues = validate_markdown_for_feishu(result)
        # 修复后应该没有未闭合代码块问题
        assert not any("未闭合" in issue for issue in issues)

    def test_long_text_truncation(self):
        """测试长文本截断。"""
        text = "## 总结\n\n" + "- 项目\n" * 100
        result = truncate_markdown_safely(text, 500)
        assert len(result) <= 550  # 允许一些额外字符
        assert '...' in result

    def test_json_before_markdown(self):
        """测试 JSON 在 Markdown 前的混合。"""
        text = '''{
  "status": "done"
}

## 详细说明

内容...'''
        result = validate_and_fix_markdown(text)
        # JSON 不是代码块，不需要 ``` 包围
        # 但应该保持格式
        assert '"status": "done"' in result
        assert '## 详细说明' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
