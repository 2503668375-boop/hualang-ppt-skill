// Export a small real deck for profile/title/sequence regression checks.
// The Python runner copies this and the production helper into a temp workspace.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {PresentationFile} from '@oai/artifact-tool';
import {createDeck, assertTopicTitle} from './hualang-kit.mjs';

const [skillDir, outputDir] = process.argv.slice(2);
if (!skillDir || !outputDir) throw new Error('Provide skillDir and outputDir.');
const english = 'A model of how data and theory can be used in one science lesson';
const longChinese = '先秦文化与秦汉政治制度比较';
for (const title of ['先秦文化', english, longChinese]) {
  assert.equal(assertTopicTitle(title), title);
}
for (const title of ['', '先读材料再比较证据', '如何理解模型', '本页讨论证据']) {
  assert.throws(() => assertTopicTitle(title));
}
assert.equal(assertTopicTitle('如何理解模型', {userSupplied:true}), '如何理解模型');

const deck = await createDeck({skillDir, title:'工具行为验证', presenter:'示例教师', date:'2026年11月6日'});
const fixtures = [
  {title:'先秦文化', purpose:'parent'},
  {title:english, purpose:'classroom'},
  {title:longChinese, purpose:'parent', tableSize:29, bodySize:31},
  {title:'边界条件', purpose:'classroom', tableSize:26},
];
for (const [i, fixture] of fixtures.entries()) {
  const slide = deck.addSchoolScene({title:fixture.title, purpose:fixture.purpose});
  deck.text(slide, '阅读材料并说明判断的依据。', {
    x:48, y:120, w:1184, h:80, name:'fixture-body',
    ...(fixture.bodySize ? {size:fixture.bodySize} : {}),
  });
  deck.nativeTable(slide, [['对象', '证据'], ['比较对象', `对应材料${i+1}`]], {
    x:48, y:240, w:1184, h:200, columnWidths:[400,784], rowHeights:[80,120],
    ...(fixture.tableSize ? {size:fixture.tableSize} : {}),
  });
}
await fs.mkdir(outputDir, {recursive:true});
const pptx = path.join(outputDir,'tool-behavior.pptx');
await (await PresentationFile.exportPptx(deck.presentation)).save(pptx);
const pureDeck = await createDeck({skillDir, title:'工具纯组件验证', presenter:'示例教师', date:'2026年11月6日'});
const pureSlide = pureDeck.addPage({title:'对象与依据', purpose:'classroom'});
pureDeck.methodStrip(pureSlide, '判断依据', '同一材料的对象、条件与结论保持连通。',
  {x:48,y:160,w:1184,h:90,size:25});
pureDeck.text(pureSlide, '本页只有文字与原生图形，不含表格或数据图。',
  {x:48,y:310,w:1184,h:70,size:25,name:'pure-shape-body'});
await (await PresentationFile.exportPptx(pureDeck.presentation)).save(path.join(outputDir,'pure-shape.pptx'));
await fs.writeFile(path.join(outputDir,'fixture.json'), JSON.stringify({
  title:'工具行为验证', presenter:'示例教师', date:'2026年11月6日',
  acceptedTitles:['先秦文化', english, longChinese],
  parentTablePx:24, classroomTablePx:23, explicitTablePx:[29,26],
}));
console.log(JSON.stringify({ok:true,pptx,slides:deck.presentation.slides.items.length}));
