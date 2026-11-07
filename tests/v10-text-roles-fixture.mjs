import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob, PresentationFile} from '@oai/artifact-tool';
import {createDeck, renderSavedDeck} from './hualang-kit.mjs';

const [skillDir, outputDir] = process.argv.slice(2);
const deck = await createDeck({
  skillDir, title: '概论与口径导出验证', presenter: '示例工作组',
  date: '2026年11月8日', zhFont: 'Noto Sans SC', defaultPurpose: 'report',
});
const areas = {};
function content(slide, key, suppliedArea) {
  const area = suppliedArea ?? deck.contentArea(slide);
  areas[key] = {area, queriedArea: deck.contentArea(slide)};
  deck.contextLine(slide, '模拟资料 · 同一期间与统计范围',
    {x: area.x, y: area.y, w: area.w, h: 28});
  deck.text(slide, '保留完整材料与判断条件，再展开本页依据。',
    {x: area.x, y: area.y + 44, w: area.w, h: 54, name: 'fixture-body'});
}

content(deck.addPage({title: '单行概论', lead: '单位费用比较须与到场规模同时核对。'}), 'single');
content(deck.addPage({title: '双行概论', lead: '费用增加后，先更新合计与单位费用。\n原有判断也要随同一口径的比较结果更新。'}), 'multiline');
const legacy = deck.addReportPage({title: '兼容概论', summary: '旧入口仍保留清楚可见的核心判断。'});
content(legacy.slide, 'legacy', legacy.areas.content);
const chartPage = deck.addPage({title: '图表口径'});
content(chartPage, 'withoutLead');
deck.chart(chartPage, 'bar', {
  position: {left: 48, top: 240, width: 700, height: 330},
  categories: ['B场', 'A场'],
  series: [{name: '每位实到费用', values: [119.05, 125]}],
  barOptions: {direction: 'bar', grouping: 'clustered'},
});

const file = path.join(outputDir, 'v10-text-roles.pptx');
await (await PresentationFile.exportPptx(deck.presentation)).save(file);
const reloaded = await PresentationFile.importPptx(await FileBlob.load(file));
const chart = reloaded.toProto().charts[0];
const result = {areas, chartAfterReload: {
  categories: chart.categories,
  seriesCategories: chart.series[0].categories,
  values: chart.series[0].values,
}};
if (process.env.HUALANG_TEST_OUTPUT) {
  result.preview = await renderSavedDeck({
    candidatePath: file, renderDir: path.join(outputDir, 'render'),
    slides: [2, 3, 4, 5], scale: 1,
  });
}
await fs.writeFile(path.join(outputDir, 'result.json'), JSON.stringify(result, null, 2));
