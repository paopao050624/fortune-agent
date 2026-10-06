/* Synthetic browser acceptance checks. Run against isolated validation data. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const fs=require('fs');const path=require('path');
const base=process.env.FORTUNE_TEST_URL||'http://127.0.0.1:8766';
const out=process.env.FORTUNE_SCREENSHOT_DIR||'work/web-validation/screenshots';
const check=(ok,message)=>{if(!ok)throw Error(message);};
(async()=>{
 fs.mkdirSync(out,{recursive:true});const errors=[];const checks=[];
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);
 const tab=async name=>page.getByRole('tab',{name,exact:true}).click();
 const complete=async selector=>page.waitForFunction(s=>document.querySelector(s).textContent==='已完成。',selector);
 const snapshot=async name=>page.screenshot({path:path.join(out,name+'.png'),fullPage:true});
 const layout=async()=>check(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'horizontal page overflow');
 await tab('塔罗问答');await page.locator('#question').fill('合成验收：如何安排学习？');
 for(const [spread,count]of[['single',1],['three',3],['decision',3],['five',5],['celtic',10]]){
  await page.locator('#spread').selectOption(spread);await page.locator('#tarot-shuffle').click();
  await page.waitForFunction(()=>document.querySelectorAll('#tarot-grid button').length===78);
  for(let n=0;n<count;n++)await page.locator('#tarot-grid button').nth(n).click();
  await page.locator('#submit').click();await complete('#status');
  check(await page.locator('#result .card').count()===count,'wrong spread count '+spread);
  const labels=await page.locator('#result .card strong').allTextContents();check(new Set(labels).size===count,'duplicate cards');
  await page.locator('#submit').click();await complete('#status');check(JSON.stringify(labels)===JSON.stringify(await page.locator('#result .card strong').allTextContents()),'reveal changed');
  checks.push('tarot-'+spread);
 }
 await snapshot('tarot-ten');await layout();
 // Exercise provider-dependent front-end responses using a declared browser stub, never real predictions.
 await page.route('**/api/run',async route=>{const data=route.request().postDataJSON();
  if(data.mode!=='tarot-followup')return route.continue();
  const original=await page.evaluate(()=>JSON.parse(document.querySelector('#result pre').textContent));
  await route.fulfill({json:{...original,interpretation:'测试替身：沿用原牌面，先完成一个小目标。'}});
 });
 await page.locator('#tarot-followup-send').evaluate(b=>b.closest('details').open=true);
 await page.locator('#tarot-followup').fill('给一个具体步骤');await page.locator('#tarot-followup-send').click();
 await page.waitForFunction(()=>document.querySelector('#status').textContent==='追问沿用原牌面。');checks.push('tarot-followup-browser-stub');
 await page.unroute('**/api/run');
 await tab('每日一张');await page.locator('#profile').fill('synthetic-browser-daily');await page.locator('#submit').click();await complete('#status');
 const daily=await page.locator('#result .card').textContent();await page.locator('#submit').click();await complete('#status');check(daily===await page.locator('#result .card').textContent(),'daily not stable');checks.push('daily-stable');
 await tab('八字排盘');await page.locator('#bazi-input').selectOption('pillars');await page.locator('#pillars').fill('己卯 丙子 戊午 戊午');await page.locator('#submit').click();await complete('#status');
 check(await page.locator('#result').textContent().then(s=>s.includes('项目模型估计')),'missing judgment');
 await page.locator('#bazi-input').selectOption('birth');await page.locator('#birth').fill('2000-01-01T12:00');await page.locator('#bazi-gender').selectOption('female');await page.locator('#bazi-date').fill('2026-10-06');await page.locator('#daily-bazi').check();await page.locator('#submit').click();await complete('#status');
 const bazi=await page.locator('#result').textContent();check(bazi.includes('己卯')&&bazi.includes('2001-08-16'),'missing computed luck');checks.push('bazi-birth-pillars-daily-luck');await snapshot('bazi');
 await tab('周易起卦');await page.locator('#coin-lines').fill('9 9 9 9 9 9');await page.locator('#submit').click();await complete('#status');check((await page.locator('#result').textContent()).includes('乾'),'missing hexagram');
 await page.locator('#reference-button').click();await complete('#status');check((await page.locator('#result').textContent()).includes('卦辞'),'missing reference');checks.push('iching-cast-reference');
 await tab('每日运势与回顾');const id='synthetic-browser-'+Date.now();
 await page.locator('#report-profile').fill(id);await page.locator('#report-birth').fill('2000-01-01T12:00');await page.locator('#report-gender').selectOption('female');
 await page.locator('#profile-chart-birth').evaluate(b=>b.closest('details').open=true);
 await page.locator('#profile-chart-birth').fill('2000-01-01T12:00');await page.locator('#profile-offset').fill('+08:00');await page.locator('#profile-lat').fill('31.23');await page.locator('#profile-lon').fill('121.47');
 await page.locator('#report-save').click();await complete('#report-status');await page.locator('#report-date').fill('2026-10-06');await page.locator('#report-generate').click();await complete('#report-status');
 check((await page.locator('#report-result').textContent()).includes('2026-10-06'),'wrong report date');
 await page.locator('#report-result textarea').fill('合成验收回顾：完成论文小节');await page.locator('#report-result button').last().click();await complete('#report-status');
 await page.locator('#report-history').click();await complete('#report-status');check((await page.locator('#report-history-list').textContent()).includes('已回顾'),'review missing');
 const downloadPromise=page.waitForEvent('download');await page.locator('#report-export').click();const download=await downloadPromise;const archive=path.join(out,'synthetic-archive.json');await download.saveAs(archive);
 const data=JSON.parse(fs.readFileSync(archive));check(data.history[0].review.includes('论文'),'export missing review');checks.push('profile-report-review-export');await snapshot('daily-report');
 await tab('西方占星');await page.locator('#chart-birth').fill('2000-01-01T12:00');await page.locator('#chart-offset').fill('+00:00');await page.locator('#chart-zone').fill('Europe/London');await page.locator('#chart-lat').fill('51.4779');await page.locator('#chart-lon').fill('0');await page.locator('#chart-submit').click();await complete('#chart-status');
 check(await page.locator('#chart-result svg').count()===1,'missing wheel');check(await page.locator('#chart-result > details[open]').count()===0,'chart detail should start collapsed');await snapshot('astrology-summary');await page.locator('#chart-result > details').filter({hasText:'查看星盘、宫位与相位'}).locator('summary').first().click();await snapshot('astrology');checks.push('astrology-manual');
 await page.locator('#chart-profile').fill(id);await page.locator('#chart-use-profile').check();check(await page.locator('#chart-birth').isDisabled(),'profile mode must disable unused manual inputs');await page.locator('#chart-save').check();await page.locator('#chart-submit').click();await complete('#chart-status');checks.push('astrology-profile-history');
 await tab('紫微斗数');await page.locator('#chart-submit').click();await complete('#chart-status');check(await page.locator('.ziwei-palace').count()===12,'missing palaces');await snapshot('ziwei-summary');await page.locator('#chart-result > details').filter({hasText:'查看十二宫与星曜'}).locator('summary').first().click();await snapshot('ziwei');checks.push('ziwei-profile-history');
 await tab('每日运势与回顾');await page.locator('#reading-history').click();await complete('#report-status');check(await page.locator('#report-history-list button').count()===2,'missing saved charts');checks.push('reading-history');
 page.on('dialog',dialog=>dialog.accept());await page.locator('#report-delete').click();await complete('#report-status');
 await page.locator('#profile-import-file').setInputFiles(archive);await page.locator('#profile-import').click();await complete('#report-status');await page.locator('#report-history').click();await complete('#report-status');check(await page.locator('#report-history-list button').count()===1,'restore failed');checks.push('profile-delete-import');
 await tab('统一对话');let turn=0;
 await page.route('**/api/run',async route=>{const d=route.request().postDataJSON();if(d.mode==='chat'){turn++;return route.fulfill({json:{session_id:'synthetic-session',status:'needs_input',method:'astrology',trace:[],result:null,reply:turn===1?'测试替身：请提供出生时间和经纬度。':'测试替身：资料已收到。'}});}if(d.mode==='chat-clear')return route.fulfill({json:{cleared:true}});return route.continue();});
 await page.locator('#chat-message').fill('用占星分析学习');await page.locator('#chat-send').click();await page.waitForFunction(()=>document.querySelector('#chat-history').textContent.includes('测试替身：请提供'));
 await page.locator('#chat-clear').click();await page.waitForFunction(()=>document.querySelector('#chat-status').textContent==='已开启新对话。');checks.push('chat-clarify-clear-browser-stub');await page.unroute('**/api/run');
 await page.setViewportSize({width:390,height:844});
 for(const name of['塔罗问答','每日一张','八字排盘','周易起卦','每日运势与回顾','西方占星','紫微斗数','统一对话']){await tab(name);await layout();if(['西方占星','紫微斗数','统一对话'].includes(name))await snapshot('mobile-'+name);}
 checks.push('mobile-all-tabs-no-overflow');check(errors.length===0,errors.join('\n'));
 await tab('每日运势与回顾');await page.locator('#report-delete').click();await complete('#report-status');
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({base,checks,pageErrors:errors,modelTesting:'Provider-dependent UI paths use explicit browser stubs; domain routing is covered by Python tests.'},null,2));
 console.log(JSON.stringify({passed:checks.length,checks}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exit(1);});
