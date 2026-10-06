# Fortune Agent

[![Tests and package](https://github.com/paopao050624/fortune-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/paopao050624/fortune-agent/actions/workflows/tests.yml)

一个用于Agent实战的开源塔罗、八字、紫微斗数与占星项目。模型选择工具、补问资料并解释实际计算结果；牌面、历法和天体位置由程序生成，追问默认复用同一次结果。

最新正式发布为 **[v0.3.0](https://github.com/paopao050624/fortune-agent/releases/tag/v0.3.0)**。发行包功能见 [v0.3发布说明](docs/release-v0.3.md)，下文以主分支为准；历史标签与下载包保留各自发布时内容。安装与各模块约定见 [使用指南](docs/charts-and-profiles.md)，历史版本见 [CHANGELOG](CHANGELOG.md)。

## 已实现的功能

| 功能 | 当前内容 | 使用说明 |
| --- | --- | --- |
| 统一对话 | 六种工具路由、确认档案复用、实际进度、取消/原任务重试与稳定追问 | [对话流程](docs/unified-agent.md) |
| 塔罗问答 | 78张牌、单张／三张／选择对比／五张／凯尔特十字，原创符号牌图、背牌选取、翻牌和原牌追问 | [塔罗体验](docs/charts-and-profiles.md#塔罗交互) |
| 每日一张 | 按代号、时区与当地日期确定固定牌面，首次模型解读本地缓存 | 下文“每日提示与综合日报” |
| 每日运势与回顾 | 档案关联的塔罗＋八字参考、大运流年依据、日报缓存、历史回顾 | [综合报告](docs/complete-fortune.md) |
| 八字 | 中国标准时间排盘、十神藏干、结构关系、项目旺衰估计、格局条件和分方法取用、大运流年 | [判断模型及边界](docs/bazi-judgment.md) |
| 紫微斗数 | 固定iztro本命十二宫、星曜四化、27条电子原文匹配及校验解读 | [排盘约定](docs/charts-and-profiles.md#紫微斗数) |
| 西方占星 | 十大天体、热带黄道、地心位置、整宫宫位、角点、主要相位和逆行，可交互轮盘与SVG导出 | [占星约定](docs/charts-and-profiles.md#西方占星) |
| 用户档案 | 多代号、出生资料与经纬度、偏好、显式保存工具历史、导出恢复与删除 | [保存与隐私](docs/charts-and-profiles.md#档案) |
| 周易 | 三枚硬币起卦、主变卦与动爻，两种取辞策略，64卦全文参考库 | [起卦](docs/iching.md)／[解读](docs/iching-interpretation.md) |

## 安装与启动

Python包要求 **Python 3.10+**；CI验证Python 3.11与3.13，推荐使用3.11+。紫微运行需要 **Node.js 18+**；紫微排盘桥已打包，普通使用不需要安装npm依赖。

```bash
git clone https://github.com/paopao050624/fortune-agent.git
cd fortune-agent
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[all]'
fortune-doctor
fortune-web --port 8766
```

浏览器打开 `http://127.0.0.1:8766/`。默认进入统一对话，另有七个手动功能页。`fortune-web`不指定端口时使用8765。Node不在PATH时可以设置 `FORTUNE_NODE` 为完整可执行路径。

本机计算、选牌、档案和资料查看不需要API密钥。统一对话和勾选模型解读时会使用中转站，需在启动服务的终端设置环境变量：

```bash
export FORTUNE_API_KEY='你的中转站密钥'
export FORTUNE_BASE_URL='https://你的中转站域名/v1'
export FORTUNE_MODEL='中转站实际支持的完整模型ID'
```

模型接口使用Responses API；塔罗与统一对话还需要函数工具调用。不要把完整 `/responses` 地址填作API根地址。应用不自动读取 `.env`，示例字段见 [.env.example](.env.example)。密钥不通过网页输入或返回，也不要提交到Git。请求使用 `store=False`，但中转站保存政策仍由服务商决定。

## 常用命令

```bash
# 只抽牌，不调用模型
fortune-agent '怎样安排学习？' --spread three --pick 1 15 78 --json
fortune-agent '比较两种项目方向' --spread decision --interpret --style direct

# 八字综合报告；准确出生时间和传统顺逆参数具备时才计算大运
fortune-bazi --birth 2000-01-01T12:00:00+08:00 --gender female --complete --json
fortune-bazi --pillars '己卯 丙子 戊午 戊午' --structure
fortune-bazi --pillars '己卯 丙子 戊午 戊午' --daily --date 2026-10-06

# 紫微与西方占星
fortune-chart ziwei --birth 2000-01-01T12:00:00+08:00 --gender female
fortune-chart astrology --birth 2000-01-01T12:00:00+00:00 --timezone Europe/London --latitude 51.4779 --longitude 0

# 周易起卦与完整参考库
fortune-iching --lines 9 9 9 9 9 9
fortune-iching --reference 1

# 命令行统一对话
fortune-chat --profile reader-01 --timezone Asia/Shanghai
```

直接输入八字四柱时，只核验每柱的六十甲子合法性，不声称四柱已按同一出生时间校验；缺日期和时辰不能让模型假填。八字、紫微的换日及闰月约定分别展示，不混为一种历法规则。

## 每日提示与综合日报

**“每日一张”**和 `fortune-daily` 只使用固定塔罗牌。相同代号、时区和日期产生相同牌面；首次模型解读存入 `work/daily.sqlite3`，同日沿用首次回答与风格，次日也可能出现相同牌。代号用非个人信息即可；这份缓存不保存原始代号。

**“每日运势与回顾”**和 `fortune-report` 使用显式保存的档案。没有八字资料时只用塔罗；有资料时加入当天干支、本命关系以及具备起运资料时的大运流年。结合八字的日报目前仅支持Asia/Shanghai，纯塔罗支持其他IANA时区。

```bash
fortune-report save --profile demo --birth 2000-01-01T12:00:00+08:00 --gender female
fortune-report report --profile demo --date 2026-10-06
fortune-report history --profile demo
fortune-report export --profile demo
```

综合日报保存在 `work/fortune.sqlite3`。相同资料、日期和规则版本保存首次报告；首次离线保存后不会因为再次勾选模型偷偷生成第二份当天报告。修改资料或规则产生新版本，历史保留原快照。详情见 [综合日报](docs/complete-fortune.md)。

## 数据与隐私

- 单次手动八字和星盘计算不默认保存出生资料；用户主动保存档案或勾选保存工具历史时，相关资料、问题及结果会写入本机数据库。
- 档案数据库明文保存，文件权限600。导出的JSON可能包含出生资料；提供删除、导出和导入恢复。自填代号不是账户认证。
- 对话暂存在本机内存，最多20轮、闲置1小时过期。清除对话不删除档案、综合日报或独立每日塔罗缓存。
- 模型请求发送相关问题、出生资料、实际计算结果与来源；本地回顾内容不发送给模型。模型措辞支持直接／温和，但不保证未来事件。
- 默认服务仅监听本机地址；Docker内部显式绑定0.0.0.0，Compose只向127.0.0.1发布端口。没有公网账户认证，不作为多人公共服务直接暴露。

## 来源与能力边界

塔罗已有Waite原书78张牌的出处，圣杯二逆位原书缺少对应释义，页面明确标注。周易包含64卦辞、384爻辞及乾坤用九用六，使用固定电子修订与公开取辞约定。

八字参考库包含《滴天髓辑要》相关短段和《子平真诠》21个扫描核对短段。判断层的量化权重、阈值及条件代理是公开的工程近似，不是古籍统一标准；特殊从化、经典调候及各派差异保留复核。《渊海子平》《三命通会》《穷通宝鉴》和《紫微斗数全书》未完成指定底本全文校勘，不编造未接入原文和页码。

西方占星固定十大天体、热带黄道与整宫制，不包含所有宫制、小行星或合盘。天文位置与软件计算可验证，不代表占卜预测效力已经验证。结果用于反思参考，不替代医疗、法律或财务专业判断。详见 [资料与方法](docs/references.md)。

## 验证与部署

```bash
python -W error::ResourceWarning -m unittest discover -s tests -v
# Docker本机部署
docker compose up --build -d
```

完整测试包括HTTP请求；CI还运行桌面／手机浏览器验收、Docker构建、请求防护与重启数据持久化。最近补充验证见 [网页与Docker报告](evals/results/web-docker-review-2026-10-06.md)；模型相关浏览器场景使用明确测试替身，不把它报告为中转站实时可用性。

复现命令见 [CONTRIBUTING](CONTRIBUTING.md)，容器端口和数据卷说明见 [部署指南](docs/charts-and-profiles.md#docker本机部署)。项目已发布GitHub Release，尚未发布到PyPI，也没有部署成公共网站。软件与第三方依赖的授权见 [LICENSE](LICENSE) 和 [第三方许可](THIRD_PARTY_NOTICES.md)。

本批紫微原文的版本与解释链见 [紫微依据](docs/ziwei-evidence.md)；塔罗78张符号牌面为项目原创MIT资产，非原版Waite图像。

对话中的档案复用需要先预览确认；模型请求显示实际阶段并可合作式取消、复用原结果重试。见 [Agent体验与评估](docs/agent-experience.md)。
