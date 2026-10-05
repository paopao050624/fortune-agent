const fs = require('fs');
const { astro } = require('iztro');
try {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  astro.config({ yearDivide: 'normal', horoscopeDivide: 'normal', dayDivide: 'forward', algorithm: 'default' });
  const chart = astro.bySolar(input.date, input.time_index, input.gender === 'male' ? '男' : '女', true, 'zh-CN');
  const data = JSON.parse(JSON.stringify(chart));
  if (!Array.isArray(data.palaces) || data.palaces.length !== 12) throw new Error('invalid chart');
  process.stdout.write(JSON.stringify(data));
} catch (error) {
  process.stderr.write('ziwei chart calculation failed');
  process.exit(1);
}
