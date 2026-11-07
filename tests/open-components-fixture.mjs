// Native export fixture with simulated content only. Paths are supplied by runner.
import fs from 'node:fs/promises';
import path from 'node:path';
import {PresentationFile} from '@oai/artifact-tool';
import {createDeck} from './hualang-kit.mjs';

const [skillDir, outputDir] = process.argv.slice(2);
if (!skillDir || !outputDir) throw new Error('Provide skillDir and outputDir.');
const deck = await createDeck({skillDir, title:'开放组件验证', presenter:'示例教师', date:'2026年11月7日'});
const mark = (objects, prefix) => objects.forEach((object, i) => { object.name = `${prefix}-${i}`; });
const rejected = {};
const rejects = (name, operation) => {
  try { operation(); rejected[name] = false; }
  catch { rejected[name] = true; }
};

const metric = deck.addPage({title:'指标说明'});
mark(deck.metricInline(metric, '36', '课程完成', {
  x:100, y:200, w:320, unit:'项', context:'模拟数字',
}), 'fixture-metric');
const dots = deck.addPage({title:'同口径比较'});
mark(deck.dotComparison(dots, [
  {label:'模拟甲组', before:-10, after:30},
  {label:'模拟乙组', before:10, after:0},
], {x:100, y:200, w:1000, h:300, min:-10, max:30, labelWidth:140}), 'fixture-dot');
rejects('dot-outside-domain', () => deck.dotComparison(dots,
  [{label:'越界', before:40, after:20}], {min:0, max:30}));
rejects('dot-reversed-domain', () => deck.dotComparison(dots,
  [{label:'逆序', before:1, after:2}], {min:10, max:0}));
rejects('dot-nonfinite-value', () => deck.dotComparison(dots,
  [{label:'非有限数', before:NaN, after:2}], {min:0, max:30}));
rejects('dot-empty-rows', () => deck.dotComparison(dots, [], {min:0, max:30}));
rejects('dot-insufficient-space', () => deck.dotComparison(dots,
  [{label:'空间不足', before:1, after:2}], {min:0, max:30, w:200}));

const timeline = deck.addPage({title:'日期比例'});
mark(deck.milestoneTimeline(timeline, [
  // Custom positions deliberately oppose the default alternating sides.
  {date:'2026-01-01', label:'模拟开始', detail:'计划说明', labelY:430},
  {date:'2026-01-03', label:'模拟中段', detail:'阶段说明', labelY:200},
  {date:'2026-01-11', label:'模拟结束'},
], {x:100, y:200, w:1000, h:300, start:'2026-01-01', end:'2026-01-11'}), 'fixture-timeline');
const timelineOptions = {start:'2026-02-01', end:'2026-03-31'};
rejects('timeline-impossible-date', () => deck.milestoneTimeline(timeline,
  [{date:'2026-02-30', label:'无效日期'}], timelineOptions));
rejects('timeline-noniso-date', () => deck.milestoneTimeline(timeline,
  [{date:'2026/02/01', label:'非ISO日期'}], timelineOptions));
rejects('timeline-outside-domain', () => deck.milestoneTimeline(timeline,
  [{date:'2026-04-01', label:'范围之外'}], timelineOptions));
rejects('timeline-reversed-domain', () => deck.milestoneTimeline(timeline,
  [{date:'2026-02-01', label:'逆序'}], {start:'2026-03-31', end:'2026-02-01'}));
rejects('timeline-empty-events', () => deck.milestoneTimeline(timeline, [], timelineOptions));

for (const [side, anchor] of Object.entries({
  above:{x:400,y:100}, below:{x:400,y:550}, left:{x:100,y:350}, right:{x:700,y:350},
})) {
  const slide = deck.addPage({title:'批注'+side});
  mark(deck.evidenceNote(slide, '模拟说明正文', {
    x:300, y:300, w:200, h:100, title:'模拟依据', anchor, route:'straight',
  }), 'fixture-note-'+side);
}
rejects('note-inside-text', () => deck.evidenceNote(metric, '内部锚点', {
  x:300, y:300, w:200, h:100, anchor:{x:400,y:350},
}));
rejects('note-nonfinite-anchor', () => deck.evidenceNote(metric, '无效锚点', {
  x:300, y:300, w:200, h:100, anchor:{x:Infinity,y:350},
}));
const withoutSummary = deck.addReportPage({title:'无概论页'});
const withSummary = deck.addReportPage({title:'有概论页', summary:'模拟说明。'});
await fs.mkdir(outputDir, {recursive:true});
await (await PresentationFile.exportPptx(deck.presentation)).save(path.join(outputDir, 'open-components.pptx'));
await fs.writeFile(path.join(outputDir, 'open-components.json'), JSON.stringify({
  rejected,
  areas:{withoutSummary:withoutSummary.areas, withSummary:withSummary.areas},
  slideCount:deck.presentation.slides.items.length,
}, null, 2));
console.log(JSON.stringify({ok:true, slides:deck.presentation.slides.items.length}));
