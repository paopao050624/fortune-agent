/* User-visible formatting, compact disclosure, and hostile model-text regression checks. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const fs=require('fs');const path=require('path');
const check=(ok,message)=>{if(!ok)throw Error(message);};
(async()=>{
 const out=process.env.FORTUNE_SCREENSHOT_DIR||'work/format-validation';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.FORTUNE_TEST_URL||'http://127.0.0.1:8766');
 const reply='### 今日建议\n\n先完成**一个小目标**，保留*休息时间*。\n\n1. 写清完成标准。\n2. 专注20分钟。\n\n- 先确认资料。\n- 再决定下一步。\n\n| 方向 | 行动 |\n| --- | --- |\n| 学习 | 修改一小节 |\n\n[参考资料](https://example.com/reference)\n\n<img src=x onerror="window.formatProbe=1">\n[不安全链接](javascript:alert)\n\n```text\n**代码中的星号保留**\n```';
 await require('./browser_job_stub.cjs')(page,async data=>data.mode==='chat'?{session_id:'format-test',reply,status:'answered',method:'none',trace:[],result:null,turns:1}:null);
 await page.locator('#chat-message').fill('测试：**用户原文不改写**');await page.locator('#chat-send').click();await page.waitForFunction(()=>document.querySelector('.bubble.assistant .markdown'));
 const bubble=page.locator('.bubble.assistant').last();
 check(await bubble.locator('strong').textContent()==='一个小目标','bold markers not rendered');
 check(await bubble.locator('h3').textContent()==='今日建议','heading not rendered');
 check(await bubble.locator('ol li').count()===2,'ordered list broken');check(await bubble.locator('ul li').count()===2,'unordered list broken');
 check(await bubble.locator('table tbody tr').count()===1,'table broken');
 check(await bubble.locator('a').count()===1,'unsafe link accepted');check((await bubble.locator('a').getAttribute('rel')).includes('noopener'),'external link lacks guard');
 check(await bubble.locator('img,script,iframe').count()===0,'model HTML executed');check(await page.evaluate(()=>window.formatProbe===undefined),'hostile text ran code');
 check((await bubble.textContent()).includes('<img src=x'),'raw HTML not preserved as text');
 check(await bubble.locator('pre code').textContent()==='**代码中的星号保留**','code literal altered');
 check((await page.locator('.bubble.user').textContent()).includes('**用户原文不改写**'),'user message altered');
 await page.screenshot({path:path.join(out,'chat-desktop.png'),fullPage:true});
 await page.unroute('**/api/run');
 await page.getByRole('tab',{name:'八字排盘',exact:true}).click();await page.locator('#bazi-input').selectOption('pillars');await page.locator('#pillars').fill('己卯 丙子 戊午 戊午');await page.locator('#submit').click();await page.waitForFunction(()=>document.querySelector('#status').textContent==='已完成。');
 check(await page.locator('#result > .result-summary').count()===1,'missing compact overview');check(await page.locator('#result > details[open]').count()===0,'detail automatically expanded');
 check((await page.locator('#result > .result-summary').textContent()).includes('项目模型估计'),'overview loses uncertainty');
 await page.screenshot({path:path.join(out,'bazi-summary.png'),fullPage:true});
 const data=await page.evaluate(()=>JSON.parse(document.querySelector('#result pre').textContent));
 data.interpretation='## 结论\n\n这是**项目估计**，不是确定性判断。\n\n- 先核对出生资料。';
 await page.evaluate(d=>render(d),data);check(await page.locator('#result .result-summary strong').textContent()==='项目估计','tool interpretation not formatted');
 check(await page.locator('#result > .result-summary').evaluate(e=>e.previousElementSibling.tagName==='H2'),'interpretation is not first');
 await page.evaluate(d=>render(d,document.getElementById('chat-result')),data);
 check(await page.locator('#chat-result > .result-summary .markdown').count()===0,'answer duplicated in chat evidence panel');
 await page.setViewportSize({width:390,height:844});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'mobile horizontal overflow');await page.screenshot({path:path.join(out,'bazi-mobile.png'),fullPage:true});
 await page.getByRole('tab',{name:'统一对话',exact:true}).click();check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'chat mobile overflow');await page.screenshot({path:path.join(out,'chat-mobile.png'),fullPage:true});
 check(errors.length===0,errors.join('\n'));console.log('Formatted answers, safe links/HTML, compact results and desktop/mobile layout passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exit(1);});
