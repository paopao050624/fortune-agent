"""Curate actual fixed-revision Wikisource passages, never manufacture quotations."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import re
ROOT=Path(__file__).resolve().parents[1]
class Sections(HTMLParser):
    def __init__(self):super().__init__();self.sections={};self.heading=None;self.capture=False;self.parts=[];self.ignore=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.ignore+=1
        if re.fullmatch('h[1-6]',tag):self.capture=True;self.parts=[]
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.ignore=max(0,self.ignore-1)
        if re.fullmatch('h[1-6]',tag):
            self.heading=''.join(self.parts).strip();self.sections[self.heading]=[];self.capture=False
    def handle_data(self,data):
        if self.ignore:return
        if self.capture:self.parts.append(data)
        elif self.heading:self.sections[self.heading].append(data)
raw=(ROOT/'work/ziwei-core.html').read_text();parsed=Sections();parsed.feed(raw)
revision=int(re.search(r'Special:Redirect/revision/(\d+)',raw)[1]);stamp=re.search(r'property="dc:modified" content="([^"]+)"',raw)[1]
existing=ROOT/'src/fortune_agent/data/ziwei_sources.json'
if existing.exists() and revision!=json.loads(existing.read_text())['source']['revision_id']:
    raise ValueError('Source revision differs from catalog; review the new text before changing pinned sources')
text={h:re.sub(r'\s+',' ',''.join(v)).strip() for h,v in parsed.sections.items()}
# Short, continuous passages checked against complete corresponding sections.
selections=[
('紫微','問紫微所主若何？','答曰：紫微屬土，乃中天之尊星為帝座，主掌造化樞機，人生主宰。','统筹与整体协调','今天如何把分散的任务整合成一个清楚的目标？'),
('天机','問天機所主如何？','有靈機應變之志。淵魚察見，作事有方。','规划与应变','哪些条件变化需要你调整计划？'),
('太阳','問太陽所主若何？',None,'表达与公开责任','哪些承诺需要说清楚并主动兑现？'),
('武曲','問武曲星所主為何？','答曰：武曲北斗第六星，屬金，乃財帛宮主。','资源与执行','有哪些投入、预算或执行标准需要核对？'),
('天同','問天同星所主若何？','答曰：天同星屬水，乃南方第四星也，為福德宮之主宰。','恢复与支持','如何安排恢复时间并寻求合适的支持？'),
('廉贞','問廉貞所主若何？','答曰：廉貞屬火，北斗第五星也。在斗司品秩，在數司權令。','规则与边界','你需要确认哪些职责和边界？'),
('天府','問天府所主若何？','答曰：天府屬土，南斗主令第一星也。為財帛之主宰，在斗司福權之宿，會吉皆為富貴之基，定作文昌之論。','资源保管与组织','你手上的资源有没有长期的安排？'),
('太阴','問太陰星所主若何？','答曰：太陰乃水之精，為田宅主，化富，與日為配。','安顿与积累','什么环境和长期积累能支持你的日常生活？'),
('贪狼','問貪狼所主若何？','其氣屬木，體屬水，故化氣為桃花。','兴趣与互动','如何筛选兴趣、机会与社交投入？'),
('巨门','問巨門所主若何？','巨門在天，司品萬物。在數則掌執是非，主於暗昧，疑是多非，欺瞞天地，進退兩難。','辨析与沟通','信息不清时，哪些事实需要先核实再表达？'),
('天相','問天相星所主若何？','答曰：天相屬水，南斗第五星也。為司爵之宿，為福善，化氣曰印，是為官祿文星，佐帝之位。','协调与制度','怎样协调不同人的职责而不替人作决定？'),
('天梁','問天梁星所主若何？','答曰：天梁屬土，南斗第二星也。司壽化氣為蔭為福壽，乃父母之主命化暴戾為祥和。','支持与经验','可以借助谁的经验审视当前问题？'),
('七杀','問七殺星所主若何？','答曰：七殺南斗第六星也，屬火、金。乃斗中之上將，實成敗之孤辰。在斗司斗柄，主於風憲。','决断与挑战','面对压力，哪些行动有明确边界和退出条件？'),
('破军','問破軍所主若何？','居子午入廟，在天為殺氣，在數為耗星，故化氣曰耗。','调整与更新','改变现有安排前，需要评估哪些成本和影响？')]
aux=[('文昌','問文昌星所主若何？','学习与表达'),('文曲','问文曲星所主若何？','表达与细节'),('左辅','问左辅所主若何？','协助与合作'),('右弼','问右弼所主若何？','协助与合作'),('禄存','问禄存星所主若何？','积累与资源'),('天马','问天马星所主若何？','行动与迁移')]
mutagens=[('禄','问化禄星所主若何？','资源与支持'),('权','问化权星所主若何？','责任与行动'),('科','问化科星所主若何？','学习与呈现'),('忌','问化忌星所主若何？','阻滞与反思')]
print('source revision',revision)
for h in ['問太陽所主若何？',*[h for _,h,_ in aux],*[h for _,h,_ in mutagens]]:print(h,text.get(h,'MISSING')[:200])
entries=[]
def add(ident,heading,quote,star=None,mutagen=None,topic='',reflection=''):
    section=text[heading]
    if quote is None:
        # Exact first complete sentence, no modern rewrite included in quote.
        quote=section.split('。')[0]+'。'
    if quote not in section:raise ValueError('Quote does not match source: '+ident)
    note=['固定电子转录，尚未与指定纸本扫描逐字校勘；同页混有简繁文字与异文，按提供文本保留，不自行更正。','相关章节含旧时代性别、贫富、疾病和宿命论表述；仅作历史概念参考，不套用于用户的事实、诊断或预言。']
    entries.append({'id':ident,'work':'紫微斗数全书','chapter':'卷一 · '+heading,'heading':heading,'source_text':quote,'star':star,'mutagen':mutagen,'topic':topic,'reflection':reflection,
        'source_url':f'https://zh.wikisource.org/w/index.php?title=紫微斗數全書/卷一&oldid={revision}',
        'locator':'卷一 · '+heading+'（电子修订；不提供纸本页码）','revision_id':revision,'edition_note':note[0],'notes':note,'section_text_sha256':hashlib.sha256(section.encode()).hexdigest()})
for star,heading,quote,topic,reflection in selections:add('ziwei-star-'+star,heading,quote,star=star,topic=topic,reflection=reflection)
for star,heading,topic in aux:add('ziwei-star-'+star,heading,None,star=star,topic=topic,reflection='怎样把这项传统意象转化为可以核实的具体行动？')
for m,h,topic in mutagens:add('ziwei-mutagen-'+m,h,None,mutagen=m,topic=topic,reflection='哪些资源、责任或阻碍值得结合实际经历复核？')
add('ziwei-principle-context','太微賦','星有同躔，數有分定，須明其生剋之要，必詳乎得垣失度之分。',topic='重视配合与位置',reflection='不要只根据一颗星作人生判断。')
add('ziwei-principle-combined','太微賦','星臨廟旺，再觀生剋之機。命坐強宮，細察制化之理。',topic='亮度不等于结果',reflection='同宫、对宫和三方的配合需要一起核对。')
add('ziwei-principle-not-absolute','增補太微賦','凶不皆凶，吉無純吉。',topic='避免绝对吉凶',reflection='记录实际条件，而不是给自己贴吉凶标签。')
catalog={'source':{'work':'紫微斗数全书','page_title':'紫微斗數全書/卷一','revision_id':revision,'revision_timestamp':stamp,'retrieved_date':'2026-10-06','fetch_url':'https://api.wikimedia.org/core/v1/wikisource/zh/page/紫微斗數全書%2F卷一/html','html_sha256':hashlib.sha256(raw.encode()).hexdigest(),'edition_note':'Wikisource电子转录，纸本版本未确证，未完成全书/跨版本校勘；作者归属不由本批确证。','rights_note':'历史文本摘录；电子转录来源Wikisource，保留归属与固定修订链接，按其CC BY-SA条款提供转录部分；不把文本来源授权混作代码MIT。'},'entries':entries}
(ROOT/'src/fortune_agent/data/ziwei_sources.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
print('saved',len(entries),'source excerpts')
