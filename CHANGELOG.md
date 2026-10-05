# Changelog

## Unreleased

- Add source-traced natal structural analysis: seasonal month context, exact-stem versus same-element hidden-root observations, month-stem transmission and pattern-study candidates.
- Preserve root-strength and final pattern/useful-god uncertainty, separating program facts from unimplemented full judgment rules.
- Add explicit daily Ba Zi reference pillars and ten-god relationships at a documented China-standard-time noon reference, with CLI, web and conversational support.
- Keep natal and daily data separate, disclose solar-term boundary limits, and avoid unsupported daily luck scores or promises.
- Add a unified conversational agent with model tool routing, required-data clarification, stable followups and in-memory expiring sessions.
- Add local web chat, tool traces, clear/new conversation controls and an interactive `fortune-chat` command.
- Preserve prepared artifacts after model failures and validate birth data against user messages before execution.
- Add three-coin I Ching casting, six user-supplied line totals, moving lines, and main/changed hexagrams in the CLI and local web interface.
- Add the complete 64 judgments, 384 line texts and Qian/Kun special passages with per-page fixed source revisions and variant notes.
- Add seven moving-count cases and an alternative all-moving-lines policy, offline reference lookup, structured model interpretation and validated passage IDs.
- Accept user-supplied four pillars in the CLI and local web interface.
- Validate individual pillars against the sexagenary cycle and explicitly preserve unknown birth time, timezone, solar terms, and day-boundary conventions.
- Reuse source-linked interpretation and relationship calculations without inventing a birth date or claiming the supplied chart is calendar-verified.

## 0.1.0

First local prototype. This is a development release, not a complete implementation of all planned divination systems.

- Complete 78-card tarot deck, one-card and three-card spreads, automatic and selected draws.
- Relay-compatible Responses API interpretation with direct and gentle styles.
- Traceable Waite card meanings and fixed comparative evaluation cases.
- Daily tarot card by profile, local date, and timezone, with first-interpretation caching.
- Four pillars for China standard time, explicit day-boundary rules, calculated ten-god and hidden-stem relationships.
- Limited, source-linked excerpts from Di Tian Sui and Zi Ping Zhen Quan.
- Financial-pattern method checklist that keeps unresolved conditions explicit.
- Local browser interface for tarot, daily tarot, and four-pillar calculations.
- Offline tests, reproducible evaluation fixtures, and package build workflow.

Known limits: no complete strength, pattern, useful-god, or luck-cycle calculation; no Zi Wei Dou Shu, I Ching, or Western astrology; no public deployment or account system. Real evaluations are small, reviewed samples. The browser layout still requires visual acceptance in a supported browser environment.

## 未发布：八字特殊月令规则

- 增加建禄、阴干月劫、五阳干阳刃的研究路径映射。
- 增加辰戌丑未杂气月的透干与完整三合支字证据筛选。
- 保留原文异文和未核实条件，不自动判合化、旺衰、成格或喜用神。

## 未发布：干支关系观察

- 新增显干五合、地支六合冲害破、相刑、自刑重复支及三刑支字齐备观察。
- 保留柱位、方向、多项关系重叠与根气／候选关联，未判断关系效力。
- 网页、统一对话和命令行共用程序结果；关系规则纳入参考库哈希。

## 未发布：综合报告与每日运势

- 新增八字旺衰证据、分方法取用和大运流年报告。最终判断缺条件时仍未确定。
- 准确出生时间与用户提供的传统顺逆参数具备时，按分钟折算起运，按精确起运周年选择当前大运。
- 新增本地档案、塔罗与八字综合日报、历史回顾、导出与删除，统一对话复用保存档案。
- 新增 fortune-report 命令与网页入口，离线可用；模型失败不保存空日报。

## 未发布：八字判断模型 v1

- 新增项目旺衰估计及六情景敏感性检查，公开权重和阈值。
- 新增格局配合、风险、救应与禄劫刃条件规则，新增10个扫描核对短段。
- 新增扶抑候选、通用月支调候方向、方法冲突与特殊从化筛选。
- 网页、统一对话和综合日报复用计算结果；模型估计与古籍最终效力分别标注。
