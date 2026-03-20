"""测试 Markdown 检查器 - 整合 markdownlint 和飞书验证。"""

import pytest
from pathlib import Path
from codex_autoloop.md_checker import (
    check_markdown,
    check_for_feishu,
    check_with_markdownlint,
    format_check_report,
    quick_fix_for_feishu,
    MarkdownIssue,
)


class TestCheckForFeishu:
    """测试飞书特定检查。"""

    def test_valid_markdown(self):
        """测试有效的 Markdown。"""
        text = """# 标题

内容

- 列表项
- 列表项
"""
        issues = check_for_feishu(text)
        assert len(issues) == 0

    def test_unclosed_code_block(self):
        """测试未闭合代码块检测。"""
        text = """```python
def test():
    pass
"""
        issues = check_for_feishu(text)
        assert any("未闭合" in i.description for i in issues)

    def test_header_missing_newline(self):
        """测试标题后缺少换行检测。"""
        text = """## 标题
内容"""
        issues = check_for_feishu(text)
        assert any("缺少空行" in i.description for i in issues)

    def test_table_not_supported(self):
        """测试表格检测。"""
        text = """| 列 1 | 列 2 |
|------|------|
| 值 1 | 值 2 |"""
        issues = check_for_feishu(text)
        assert any("表格" in i.description for i in issues)

    def test_footnote_not_supported(self):
        """测试脚注检测。"""
        text = """文本[^1]
[^1]: 脚注"""
        issues = check_for_feishu(text)
        assert any("脚注" in i.description for i in issues)


class TestCheckMarkdown:
    """测试完整检查流程。"""

    def test_all_valid(self):
        """测试完全有效的 Markdown。"""
        text = """# 标题

## 子标题

内容

- 列表
- 列表

```python
code
```
"""
        result = check_markdown(text, check_feishu=True)
        assert result.feishu_ready is True

    def test_with_issues(self):
        """测试有问题的 Markdown。"""
        text = """## 标题
内容
```python
code"""
        result = check_markdown(text, check_feishu=True)
        assert result.feishu_ready is False

    def test_auto_fix(self):
        """测试自动修复。"""
        text = """## 标题
内容"""
        result = check_markdown(text, auto_fix=True)
        assert result.fixed_content is not None
        assert "## 标题\n\n内容" in result.fixed_content


class TestQuickFixForFeishu:
    """测试快速修复功能。"""

    def test_fix_trailing_spaces(self):
        """测试移除行尾空格。"""
        text = "内容   \n"
        result = quick_fix_for_feishu(text)
        assert not result.endswith("   \n")

    def test_fix_header_spacing(self):
        """测试标题空格修复。"""
        text = "##标题"
        result = quick_fix_for_feishu(text)
        assert "## " in result

    def test_preserve_valid_content(self):
        """测试保留有效内容。"""
        text = """# 正确的标题

内容
"""
        result = quick_fix_for_feishu(text)
        assert "# 正确的标题" in result


class TestFormatCheckReport:
    """测试报告格式化。"""

    def test_text_format(self):
        """测试文本格式报告。"""
        result = check_markdown("## 标题\n内容", check_feishu=True)
        report = format_check_report(result, "text")
        assert "Markdown 检查" in report

    def test_markdown_format(self):
        """测试 Markdown 格式报告。"""
        result = check_markdown("## 标题\n内容", check_feishu=True)
        report = format_check_report(result, "markdown")
        assert "# Markdown 检查报告" in report

    def test_json_format(self):
        """测试 JSON 格式报告。"""
        result = check_markdown("## 标题\n内容", check_feishu=True)
        report = format_check_report(result, "json")
        import json
        parsed = json.loads(report)
        assert "is_valid" in parsed
        assert "issues" in parsed


class TestMarkdownlintIntegration:
    """测试 markdownlint 集成。"""

    def test_mdl_not_installed(self):
        """测试 mdl 未安装的情况。"""
        text = "# 标题"
        issues = check_with_markdownlint(text, mdl_path="nonexistent_mdl")
        # 应该返回提示信息而不是崩溃
        assert any(
            "未找到" in i.description or "失败" in i.description
            for i in issues
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
