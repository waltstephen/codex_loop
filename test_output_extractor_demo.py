#!/usr/bin/env python3
"""测试 Reviewer/Planner 输出提取器效果。"""

import json
from codex_autoloop.output_extractor import (
    extract_and_format_reviewer,
    extract_and_format_planner,
)
from codex_autoloop.feishu_adapter import format_feishu_event_card

# ============= 测试 Reviewer 输出提取 =============
print("=" * 60)
print("测试 Reviewer 输出提取")
print("=" * 60)

reviewer_json = json.dumps({
    "status": "done",
    "confidence": 0.95,
    "reason": "所有验收检查通过，文件已成功创建",
    "next_action": "任务已完成，无需进一步操作",
    "round_summary_markdown": "## 本轮完成\n\n- 创建了 README.md 文件\n- 添加了项目介绍\n- 配置了安装说明",
    "completion_summary_markdown": "## 完成证据\n\n```bash\n$ ls -la README.md\n-rw-r--r-- 1 user user 1234 Jan 1 12:00 README.md\n```",
}, ensure_ascii=False)

print("\n原始 JSON 输出:")
print(reviewer_json[:200] + "...")

formatted_reviewer = extract_and_format_reviewer(reviewer_json)
print("\n格式化后的 Markdown:")
print(formatted_reviewer)

# 测试事件卡片格式
event = {
    "type": "reviewer.output",
    "raw_output": reviewer_json,
}
card_result = format_feishu_event_card(event)
if card_result:
    title, content, template = card_result
    print(f"\n飞书卡片标题：{title}")
    print(f"模板颜色：{template}")

# ============= 测试 Planner 输出提取 =============
print("\n" + "=" * 60)
print("测试 Planner 输出提取")
print("=" * 60)

planner_json = json.dumps({
    "summary": "项目整体进展顺利，核心功能已完成 80%",
    "workstreams": [
        {"area": "需求分析", "status": "done"},
        {"area": "架构设计", "status": "done"},
        {"area": "核心开发", "status": "in_progress"},
        {"area": "单元测试", "status": "todo"},
        {"area": "文档编写", "status": "todo"},
    ],
    "done_items": [
        "完成需求分析文档",
        "确定技术栈和架构",
        "实现核心数据模型",
        "搭建基础项目结构",
    ],
    "remaining_items": [
        "完成 API 接口实现",
        "集成测试",
        "性能优化",
        "部署脚本",
    ],
    "risks": [
        "第三方 API 可能有限制",
        "性能要求较高需要优化",
    ],
    "next_steps": [
        "完成剩余的 API 端点",
        "开始编写单元测试",
        "准备部署环境",
    ],
    "exploration_items": [
        "研究缓存策略",
        "评估监控方案",
    ],
    "report_markdown": "## 完整报告\n\n详见上文。",
}, ensure_ascii=False)

print("\n原始 JSON 输出:")
print(planner_json[:200] + "...")

formatted_planner = extract_and_format_planner(planner_json)
print("\n格式化后的 Markdown:")
print(formatted_planner)

# 测试事件卡片格式
event = {
    "type": "planner.output",
    "raw_output": planner_json,
}
card_result = format_feishu_event_card(event)
if card_result:
    title, content, template = card_result
    print(f"\n飞书卡片标题：{title}")
    print(f"模板颜色：{template}")

print("\n" + "=" * 60)
print("测试完成!")
print("=" * 60)
