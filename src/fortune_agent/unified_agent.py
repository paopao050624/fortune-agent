"""Model-directed routing, deterministic tools, clarification and stable followups."""
from dataclasses import asdict, dataclass, replace
from copy import deepcopy
from datetime import datetime, timezone
import json
import re
from zoneinfo import ZoneInfo

from .agent import TarotAgent
from .bazi import calculate_bazi, parse_bazi_pillars
from .bazi_analysis import comprehensive_analysis
from .bazi_agent import interpret_bazi
from .bazi_facts import chart_facts
from .bazi_rules import wealth_checklist
from .bazi_daily import daily_bazi_context
from .bazi_structure import analyze_structure
from .bazi_sources import evidence_for as bazi_evidence
from .daily import daily_draw
from .fortune_store import FortuneStore
from .fortune_daily import make_daily_report, report_identity
from .daily_service import get_daily
from .daily_store import DailyStore
from .iching import build_cast, cast_coins
from .iching_agent import interpret_cast
from .iching_reading import select_passages
from .meanings import evidence_for
from .tarot import draw_reading

ROUTER_INSTRUCTIONS = """你是统一占卜助手的意图与资料路由器，只调用 choose_action，不自行起卦、抽牌或排盘。
支持 tarot（塔罗）、daily（每日提示；存在已保存档案时整合塔罗与八字）、bazi（八字）和 iching（周易）。紫微和西方占星尚未实现。
今天运势等泛化当日问题默认 daily，但明确指定其他方式时遵循用户选择。没有指定方式且不是每日问题时，clarify 询问想用塔罗、八字或周易，不擅自替用户选择。
明确要求每日八字或用八字看今天时选 bazi，沿用本方式已收集资料；普通今日提示才用 daily 塔罗。每日八字只算当天干支与本命日主关系，不能承诺吉凶。
用户只说算塔罗或起卦但没有具体问题，clarify 追问。问题足够具体则 read；塔罗未选牌阵采用 three。
八字可以提供完整四柱或准确出生时间。只提取用户实际给出的信息，未说时辰不得填午夜，未说日期不得编造日期。
将明确出生日期时间规范为 ISO 8601；仅当前支持的中国标准时间可用 +08:00，用户没确认时区时 birth_timezone=unknown 并追问。
直接四柱按年、月、日、时提供；不凭姓名、性别或年份推断缺失柱。birth 和 pillars 不同时填。
slots 是以前从用户收集的资料，可用于补全。fields 为 null 表示没有新信息，不删除旧资料。
active_result 存在时，解释已有结果、进一步建议、为何抽到某牌等选 followup。默认不重抽、不改命盘；用户明确重抽/重新起卦或转到新方式才 read。
同一周易卦切换取辞策略必须 followup 并设置 policy，不重新起卦；每日牌的小步骤追问也必须 followup，不能只重复缓存的首条回答。
收到资料补充而没有重复问题时，使用 slots.question 保留此前问题。如果用户改出生资料，应 read 重新核对。
用户可选择 direct/gentle，默认 gentle；直接不意味着确定性预测。不能承诺未来、诊断、停药、投资或胜诉结果。
你好、功能介绍等用 answer，简短说明。超出已实现模块用 unsupported，明确限制。澄清 reply 简短且一次只问当前必要资料。
每日代号及时区来自页面设置，不要从用户文字编造。六次硬币值与选牌位置只提取明确数字，不能为了读卦自己填随机数。
输出 question 是用户的问题或已确认问题；未获得具体问题时为 null。所有模型输出都会再次被程序校验。"""

ROUTE_SCHEMA = {"type":"object","additionalProperties":False,"properties":{
    "action":{"type":"string","enum":["read","followup","clarify","answer","unsupported"]},
    "method":{"type":"string","enum":["none","tarot","daily","bazi","iching"]},
    "question":{"type":["string","null"]}, "birth":{"type":["string","null"]},
    "pillars":{"type":["string","null"]},
    "birth_timezone":{"type":["string","null"],"enum":["Asia/Shanghai","unknown","unsupported",None]},
    "spread":{"type":["string","null"],"enum":["single","three",None]},
    "picks":{"type":["array","null"],"items":{"type":"integer"}},
    "lines":{"type":["array","null"],"items":{"type":"integer"}},
    "policy":{"type":["string","null"],"enum":["moving-count-v1","all-moving-v1",None]},
    "style":{"type":["string","null"],"enum":["direct","gentle",None]},
    "reply":{"type":"string"}},
    "required":["action","method","question","birth","pillars","birth_timezone","spread","picks","lines","policy","style","reply"]}
ROUTE_TOOL = {"type":"function","name":"choose_action","description":"Choose the supported tool or ask for missing information.",
              "parameters":ROUTE_SCHEMA,"strict":True}


def validate_route(route):
    if not isinstance(route,dict) or set(route)!=set(ROUTE_SCHEMA["required"]):
        raise ValueError("路由输出结构无效")
    for key,schema in ROUTE_SCHEMA["properties"].items():
        value=route[key]
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"路由字段 {key} 无效")
        if key in ("picks","lines"):
            if value is not None and (not isinstance(value,list) or len(value)>6 or any(type(v) is not int for v in value)):
                raise ValueError("选牌或六爻输入无效")
        elif value is not None and (not isinstance(value,str) or len(value)>2000):
            raise ValueError(f"路由字段 {key} 无效")
    return route


def birth_matches_user_text(birth,history):
    try: instant=datetime.fromisoformat(birth)
    except (ValueError,TypeError): return False
    dates={(int(y),int(m),int(d)) for y,m,d in re.findall(
        r"(\d{4})\s*(?:年|[-/.])\s*(\d{1,2})\s*(?:月|[-/.])\s*(\d{1,2})",history)}
    without_offsets=re.sub(r"[+-]\d{2}:\d{2}","",history)
    clocks={(int(h),int(m)) for h,m in re.findall(r"(\d{1,2})\s*[:：]\s*(\d{2})",without_offsets)}
    digits={"一":1,"二":2,"两":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"零":0}
    for period,hour,minute in re.findall(r"(上午|下午|晚上|中午|早上|凌晨)?\s*([\d一二三四五六七八九十两]+)\s*(?:点|時|时)(?:\s*(\d{1,2})分)?",without_offsets):
        if hour.isdigit(): h=int(hour)
        elif "十" in hour:
            tens,ones=hour.split("十",1);h=digits.get(tens,1)*10+digits.get(ones,0)
        else:h=digits.get(hour,-1)
        if period in ("下午","晚上") and 0<=h<12:h+=12
        if period=="凌晨" and h==12:h=0
        clocks.add((h,int(minute) if minute else 0))
    return (instant.year,instant.month,instant.day) in dates and (instant.hour,instant.minute) in clocks


@dataclass
class Artifact:
    method: str
    question: str
    domain: object
    data: dict
    policy: str = "moving-count-v1"


class UnifiedAgent:
    def __init__(self, client, model, cache_path, daily_lock):
        self.client,self.model,self.cache_path,self.daily_lock=client,model,cache_path,daily_lock

    def decide(self,session,content):
        active = None
        if session.artifact:
            active={"method":session.artifact.method,"question":session.artifact.question,
                    "data":{key:value for key,value in session.artifact.data.items() if key not in ("review","profile_key","key")}}
        context={"reference_date":datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(),
                 "slots":session.slots,"active_result":active,
                 "recent_messages":session.messages[-12:],"user_message":content}
        response=self.client.responses.create(model=self.model,instructions=ROUTER_INSTRUCTIONS,
            input=[{"role":"user","content":json.dumps(context,ensure_ascii=False)}],
            tools=[ROUTE_TOOL],tool_choice={"type":"function","name":"choose_action"},parallel_tool_calls=False,store=False)
        calls=[item for item in response.output if item.type=="function_call"]
        if len(calls)!=1 or calls[0].name!="choose_action":
            raise RuntimeError("模型未选择有效工具；请重试")
        try:
            return validate_route(json.loads(calls[0].arguments))
        except (ValueError,TypeError) as exc:
            raise RuntimeError("模型路由数据无效，未执行工具") from exc

    def turn(self,session,message,profile="reader-01",zone="Asia/Shanghai"):
        if not isinstance(message,str) or not message.strip() or len(message)>2000:
            raise ValueError("消息须为 1–2000 个字符")
        message=message.strip()
        if len(session.messages)>=40:
            raise ValueError("本次对话已满 20 轮，请开启新对话")
        route=self.decide(session,message)
        model_action=route["action"]
        trace=[{"tool":"choose_action","action":route["action"],"method":route["method"]}]
        method=route["method"]
        if method=="none": method=session.slots.get("method","none")
        if method!=session.slots.get("method") and method!="none":
            preferred_style=session.slots.get("style")
            session.slots={"method":method}
            if preferred_style:session.slots["style"]=preferred_style
            session.artifact=None
        old_input=(session.slots.get("birth"),session.slots.get("pillars"))
        for key in ("question","birth","pillars","birth_timezone","spread","picks","lines","policy","style"):
            if route[key] is not None:
                session.slots[key]=route[key]
        if route["birth"] is not None: session.slots.pop("pillars",None)
        if route["pillars"] is not None: session.slots.pop("birth",None)
        if method=="bazi":
            if re.search(r"今天|今日|每日|当日",message):
                session.slots["daily_bazi"]=True
            elif re.search(r"取消每日|不看当天|只看本命",message):
                session.slots.pop("daily_bazi",None)
            if session.artifact and bool(session.artifact.data.get("daily_context"))!=bool(session.slots.get("daily_bazi")):
                session.artifact=None
        if method=="bazi" and session.slots.get("_awaiting_birth_timezone") and re.fullmatch(r"(?:是|是的|对|对的|确认|没错|按这个时区)[。！!\s]*",message):
            session.slots["birth_timezone"]="Asia/Shanghai"
            session.slots["_birth_timezone_user_confirmed"]=True
            session.slots.pop("_awaiting_birth_timezone",None)
            route["action"]="read"
        if old_input!=(session.slots.get("birth"),session.slots.get("pillars")) and method=="bazi":
            session.artifact=None
        if session.artifact and not session.artifact.data.get("interpretation") and route["action"]=="read":
            if not re.search(r"重抽|重新抽|重新起卦|再抽|新问题|重新掷",message):
                route["action"]="followup"
        if session.artifact and session.artifact.method==method and route["action"]=="read":
            same_result_request=re.search(r"同一|这次|这个卦|这张|第二张|第一张|第三张|已有|沿用|保持|更具体|小步骤|进一步|追问|换.*并读|换.*取辞",message)
            policy_change=method=="iching" and route["policy"] and route["policy"]!=session.artifact.policy
            if (same_result_request or policy_change) and not re.search(r"重抽|重新抽|重新起卦|再抽|重新掷",message):
                route["action"]="followup"
        trace[0].update({"action":route["action"],"model_action":model_action})

        def finish(reply,result=None,status="completed"):
            session.messages.extend([{"role":"user","content":message},{"role":"assistant","content":reply[:6000]}])
            return {"session_id":session.id,"reply":reply,"status":status,"method":method,
                    "trace":trace,"result":deepcopy(result),"turns":len(session.messages)//2}

        if route["action"] in ("answer","unsupported"):
            reply=("紫微斗数与西方占星目前尚未实现。可以使用塔罗、每日提示、八字或周易。"
                   if route["action"]=="unsupported" else route["reply"] or "可以问我塔罗、每日提示、八字或周易问题。")
            return finish(reply,status="answered")

        if route["action"]=="followup" and session.artifact and session.artifact.method==method:
            if method=="iching" and route["policy"]:
                session.artifact.policy=route["policy"]
                selection=select_passages(session.artifact.domain,route["policy"])
                session.artifact.data.update({"selection":selection,"evidence":selection["passages"]})
            if method=="daily":
                current=daily_draw(profile,zone)
                if (session.artifact.data["day"]!=current.day or session.artifact.data["timezone"]!=zone
                    or session.artifact.data.get("profile_key")!=current.cache_key):
                    session.artifact=None
                if session.artifact and session.artifact.data.get("mode")=="daily-report":
                    from pathlib import Path
                    store=FortuneStore(Path(self.cache_path).parent / "fortune.sqlite3")
                    try: expected_key=report_identity(store,profile)[3]
                    except ValueError: expected_key=None
                    if expected_key!=session.artifact.data.get("key"):session.artifact=None
            if session.artifact:
                if method=="bazi" and session.slots.get("daily_bazi"):
                    current=daily_bazi_context(session.artifact.domain)
                    session.artifact.data["daily_context"]=current
                context=self.followup_question(session,message)
                result=self.explain(session.artifact,context,session.slots.get("style","gentle"),
                                    include_hexagram_context=bool(re.search(r"主卦|变卦",message)))
                result["followup"]=True
                trace.append({"tool":"explain_existing_result","method":method,"reused":True})
                return finish(result["interpretation"],result)

        slots=session.slots
        question=slots.get("question")
        if method=="none":
            return finish("你想用塔罗、八字还是周易？如果只想看今天的提示，可以选择每日一张。",status="needs_input")
        if method in ("tarot","iching") and not question:
            return finish("你想梳理什么具体问题？例如学习安排、工作选择或沟通分歧。",status="needs_input")
        if method=="bazi":
            if not slots.get("birth") and not slots.get("pillars"):
                return finish("请提供完整四柱（年、月、日、时），或准确的公历出生日期、时刻和时区。暂仅支持中国标准时间排盘；未知时辰请不要假填。",status="needs_input")
            if slots.get("birth") and slots.get("birth_timezone")!="Asia/Shanghai":
                slots["_awaiting_birth_timezone"]=True
                return finish("出生时区尚未确认。你的出生时刻是否按中国标准时间（+08:00）记录？其他地区排盘当前不支持。",status="needs_input")
            # A model assertion alone cannot establish the user confirmed a timezone.
            history="\n".join([m["content"] for m in session.messages if m["role"]=="user"]+[message])
            if slots.get("pillars"):
                try:
                    candidate=parse_bazi_pillars(slots["pillars"])
                except ValueError as exc:
                    return finish(f"资料需要修正：{exc}",status="needs_input")
                wanted=candidate.year+candidate.month+candidate.day+candidate.hour
                supplied="".join(re.findall(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]",history))
                if wanted not in supplied:
                    return finish("请完整写出年、月、日、时四柱；我不能补出你未提供的干支。",status="needs_input")
            if slots.get("birth"):
                if not birth_matches_user_text(slots["birth"],history):
                    return finish("请补充准确的公历出生年月日和时刻；不能用默认日期或午夜代替未知资料。也可以直接提供完整四柱。",status="needs_input")
            if slots.get("birth") and not slots.get("_birth_timezone_user_confirmed") and not re.search(r"中国标准|北京时间|东八区|Asia/Shanghai|\+08:00|北京|上海",history):
                slots["_awaiting_birth_timezone"]=True
                return finish("请明确确认出生时刻是中国标准时间（+08:00）；页面中的每日时区不会用来推断出生时区。",status="needs_input")
        if route["action"]=="clarify":
            return finish(route["reply"] or "请补充需要分析的资料或具体问题。",status="needs_input")

        try:
            artifact=self.prepare(method,question or "请解释四柱及已有依据。",slots,profile,zone)
        except ValueError as exc:
            return finish(f"资料需要修正：{exc}",status="needs_input")
        session.artifact=artifact  # Keep the actual result even if interpretation times out.
        trace.append({"tool":{"tarot":"draw_tarot","daily":"daily_tarot","bazi":"prepare_bazi","iching":"cast_iching"}[method],
                      "method":method,"reused":False})
        if artifact.data.get("interpretation"):
            result=artifact.data
        else:
            result=self.explain(artifact,artifact.question,slots.get("style","gentle"),
                                include_hexagram_context=bool(re.search(r"主卦|变卦",artifact.question)))
        trace.append({"tool":"interpret_result","method":method})
        return finish(result["interpretation"],result)

    def prepare(self,method,question,slots,profile,zone):
        if method=="tarot":
            reading=draw_reading(question,slots.get("spread","three"),tuple(slots["picks"]) if slots.get("picks") is not None else None)
            return Artifact(method,question,reading,{"mode":method,"reading":asdict(reading),"evidence":evidence_for(reading)})
        if method=="iching":
            cast=build_cast(slots["lines"]) if slots.get("lines") is not None else cast_coins()
            policy=slots.get("policy","moving-count-v1")
            selection=select_passages(cast,policy)
            return Artifact(method,question,cast,{"mode":method,"cast":asdict(cast),"selection":selection,
                                                "evidence":selection["passages"]},policy)
        if method=="bazi":
            chart=parse_bazi_pillars(slots["pillars"]) if slots.get("pillars") else calculate_bazi(slots["birth"])
            from pathlib import Path
            gender=None
            store=FortuneStore(Path(self.cache_path).parent / "fortune.sqlite3")
            try: saved=store.get_profile(profile)
            except ValueError: saved=None
            if saved and chart.birth_time and saved.get("birth"):
                if calculate_bazi(saved["birth"]).birth_time==chart.birth_time:gender=saved["gender"]
            data={"mode":method,"chart":asdict(chart),"derived_facts":chart_facts(chart),
                  "method_checklist":wealth_checklist(chart),"evidence":bazi_evidence(chart),
                  "structural_analysis":analyze_structure(chart),
                  "complete_analysis":comprehensive_analysis(chart,gender),
                  "daily_context":daily_bazi_context(chart) if slots.get("daily_bazi") else None}
            return Artifact(method,question,chart,data)
        if method=="daily":
            instant=datetime.now(timezone.utc)
            draw=daily_draw(profile,zone,instant)
            from pathlib import Path
            store=FortuneStore(Path(self.cache_path).parent / "fortune.sqlite3")
            try: saved_profile=store.get_profile(profile)
            except ValueError: saved_profile=None
            if saved_profile:
                if saved_profile["timezone"]!=zone:
                    raise ValueError("对话每日时区与保存档案不一致，请统一设置后重试")
                with self.daily_lock:
                    report=make_daily_report(store,profile,client=self.client,model=self.model)
                report["profile_key"]=draw.cache_key
                reply=report.get("interpretation") or "\n".join(i["question"] for i in report["reflections"])
                report["interpretation"]=reply
                return Artifact(method,draw.reading.question,draw.reading,report)
            with self.daily_lock:
                result=get_daily(profile,zone,store=DailyStore(self.cache_path),client=self.client,
                                 model=self.model,style=slots.get("style","gentle"),at=instant)
            return Artifact(method,result.reading.question,result.reading,
                            {"mode":method,**asdict(result),"profile_key":draw.cache_key})
        raise ValueError("未知方法")

    def followup_question(self,session,message):
        recent=session.messages[-4:]
        transcript="\n".join(f"{m['role']}：{m['content'][:2000]}" for m in recent)
        return f"同一次结果的追问，不重新生成牌面、命盘或卦象。\n原问题：{session.artifact.question}\n近期对话：\n{transcript}\n当前追问：{message}"

    def explain(self,artifact,question,style,include_hexagram_context=False):
        data=dict(artifact.data)
        if data.get("mode")=="daily-report":
            payload={k:v for k,v in data.items() if k not in ("profile_key","key","review")}
            response=self.client.responses.create(model=self.model,store=False,
                instructions="围绕同一份每日综合报告回答追问，不改牌面、日期或计算结果。不预测事件，不将未确定旺衰、格局、用神写为已确定。用中文给可执行建议。",
                input=[{"role":"user","content":json.dumps({"question":question,"report":payload},ensure_ascii=False)}])
            if not response.output_text.strip():raise RuntimeError("模型返回空回答")
            data["interpretation"]=response.output_text.strip()
        elif artifact.method in ("tarot","daily"):
            fixed=replace(artifact.domain,question=question)
            result=TarotAgent(self.client,self.model,draw=lambda *_:fixed).read(question,fixed.spread,style=style)
            data["interpretation"]=result.interpretation
        elif artifact.method=="bazi":
            data["interpretation"]=interpret_bazi(artifact.domain,question,self.client,self.model,
                                                   style=style,daily_context=data.get("daily_context"),full_analysis=data.get("complete_analysis"))
        else:
            result=interpret_cast(artifact.domain,question,self.client,self.model,artifact.policy,style,
                                  include_hexagram_context=include_hexagram_context)
            data.update(result)
        # Keep original question and immutable tool facts for later followups.
        artifact.data["interpretation"]=data["interpretation"]
        return data
