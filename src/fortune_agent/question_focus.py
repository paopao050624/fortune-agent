"""Topic-specific response guidance; it never infers personal circumstances."""
import re
import hashlib
import json

TOPICS={
 'study':('学习与研究',r'学习|考试|复习|论文|毕业|课题|研究|作业|课程', '围绕任务拆分、练习反馈、资料核查与时间安排；动作要说明完成标准，不泛泛说努力。'),
 'work':('工作与项目',r'工作|项目|求职|面试|职业|职场|同事|创业', '围绕目标、职责、依赖、交付与沟通；明确下一步可核实的条件，不承诺升职或收入。'),
 'relationship':('关系与沟通',r'感情|恋爱|关系|伴侣|分手|复合|沟通|家人|朋友', '围绕表达需求、倾听、边界与共同确认；不读取他人内心，不断定对方爱意或婚姻结局。'),
 'resources':('资源与选择',r'钱|预算|收入|投资|财务|花费|资源|选择|决策', '围绕成本、可承担损失、必要资料与备选方案；不提供收益保证或买卖指令。')}


def question_guidance(question):
    matches=[(key,title,guide) for key,(title,pattern,guide) in TOPICS.items() if re.search(pattern,question)]
    text='；'.join(f'{title}：{guide}' for _,title,guide in matches) if matches else '围绕用户明确的问题回答，资料不明时用条件表达，避免补出其经历。'
    return ('回答组织：先用2–3句回应用户问题，再解释1–3个直接相关工具依据，最后给两条可执行行动。'
            '不要逐项堆砌不相关命盘信息；引用与方法限制合并为一小段，避免每段重复免责声明。保留真实的不确定性。'
            '不从星曜牌面推定性格、关系事实、疾病或财富。问题重点：'+text)


def guidance_signature():
    material={'topics':TOPICS,'general':question_guidance('一般问题'),'version':'question-focus-v1'}
    return hashlib.sha256(json.dumps(material,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
