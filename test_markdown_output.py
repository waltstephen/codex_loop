#!/usr/bin/env python3
"""测试 Markdown 输出渲染修复效果。

验证 md_checker 能正确修复常见的 Markdown 格式问题。
"""

from codex_autoloop.md_checker import (
    validate_and_fix_markdown,
    validate_markdown_for_feishu,
    check_unclosed_blocks,
)


def test_case(name: str, text: str) -> None:
    """运行单个测试用例。"""
    print(f"\n{'='*60}")
    print(f"测试：{name}")
    print(f"{'='*60}")
    print("\n原始输入:")
    print(repr(text))
    print("\n原始输入 (渲染):")
    print(text)

    # 检查问题
    issues = check_unclosed_blocks(text)
    valid, all_issues = validate_markdown_for_feishu(text)

    if issues or all_issues:
        print("\n检测到的问题:")
        for issue in issues:
            print(f"  - {issue}")
        for issue in all_issues:
            if issue not in issues:
                print(f"  - {issue}")
    else:
        print("\n未检测到问题")

    # 修复
    fixed = validate_and_fix_markdown(text)

    print("\n修复后:")
    print(repr(fixed))
    print("\n修复后 (渲染):")
    print(fixed)

    # 验证修复结果
    fixed_valid, fixed_issues = validate_markdown_for_feishu(fixed)
    if fixed_issues:
        print("\n修复后仍存在的问题:")
        for issue in fixed_issues:
            print(f"  - {issue}")
    else:
        print("\n修复后无问题!")


def main():
    """运行所有测试用例。"""
    print("=" * 60)
    print("ArgusBot 飞书 Markdown 渲染问题修复验证")
    print("=" * 60)

    # 测试用例 1: JSON 代码块未闭合
    test_case(
        "JSON 代码块未闭合",
        '''reviewer:
{
  "status": "done",
  "confidence": 0.9
}'''
    )

    # 测试用例 2: Markdown 代码块未闭合
    test_case(
        "Markdown 代码块未闭合",
        '''## Round 2 总结

### 完成的工作

```python
def test():
    pass
'''
    )

    # 测试用例 3: 标题后缺少换行
    test_case(
        "标题后缺少换行",
        '''## 标题
内容...'''
    )

    # 测试用例 4: 完整的 Reviewer 输出示例
    test_case(
        "完整的 Reviewer 输出示例",
        '''## Round 2 审核

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

无需后续操作。'''
    )

    # 测试用例 5: 长文本截断
    test_case(
        "长文本（需要截断）",
        "## 总结\n\n" + "- 项目\n" * 100
    )

    # 测试用例 6: 混合 JSON 和 Markdown
    test_case(
        "混合 JSON 和 Markdown",
        '''## 审核结果

```json
{
  "status": "done"
}
```

审核通过，任务完成。'''
    )

    print("\n" + "=" * 60)
    print("验证完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
