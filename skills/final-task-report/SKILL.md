---
name: final-task-report
description: Use when the main execution agent must produce a final Markdown delivery report after the task is complete, especially when reviewer status is done and the report must be saved to a specific local file for human/mobile reading and bot delivery.
---

# Final Task Report

Use this skill only in the final handoff phase.

## Goal

Produce one Markdown report file that a user can read directly on phone or desktop.

The report must stay grounded in the actual work completed in the repository and current session.
Do not invent experiments, datasets, or code changes.

This skill is meant to be updated over time as the reporting format evolves.
Main agent should follow this skill directly for final report generation.

## Required Sections

Always include these sections in order:

1. `## 0. Original User Task` or `## 0. 原始用户任务`
2. `## 1. What This Task Proposed` or `## 1. 本次实验提出了哪些点`
3. `## 2. How It Was Done and What Data Was Used` or `## 2. 具体是怎么做的，使用了什么数据`
4. `## 3. What the Main Agent Changed, What Approach It Used, and What Experiments It Ran` or `## 3. main agent 修改了什么，使用了什么思路，跑了什么实验`
5. `## 4. Special Notes` or `## 4. 特殊说明`

If the task context is mixed-language, bilingual section titles are acceptable.

## Content Rules

1. Summarize only completed work.
2. If no dataset was used, write `未使用` or `none`.
3. If no experiment was run, write `未运行额外实验` or `none`.
4. Include the original user task and any explicit user follow-up requirements.
5. Special Notes should capture:
   - maintenance rules
   - user-visible caveats
   - follow-up constraints
   - any special thing the user explicitly asked to be highlighted
6. Do not infer or mention unrelated internal skill context. User requirements are enough.
7. Prefer the language of the user task:
   - Chinese task -> Chinese report
   - English task -> English report
   - mixed context -> bilingual or mixed headings
8. Prefer concrete evidence:
   - files changed
   - commands/checks run
   - observed outputs
   - validation results
9. Keep it readable on mobile:
   - short paragraphs
   - flat bullets
   - avoid long walls of text

## Write Contract

1. Write to the exact file path requested by the caller.
2. Do not rename the output file.
3. Do not create multiple alternative reports unless explicitly requested.
4. After writing, reply only with the final file path/status if the caller asks for a terse machine-readable response.
