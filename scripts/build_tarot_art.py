"""Build 78 original symbolic SVG cards. These are not reproductions of Waite art."""
from pathlib import Path
from html import escape
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fortune_agent.tarot import DECK
OUT=Path(__file__).resolve().parents[1]/'src/fortune_agent/static/tarot'
OUT.mkdir(parents=True,exist_ok=True)
colors={None:('#263e63','#dfbf76'), '权杖':('#8a4939','#f0c787'),'圣杯':('#326879','#b8d9d4'),'宝剑':('#4f5678','#d1d8e6'),'星币':('#43624b','#d9ca87')}
major_symbols=['旅途','意志','直觉','滋养','秩序','传承','选择','前行','勇气','内省','变化','衡量','换位','更新','调和','束缚','重构','希望','未知','明朗','回应','整合']
def star(cx,cy,r):
 import math
 pts=['%.2f,%.2f'%(cx+math.cos(-math.pi/2+i*math.pi/5)*(r if i%2==0 else r*.42),cy+math.sin(-math.pi/2+i*math.pi/5)*(r if i%2==0 else r*.42)) for i in range(10)]
 return '<polygon points="'+' '.join(pts)+'" fill="none" stroke="currentColor" stroke-width="2"/>'
def icon(suit,x,y,size=18):
 if suit=='权杖':return f'<g transform="translate({x},{y})"><path d="M-6 18 L6 -18 M-2 5 Q-20 -2 -11 -9 Q-1 -12 2 -4 M3 -6 Q18 -19 19 -5 Q12 4 2 1" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></g>'
 if suit=='圣杯':return f'<g transform="translate({x},{y})"><path d="M-16 -14 H16 L12 0 Q0 14 -12 0 Z M0 8 V20 M-12 21 H12" fill="none" stroke="currentColor" stroke-width="2.5"/></g>'
 if suit=='宝剑':return f'<g transform="translate({x},{y})"><path d="M0 -23 L7 -10 L2 10 H-2 L-7 -10 Z M-14 12 H14 M0 13 V25 M-5 26 H5" fill="none" stroke="currentColor" stroke-width="2.5"/></g>'
 return f'<g transform="translate({x},{y})"><circle r="21" fill="none" stroke="currentColor" stroke-width="2"/>{star(0,0,16)}</g>'
def major(number):
 # Distinct geometry reflects card themes without copying a deck's artwork.
 motifs={0:'<path d="M60 235 Q100 115 190 100 M65 230 L90 228 M65 230 L68 205"/>',1:'<path d="M70 160 C70 120 112 120 130 160 C149 201 190 201 190 160 C190 120 150 120 130 160 C110 200 70 200 70 160"/>',2:'<path d="M148 94 A54 54 0 1 0 148 202 A40 40 0 0 1 148 94"/>',3:'<path d="M130 228 V160 M130 190 Q62 189 80 143 Q120 144 130 190 M130 167 Q194 162 180 117 Q135 118 130 167"/>',4:'<path d="M82 220 V129 L178 129 V220 M78 129 L91 83 L113 110 L130 75 L149 110 L170 83 L183 129"/>',5:'<path d="M130 80 V225 M83 117 H177 M97 158 H163"/>',6:'<path d="M130 210 C40 150 77 90 130 126 C183 90 220 150 130 210"/>',7:'<path d="M74 192 L99 119 H165 L185 192 Z M65 199 H195 M130 116 V80 L160 96 L130 101"/><circle cx="92" cy="215" r="16"/><circle cx="168" cy="215" r="16"/>',8:'<path d="M130 100 C78 67 60 136 104 150 C153 166 180 201 205 146 M130 100 C177 65 198 128 156 152 C109 173 81 200 54 147"/>',9:'<path d="M108 111 H152 V185 H108 Z M110 112 Q130 69 150 112 M130 186 V221"/>',10:'<circle cx="130" cy="155" r="64"/><path d="M130 91 V219 M66 155 H194 M85 110 L175 200 M85 200 L175 110"/>',11:'<path d="M130 80 V227 M80 118 H180 M90 118 L67 175 H113 Z M170 118 L147 175 H193 Z M102 229 H158"/>',12:'<path d="M65 92 H195 M130 92 V155 L96 191 M130 155 L163 174 M130 160 V207"/><circle cx="130" cy="223" r="14"/>',13:'<path d="M70 220 Q126 200 181 125 M81 180 Q86 87 167 96 Q146 134 81 180"/><circle cx="173" cy="109" r="8"/>',14:'<path d="M78 103 H115 L108 148 H84 Z M147 183 H183 L177 225 H153 Z M110 129 Q173 129 164 179"/>',15:'<path d="M93 129 C54 157 95 214 131 175 M131 175 C166 137 202 193 169 220 M91 124 L132 87 L174 124"/>',16:'<path d="M103 221 L111 124 H161 L177 221 Z M142 70 L122 107 L151 109 L126 156"/>',17:star(130,143,61)+'<path d="M74 219 Q130 187 189 218"/>',18:'<path d="M151 86 A58 58 0 1 0 151 202 A43 43 0 0 1 151 86 M76 229 Q120 205 184 230"/>',19:'<circle cx="130" cy="152" r="43"/><path d="M130 81 V94 M130 210 V224 M57 152 H71 M188 152 H202 M78 100 L88 110 M172 194 L183 205 M79 204 L90 193 M171 111 L182 100"/>',20:'<path d="M82 206 Q130 150 177 206 M130 91 V165 M107 117 L130 91 L153 117"/><circle cx="130" cy="212" r="13"/>',21:'<ellipse cx="130" cy="153" rx="64" ry="87"/><path d="M72 180 Q100 207 132 193 Q165 177 174 141 M96 103 Q131 91 160 119"/>'}
 return '<g fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'+motifs[number]+'</g>'
manifest={'version':'symbolic-tarot-art-v1','creator':'Fortune Agent contributors','license':'MIT','description':'项目原创符号插画，用于辨识牌名与主题；不是Waite原版图像或原文释义。','cards':{}}
for card in DECK:
 bg,ink=colors[card.suit];number=int(card.id.split('-')[-1]);subtitle=major_symbols[number] if card.suit is None else (['','王牌','二','三','四','五','六','七','八','九','十','侍从','骑士','王后','国王'][number])
 if card.suit is None:art=major(number)
 elif number<=10:
  locations=[(130,150)] if number==1 else [(95+(i%2)*70,92+(i//2)*35) for i in range(number)]
  art=''.join(icon(card.suit,x,y) for x,y in locations)
 else:
  art='<path d="M80 94 L94 65 L113 82 L130 56 L147 82 L166 65 L180 94 Z" fill="none" stroke="currentColor" stroke-width="2"/>'+icon(card.suit,130,171)+'<path d="M82 237 Q130 216 178 237" fill="none" stroke="currentColor" stroke-width="2"/>'
 svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 390" role="img" aria-labelledby="title"><title id="title">{escape(card.name)} · 原创符号插画</title><defs><linearGradient id="paper" x2="0.8" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="#172a30"/></linearGradient></defs><rect width="260" height="390" rx="18" fill="url(#paper)"/><rect x="12" y="12" width="236" height="366" rx="12" fill="none" stroke="{ink}" opacity=".7"/><rect x="19" y="19" width="222" height="352" rx="8" fill="none" stroke="{ink}" opacity=".25"/><g color="{ink}"><circle cx="130" cy="152" r="99" fill="none" stroke="currentColor" opacity=".12"/>{art}</g><text x="130" y="297" text-anchor="middle" font-family="serif" font-size="23" fill="{ink}">{escape(card.name)}</text><text x="130" y="325" text-anchor="middle" font-family="serif" font-size="13" letter-spacing="4" fill="{ink}" opacity=".8">{escape(subtitle)}</text><text x="130" y="353" text-anchor="middle" font-family="sans-serif" font-size="8" letter-spacing="2" fill="{ink}" opacity=".5">FORTUNE · SYMBOL STUDY</text></svg>'''
 (OUT/(card.id+'.svg')).write_text(svg)
 manifest['cards'][card.id]={'path':'tarot/'+card.id+'.svg','name':card.name,'motif':subtitle}
(ROOT:=OUT.parents[1]).joinpath('data/tarot_art.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Built 78 original symbolic cards and attribution manifest.')
