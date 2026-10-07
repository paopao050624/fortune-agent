# 工具参数

以下 `RUN` 表示 `python <skill目录>/scripts/run_fortune.py`，不是实际可执行文件。跨目录调用可加全局参数 `--project <源码目录>`，必须放在 action 之前。源码或 Python 包依赖必须安装在执行脚本的同一个 Python 环境中。

```bash
RUN doctor
RUN tarot '如何安排毕业论文？' --spread three --json
RUN daily --profile demo --timezone Asia/Shanghai --json
RUN bazi --birth 2000-01-01T12:00:00+08:00 --gender female --complete --json
RUN bazi --pillars '己卯 丙子 戊午 戊午' --daily --date 2026-10-07 --json
RUN iching --lines 7 8 9 8 7 6 --policy moving-count-v1 --json
RUN iching --reference 1 --json
RUN chart ziwei --birth 2000-01-01T12:00:00+08:00 --gender female
RUN chart astrology --birth 2000-01-01T12:00:00+08:00 --timezone Asia/Shanghai --latitude 31.23 --longitude 121.47
RUN library '财格' --module bazi --limit 5
RUN export /absolute/bazi-result.json /absolute/report.html --mode bazi
RUN export /absolute/tarot-result.json /absolute/report.svg --mode tarot --format svg
```

示例出生资料仅用于测试，不可当作用户资料。工具 CLI `--help` 显示全部参数。塔罗牌阵可选 single/three/decision/five/celtic；`--pick` 为洗牌后的1–78位置，同一读牌不要因不满意而反复重抽。每日一张离线计算不保存解读；使用 `--interpret` 才调用中转站并缓存。

塔罗离线结果不自带原文依据，需 `library` 按返回的实际牌名检索；每日牌同理。紫微也可用 library 按实际宫位/星曜补查。若未找到正逆位对应原文，明确表示缺失，不套用另一个方向冒充原书含义。

## 档案与综合日报（按用户保存要求使用）

```bash
RUN profile save --profile demo --birth 2000-01-01T12:00:00+08:00 --gender female --store /absolute/fortune.sqlite3
RUN profile report --profile demo --date 2026-10-07 --store /absolute/fortune.sqlite3
RUN profile history --profile demo --store /absolute/fortune.sqlite3
```

`profile report` 首次会缓存塔罗＋八字综合报告；档案出生信息在本地 SQLite 保存，不默认匿名化。代号不要使用真名。跨目录使用显式绝对 `--store` 路径，避免默认相对 work 路径生成多个档案库。导出、导入、回顾和删除的具体参数用 `RUN profile --help` 检查；不要在无相关请求时执行。

## 项目模型解读（可选）

需要继承的 `FORTUNE_API_KEY`、`FORTUNE_BASE_URL`、`FORTUNE_MODEL`；项目不会自动加载 `.env`，Skill 也不加载它。塔罗/daily 的 `--interpret` 是布尔开关，八字/周易/chart 的 `--interpret '问题'` 需要问题文本。默认由 Codex 根据本地事实解释，无需再次请求 API。

检索仅覆盖当前已接入文本，不等于完整藏书或向量检索；结果返回缺失书目提示。报告导出沿用项目有限字段过滤，包含解读的自由文本仍需检查是否夹带私人资料，公开分享前审阅。
