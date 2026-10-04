# Fortune Agent

一个逐步构建的塔罗与每日运势 Agent 项目。目前包含可测试的塔罗抽牌工具、通过兼容 OpenAI Responses API 的中转站运行的解牌 Agent、可追溯的 Waite 原书牌义，以及限定中国标准时间的八字四柱排盘原型。紫微、易经与西方占星尚未实现。

当前版本为 **v0.1 本地原型**。首次安装、配置和演示步骤见 [v0.1 使用说明](docs/release-v0.1.md)，开发流程见 [CONTRIBUTING](CONTRIBUTING.md)。

## 运行

需要 Python 3.10 或以上。只运行抽牌工具不需要第三方依赖。

```bash
PYTHONPATH=src python -m fortune_agent.cli "今天的学习状态如何？"
PYTHONPATH=src python -m fortune_agent.cli "这个项目该怎么推进？" --spread three --pick 1 15 78
PYTHONPATH=src python -m fortune_agent.cli "今天的学习状态如何？" --json
PYTHONPATH=src python -m unittest discover -s tests
```

使用 `--pick` 时，数字是洗牌后的牌堆位置。正逆位独立随机决定。JSON 输出保留抽牌事实，供后续解牌工具和 Agent 使用。

## 本地网页

在项目根目录启动：

```bash
python -m pip install -e '.[agent,bazi]'
fortune-web
```

浏览器打开 `http://127.0.0.1:8765`，可选择塔罗问答、每日一张牌或八字排盘。默认只在本机抽牌或计算，勾选“生成模型解读”才使用中转站；中转站环境变量应在启动服务的终端设置，密钥不通过浏览器输入或返回。源码运行也可用 `PYTHONPATH=src python -m fortune_agent.web`。

网页仅监听本机回环地址，供单人体验使用，尚未实现账户和公网部署。每日解读与命令行共用 `work/daily.sqlite3`（可用 `--cache` 指定固定路径）；塔罗问题与出生资料不保存。模型回答以文字展示，原文与来源可展开查看。关闭服务按 `Ctrl+C`，换端口可用 `fortune-web --port 8766`。

## 每日一张牌

每日模式以**塔罗一张牌**为唯一依据，暂不使用八字、紫微、易经或出生资料。使用固定的自选代号和 IANA 时区，例如：

```bash
PYTHONPATH=src python -m fortune_agent.daily_cli --profile reader-01 --timezone Asia/Shanghai
PYTHONPATH=src python -m fortune_agent.daily_cli --profile reader-01 --timezone Asia/Shanghai --interpret
```

安装项目后也可运行 `fortune-daily --profile reader-01 --timezone Asia/Shanghai --interpret`。同一代号、时区和当地日期会得到相同牌面。牌面由稳定哈希生成，属于可复现的伪随机抽牌，不是对未来的确定性计算。解读使用现有中转站环境变量；首次解读缓存在当前目录的 `work/daily.sqlite3`，之后同日直接返回缓存，即使改用不同回答风格或模型也保留当天首次结果。请从同一项目目录运行，或用 `--cache` 指定固定路径。缓存不保存原始代号，但会保存牌面、解读及来源，可删除该文件清除本地记录。请用非个人信息作为代号；代号不会发送给模型。`--json` 可输出结构化结果。

当前是单机原型。若部署成多人服务，需要以认证后的用户 ID 区分记录，并隔离各用户的缓存；自填代号不能充当账户认证。

## 八字四柱原型

八字模块使用 `lunar-python 1.4.8` 计算年、月、日、时四柱。第一版只接受公历出生时刻、`Asia/Shanghai` 时区及明确的 `+08:00` 偏移；采用节气换年换月、库的 `sect 2` 子时规则（23:00 后日柱仍按当日，00:00 换日），不做真太阳时校正。出生地暂不参与计算。详细约定见 [八字排盘方法](docs/bazi.md)。例子：

```bash
python -m pip install -e '.[bazi]'
fortune-bazi --birth 2000-01-01T12:00:00+08:00
fortune-bazi --birth 2000-01-01T12:00:00+08:00 --json
```

如需模型解释，安装 `.[agent,bazi]` 并设置下文的中转站环境变量，再运行 `fortune-bazi --birth 2000-01-01T12:00:00+08:00 --interpret '学习上应注意什么？'`。出生时间和排盘结果会发送至中转站，命令不会保存出生资料。程序提供《滴天髓辑要》相关原文，以及《子平真诠》的五个扫描核对短段；`--sources` 可离线查看资料，`--details` 查看十神和藏干，`--analysis` 查看 [财格方法条件清单](docs/bazi-wealth-checklist.md)。版本与校勘限制见 [八字古籍资料](docs/bazi-sources.md) 和 [子平真诠摘录](docs/ziping-transcription.md)，计算规则见 [十神与藏干](docs/bazi-facts.md)。《渊海子平》等其他典籍尚未接入。未知出生时刻、海外出生或要求真太阳时校正的情况暂不支持，不应拿默认时刻代替真实时刻。

八字解读的固定案例与人工复核标准见 [八字解释评估](docs/bazi-evaluation.md)。12 例真实请求的结果和限制见 [八字评估报告](evals/results/bazi-review-2026-10-04.md)，新增关系与方法资料的验证见 [月令与关系报告](evals/results/bazi-context-review-2026-10-04.md)。

要启用中转站解牌，先安装可选依赖，并在自己的终端设置中转站的密钥、API 根地址和模型名称：

```bash
python -m pip install -e '.[agent]'
export FORTUNE_API_KEY='你的中转站密钥'
export FORTUNE_BASE_URL='https://你的中转站域名/v1'
export FORTUNE_MODEL='中转站提供的模型名称'
fortune-agent "这个项目该怎么推进？" --spread three --interpret --style direct
```

`FORTUNE_BASE_URL` 填 API 根地址（通常以 `/v1` 结尾），不要填完整的 `/responses` 请求地址。当前 Agent 使用 Responses API 和函数工具调用；中转站需要支持这两项。`--style` 支持 `direct`（直接）和 `gentle`（温和）。`--json` 会同时输出抽牌事实和模型解读。密钥只从环境变量读取；代码发起请求时设置 `store=False`，但实际数据保存策略由中转站决定。问题和抽牌结果会发送到中转站，请勿输入不愿发送的个人信息。

有来源的牌会附上 Waite 原书扫描页链接。当前 78/78 张牌均有来源；原书未给出逆位释义的方向会明确标注，不会冒充原书依据。评估案例与运行方法见 [塔罗解读评估](docs/evaluation.md)。

如果收到 `model_not_found`，请在中转站后台核对该密钥所属分组的模型授权和实际可用通道；`/models` 列出的模型不一定都能在当前分组调用。

## 产品边界

- 每日运势、塔罗和八字应分别标明采用的规则，不把多个体系混成无法核查的结论。
- 用户想要的两种风格实现为“直接”和“温和”；“直接”表示措辞清楚，不表示对未来作确定性保证。
- 八字排盘必须由历法程序完成，模型只负责解释。出生时间、地点或流派规则不明时应显示不确定性。
- 出生信息和提问可能涉及隐私。未来接入存储时默认最小化保存，并提供删除方式。
- 结果用于反思与娱乐，不替代医疗、法律或财务等专业判断。

## 路线图

1. **已完成：塔罗抽牌核心。** 78 张牌、单张及三张牌阵、用户选牌、自动抽牌和测试。
2. **已完成：塔罗解读 Agent 与 20 例对照评估。** 模型通过工具获得抽牌结果；无资料与有出处资料各运行 20 例。78 张牌均有原书页码，原书缺失的个别逆位释义会明确标记。逐例评分与限制见 [评估报告](evals/results/review-2026-10-03.md)。
3. **已完成第一版：每日一张塔罗牌。** 按用户时区确定日期，同日牌面固定、首次解读本地缓存。未来可加入用户主动选择的其他依据与交互界面。
4. **八字四柱原型已完成；紫微与其他体系待开发。** 八字先限定中国标准时间，展示节气和换日规则；后续验证更多边界并建立有出处的古籍解释资料。
5. **本地网页已完成；开源发布待完成。** 网页整合三种体验；后续增加部署说明与贡献指南。项目使用 MIT 许可证。

候选典籍及使用规则见 [资料与方法](docs/references.md)。已注明的 Waite 塔罗资料、《滴天髓》和《子平真诠》有限摘录已接入；其他典籍仍在规划中。

GitHub 发布状态与本地提交记录以 Git 仓库为准；当前还没有配置远程仓库。自动测试工作流已准备，需推送后由 GitHub 执行。
