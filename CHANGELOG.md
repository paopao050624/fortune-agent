# Changelog

## Unreleased（v0.4.0之后）

后续修改记录在此。

## 0.4.0

- 提供8页项目幻灯页、架构说明、演示脚本、合成截图及评估边界；展示包随Release发布。

- 资料库665条原文支持按问题/类别检索，展示匹配原因、缺失书目和固定来源；模型保留必要锚点缩减上下文。
- 结果支持HTML、PNG和浏览器打印PDF导出，默认隐藏明确出生资料，预览可选择来源与隐私字段。
- 扩大20组真实Agent评估，记录失败与复跑；周易必须覆盖全部选文ID，避免简洁提示冲突。
- 八字完成结构与稳健性校准：参数分类冲突时暂停扶抑取用；无专家标签不宣称命理准确率改善。

## 0.3.0（历史版本）

- 统一对话明确确认后复用档案与偏好，资料变更重新确认，切换上下文隔离。
- 新增后台请求阶段、经过时间、合作式取消和保留原牌卦/命盘的重试；公开计费边界。
- 各工具按学习/工作/关系/资源问题组织解读，新增五组真实Agent小样本评估。

- 紫微卷一27条固定修订摘录按宫位/星曜/四化检索，模型引用ID校验，原文由程序展示。
- 塔罗新增78张原创符号SVG牌面、牌背与正逆位视觉；占星新增防重叠可交互轮盘、相位过滤及SVG导出。

- 优化结果阅读：安全排版加粗/标题/列表/表格，优先显示解读与建议，计算细节收起；聊天回答不在依据栏重复。

- 完整网页、HTTP与Docker验证：桌面/手机17组交互、容器构建、Host/token校验及重启持久化；新增可复现脚本和CI任务。
- 修复Docker外部端口映射引起的Host拒绝，支持显式 `--external-port`。
- 档案模式禁用未使用的手填星盘资料，并显示实际计算采用的出生时间。
- 全面同步README、功能文档、安装依赖、存储说明与验证状态；历史版本单独标注。
- 修正对话能力说明和CLI欢迎语，避免将已支持的紫微/占星误称为尚未实现。

## 0.2.0（历史版本）

- 统一Agent：六种工具路由、必要资料补问、稳定追问、重试与会话清除；不假填出生资料。
- 周易：硬币起卦、主变卦与动爻、64卦辞/384爻辞/用九用六参考库，两种取辞策略与校验后的原文呈现。
- 八字：用户四柱输入、月令/藏根/透干观察、禄劫刃及杂气路径、合冲刑害破关系、公开参数的旺衰估计、格局条件与喜用候选。
- 八字时间链：准确出生时间与传统顺逆参数具备时计算起运、十年大运及参考流年；本命与当日干支分开。
- 每日与档案：塔罗和八字综合日报、本地多档案、偏好与经纬度、回顾、导出恢复、删除及显式保存的工具历史。
- 紫微与占星：固定iztro十二宫本命盘、Astronomy Engine十大天体热带整宫制，CLI及统一对话支持。
- 塔罗体验：服务端固定洗牌、78背牌选择、翻牌与原牌追问，单张/三张/对比/五张/凯尔特十字。
- 开源交付：第三方完整许可、Docker本机配置、环境检查命令、贡献和安全文档，以及GitHub发行附件。

发布时部分网页与Docker验证按用户要求跳过；发布后在主分支补充验证并修复。v0.2.0标签和原附件保留发布时内容，详见 [发布记录](docs/release-v0.2.md)。

## 0.1.0（历史版本）

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

以上0.1.0限制记录该历史版本，不代表当前功能。
