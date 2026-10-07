# Fortune Agent v0.5.0

v0.5.0 将 Fortune Agent 的核心能力整理为可安装的 Codex Skill，并增加了从全新目录安装和运行的自动验证。

## 主要内容

- 新增 `skills/fortune-agent`，支持塔罗、每日一张、八字、周易、紫微斗数、西方占星、资料检索和 HTML/SVG 报告导出。
- 新增 `scripts/install_codex_skill.py`，一条命令安装 Skill，并自动绑定当前源码目录。
- 新增 `scripts/smoke_codex_skill.py`，离线验证抽牌、八字、资料检索和报告导出。
- GitHub Actions 纳入 Skill 安装检查和冒烟测试。
- Skill 不携带中转站密钥、`.env`、用户档案或本机运行路径。

## 安装

```bash
git clone https://github.com/paopao050624/fortune-agent.git
cd fortune-agent
python -m pip install -e '.[all]'
python scripts/install_codex_skill.py
```

重新打开 Codex 会话后可使用 `$fortune-agent`。项目模型解读仍需自行设置 `FORTUNE_API_KEY`、`FORTUNE_BASE_URL` 和 `FORTUNE_MODEL`；本地排盘、抽牌和资料检索无需 API。

## 边界

Skill 调用项目已有的确定性计算和资料库，不把传统象征解释当作现实事件保证。八字、紫微和占星的时区、换日、宫制及资料版本边界见项目使用指南。
