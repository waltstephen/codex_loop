#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书消息卡片测试文件 - 随机内容生成
"""

import json
import random
from datetime import datetime

# 随机内容库
TITLES = [
    "每日报告",
    "系统通知",
    "任务更新",
    "数据摘要",
    "项目进展",
    "测试卡片",
    "随机消息",
    "温馨提醒"
]

TEMPLATES = ["blue", "wathet", "turquoise", "green", "yellow", "orange", "red", "purple"]

CONTENT_POOL = [
    "这是一条自动生成的测试消息卡片",
    "系统运行正常，所有服务都在正常工作",
    "今天的天气不错，适合写代码",
    "任务已完成，请查看详细信息",
    "数据更新成功，共处理 100 条记录",
    "欢迎使用飞书机器人服务",
    "这是一个测试内容，请忽略",
    "代码部署成功，版本 v1.2.3"
]

BUTTON_TEXTS = ["查看详情", "确认", "好的", "了解更多", "立即处理"]


def generate_random_card():
    """生成随机内容的消息卡片"""
    title = random.choice(TITLES)
    template = random.choice(TEMPLATES)
    content_text = random.choice(CONTENT_POOL)
    button_text = random.choice(BUTTON_TEXTS)

    # 随机生成 1-3 个内容元素
    elements = []
    element_count = random.randint(1, 3)

    for i in range(element_count):
        element_type = random.choice(["div", "action", "hr"])

        if element_type == "div":
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": f"[{i+1}] {random.choice(CONTENT_POOL)}"
                }
            })
        elif element_type == "action" and i < element_count - 1:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": random.choice(BUTTON_TEXTS)
                        },
                        "type": random.choice(["primary", "default"]),
                        "value": {"action": "click_" + str(random.randint(1, 100))}
                    }
                ]
            })
        elif element_type == "hr":
            elements.append({"tag": "hr"})

    # 确保最后一个元素是 action（如果有按钮）
    if random.random() > 0.5:
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": button_text
                    },
                    "type": "primary",
                    "value": {"action": "main_action", "timestamp": datetime.now().isoformat()}
                }
            ]
        })

    card = {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"{title} - {random.randint(1000, 9999)}"
            },
            "template": template
        },
        "elements": elements
    }

    return card


def main():
    print("=" * 60)
    print("飞书消息卡片测试生成器")
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # 生成 3 个不同的卡片
    for i in range(3):
        card = generate_random_card()
        content_json = json.dumps(card, ensure_ascii=False, indent=2)

        print(f"--- 卡片 {i+1} ---")
        print(f"标题：{card['header']['title']['content']}")
        print(f"模板颜色：{card['header']['template']}")
        print(f"元素数量：{len(card['elements'])}")
        print()
        print("完整 JSON 内容:")
        print(content_json)
        print()
        print("=" * 60)
        print()


if __name__ == "__main__":
    main()
