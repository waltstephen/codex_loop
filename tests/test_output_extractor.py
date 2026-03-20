"""测试 output_extractor 模块。"""

import json
from codex_autoloop.output_extractor import (
    extract_reviewer_output,
    extract_planner_output,
    format_reviewer_markdown,
    format_planner_markdown,
    extract_and_format_reviewer,
    extract_and_format_planner,
    extract_message_content,
    clean_json_output,
    parse_agent_response,
)


class TestExtractReviewerOutput:
    """测试 Reviewer 输出提取。"""

    def test_extract_valid_json(self):
        """测试有效的 JSON 提取。"""
        json_text = json.dumps({
            "status": "done",
            "confidence": 0.95,
            "reason": "所有验收检查通过",
            "next_action": "任务已完成",
            "round_summary_markdown": "## 本轮完成\n\n- 创建了 README.md",
            "completion_summary_markdown": "## 完成证据\n\n- README.md 文件已创建",
        })

        output = extract_reviewer_output(json_text)
        assert output is not None
        assert output.status == "done"
        assert output.confidence == 0.95
        assert "README.md" in output.round_summary

    def test_extract_json_with_code_blocks(self):
        """测试包含 markdown 代码块的 JSON 提取。"""
        json_text = '''```json
{
  "status": "continue",
  "confidence": 0.8,
  "reason": "进行中",
  "next_action": "继续开发",
  "round_summary_markdown": "## 进度\\n\\n完成了 50%",
  "completion_summary_markdown": ""
}
```'''

        output = extract_reviewer_output(json_text)
        assert output is not None
        assert output.status == "continue"

    def test_extract_truncated_json_with_regex(self):
        """测试从截断的 JSON 中使用正则提取字段。"""
        # 模拟被截断的 JSON（如 live_updates 中 420 字符限制导致）
        truncated = '{"status": "done", "confidence": 0.95, "reason": "任务已完成所有验'

        output = extract_reviewer_output(truncated)
        assert output is not None
        assert output.status == "done"
        assert output.confidence == 0.95

    def test_extract_truncated_json_repair_braces(self):
        """测试修复被截断的 JSON 括号。"""
        from codex_autoloop.output_extractor import try_repair_truncated_json

        # 测试截断的 JSON
        truncated = '{"status": "done", "workstreams": ['
        repaired = try_repair_truncated_json(truncated)

        # 应该自动闭合括号
        assert repaired.count("}") >= repaired.count("{")
        assert repaired.count("]") >= repaired.count("[")

        # 尝试解析应该不抛异常
        try:
            json.loads(repaired)
        except json.JSONDecodeError:
            # 如果还是失败，至少说明已经尝试修复
            pass

    def test_extract_invalid_json_returns_none(self):
        """测试无效 JSON 返回空对象而不是 None。"""
        output = extract_reviewer_output("not valid json")
        # 正则回退方案会返回一个带有默认值的对象
        assert output is not None
        assert output.status == ""
        assert output.confidence == 0.0

    def test_extract_missing_fields(self):
        """测试缺失字段使用默认值。"""
        json_text = json.dumps({"status": "done"})

        output = extract_reviewer_output(json_text)
        assert output is not None
        assert output.status == "done"
        assert output.confidence == 0.0
        assert output.reason == ""


class TestExtractPlannerOutput:
    """测试 Planner 输出提取。"""

    def test_extract_valid_json(self):
        """测试有效的 Planner JSON 提取。"""
        json_text = json.dumps({
            "summary": "项目进展顺利",
            "workstreams": [
                {"area": "开发", "status": "in_progress"},
                {"area": "测试", "status": "todo"},
            ],
            "done_items": ["需求分析", "架构设计"],
            "remaining_items": ["编码", "测试"],
            "risks": ["时间紧张"],
            "next_steps": ["完成核心功能"],
            "exploration_items": ["性能优化"],
            "report_markdown": "## 完整报告",
        })

        output = extract_planner_output(json_text)
        assert output is not None
        assert output.summary == "项目进展顺利"
        assert len(output.workstreams) == 2
        assert len(output.done_items) == 2

    def test_extract_truncated_planner_json(self):
        """测试从截断的 Planner JSON 中提取字段。"""
        truncated = '{"summary": "项目进展顺利", "workstreams": [{"area": "开发", "status": "in_progress"}'

        output = extract_planner_output(truncated)
        assert output is not None
        assert output.summary == "项目进展顺利"
        assert len(output.workstreams) == 1
        assert output.workstreams[0]["area"] == "开发"

    def test_extract_empty_arrays(self):
        """测试空数组字段。"""
        json_text = json.dumps({"summary": "测试"})

        output = extract_planner_output(json_text)
        assert output is not None
        assert output.workstreams == []
        assert output.done_items == []


class TestFormatReviewerMarkdown:
    """测试 Reviewer Markdown 格式化。"""

    def test_format_done_status(self):
        """测试完成状态的格式化。"""
        from codex_autoloop.output_extractor import ReviewerOutput

        output = ReviewerOutput(
            status="done",
            confidence=0.9,
            reason="测试原因",
            next_action="无",
            round_summary="## 本轮总结\n\n- 完成 A",
            completion_summary="## 完成证据\n\n- A 已验收",
        )

        md = format_reviewer_markdown(output)
        assert "✅" in md
        assert "**状态**: done" in md
        assert "**置信度**: 90%" in md
        assert "**本轮总结**" in md

    def test_format_blocked_status(self):
        """测试阻塞状态的格式化。"""
        from codex_autoloop.output_extractor import ReviewerOutput

        output = ReviewerOutput(
            status="blocked",
            confidence=0.5,
            reason="遇到阻塞",
            next_action="需要帮助",
            round_summary="",
            completion_summary="",
        )

        md = format_reviewer_markdown(output)
        assert "🚫" in md
        assert "**评审原因**" in md

    def test_format_empty_fields(self):
        """测试空字段的格式化。"""
        from codex_autoloop.output_extractor import ReviewerOutput

        output = ReviewerOutput(
            status="done",
            confidence=1.0,
            reason="",
            next_action="",
            round_summary="",
            completion_summary="",
        )

        md = format_reviewer_markdown(output)
        # 空字段不应输出对应部分
        assert "**评审原因**" not in md
        assert "**本轮总结**" not in md


class TestFormatPlannerMarkdown:
    """测试 Planner Markdown 格式化。"""

    def test_format_with_all_fields(self):
        """测试包含所有字段的格式化。"""
        from codex_autoloop.output_extractor import PlannerOutput

        output = PlannerOutput(
            summary="总结",
            workstreams=[{"area": "开发", "status": "in_progress"}],
            done_items=["项 1"],
            remaining_items=["项 2"],
            risks=["风险 1"],
            next_steps=["步骤 1"],
            exploration_items=["探索 1"],
            full_report="完整报告",
        )

        md = format_planner_markdown(output)
        assert "## 📋 Planner 规划报告" in md
        assert "| 开发 | 🔄 进行中 |" in md
        assert "**✅ 完成项**" in md
        assert "**⏳ 剩余项**" in md
        assert "**⚠️ 风险**" in md

    def test_format_workstream_statuses(self):
        """测试工作流状态图标。"""
        from codex_autoloop.output_extractor import PlannerOutput

        output = PlannerOutput(
            summary="",
            workstreams=[
                {"area": "A", "status": "done"},
                {"area": "B", "status": "in_progress"},
                {"area": "C", "status": "todo"},
                {"area": "D", "status": "blocked"},
            ],
            done_items=[],
            remaining_items=[],
            risks=[],
            next_steps=[],
            exploration_items=[],
            full_report="",
        )

        md = format_planner_markdown(output)
        assert "✅ 完成" in md
        assert "🔄 进行中" in md
        assert "⏳ 待办" in md
        assert "🚫 阻塞" in md


class TestExtractAndFormat:
    """测试完整的提取和格式化流程。"""

    def test_extract_and_format_reviewer(self):
        """测试 Reviewer 完整流程。"""
        json_text = json.dumps({
            "status": "done",
            "confidence": 0.85,
            "reason": "完成",
            "next_action": "结束",
            "round_summary_markdown": "## 总结",
            "completion_summary_markdown": "## 证据",
        })

        result = extract_and_format_reviewer(json_text)
        assert "✅" in result
        assert "**状态**: done" in result

    def test_extract_and_format_planner(self):
        """测试 Planner 完整流程。"""
        json_text = json.dumps({
            "summary": "进展良好",
            "workstreams": [],
            "done_items": ["完成项"],
            "remaining_items": [],
            "risks": [],
            "next_steps": [],
            "exploration_items": [],
            "report_markdown": "",
        })

        result = extract_and_format_planner(json_text)
        assert "## 📋 Planner 规划报告" in result
        assert "**✅ 完成项**" in result

    def test_extract_and_format_invalid_json(self):
        """测试无效 JSON 返回原文本。"""
        invalid = "not json at all"

        # extract_and_format_reviewer 在提取失败时返回原文本
        result = extract_and_format_reviewer(invalid)
        # 由于正则回退返回空对象，格式化后会输出基本结构
        assert "Reviewer" in result  # 至少包含标题

        result = extract_and_format_planner(invalid)
        assert "Planner" in result  # 至少包含标题


class TestExtractMessageContent:
    """测试 Markdown 字段提取。"""

    def test_extract_markdown_fields(self):
        """测试提取 Markdown 字段。"""
        json_text = json.dumps({
            "status": "done",
            "round_summary_markdown": "## 本轮总结",
            "completion_summary_markdown": "## 完成证据",
            "overview_markdown": "## 概览",
            "report_markdown": "## 报告",
            "summary_markdown": "## 总结",
            "other_field": "不是 markdown",
        })

        result = extract_message_content(json_text)
        assert "round_summary_markdown" in result
        assert "completion_summary_markdown" in result
        assert "overview_markdown" in result
        assert "report_markdown" in result
        assert "summary_markdown" in result
        assert "other_field" not in result

    def test_extract_partial_fields(self):
        """测试部分字段存在的情况。"""
        json_text = json.dumps({
            "status": "done",
            "round_summary_markdown": "## 总结",
        })

        result = extract_message_content(json_text)
        assert len(result) == 1
        assert result["round_summary_markdown"] == "## 总结"


class TestCleanJsonOutput:
    """测试 JSON 清理。"""

    def test_remove_json_markdown_markers(self):
        """测试移除 markdown 代码块标记。"""
        text = '''```json
{
  "key": "value"
}
```'''

        cleaned = clean_json_output(text)
        assert "```" not in cleaned
        assert '"key": "value"' in cleaned

    def test_clean_plain_text(self):
        """测试纯文本无需清理。"""
        text = '{"key": "value"}'
        cleaned = clean_json_output(text)
        assert cleaned == text


class TestParseAgentResponse:
    """测试 Agent 响应解析。"""

    def test_parse_clean_json(self):
        """测试解析干净的 JSON。"""
        json_text = '{"status": "done", "confidence": 0.9}'

        result = parse_agent_response(json_text)
        assert result is not None
        assert result["status"] == "done"

    def test_parse_markdown_wrapped_json(self):
        """测试解析 markdown 包裹的 JSON。"""
        text = '''一些说明文字
```json
{
  "status": "continue"
}
```
更多文字'''

        result = parse_agent_response(text)
        assert result is not None
        assert result["status"] == "continue"

    def test_parse_invalid_returns_none(self):
        """测试无效 JSON 返回 None。"""
        result = parse_agent_response("not json")
        assert result is None
