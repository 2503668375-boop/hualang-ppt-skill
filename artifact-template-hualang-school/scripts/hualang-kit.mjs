import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob, PresentationFile} from '@oai/artifact-tool';

export const colors = Object.freeze({
  purple: '#403653', secondary: '#70677F', gold: '#BCA36D',
  paper: '#FDFDFE', pale: '#F1EEF5', line: '#DAD4E2', white: '#FFFFFF',
});
export const fonts = Object.freeze({zh: 'PingFang SC', latin: 'Arial'});
export const canvas = Object.freeze({width: 1280, height: 720});
const noLine = {fill: 'none', width: 0};

export function assertTopicTitle(value, {userSupplied = false} = {}) {
  const title = String(value ?? '').trim();
  if (!title) throw new Error('页面题名不能为空。');
  if (userSupplied) return title;
  const prohibited = /(^先|先.+再|然后|接着|怎样|怎么|如何|本页|我们|你|哪些|什么|^它|从.+开始)/;
  const units = (title.match(/[\u3400-\u9fff]|[A-Za-z0-9]+/g) ?? []).length;
  if (prohibited.test(title) || /[：:？?，,；;]/.test(title) || units > 12) {
    throw new Error('自动题名须为具体短语，通常4、6或8字；不用口播、问句或长结论：' + title);
  }
  return title;
}


// CSS pixels at 96 dpi. Keep the content geometry under the caller's control.
export function text(owner, value, {x, y, w, h, size = 26, color = colors.purple,
  bold = false, font, zhFont = fonts.zh, latinFont = fonts.latin,
  align = 'left', name = 'content', lineSpacing = 1.2} = {}) {
  const shape = owner.shapes.add({geometry: 'textbox', name,
    position: {left: x, top: y, width: w, height: h}, fill: 'none', line: noLine});
  styleText(shape, value, {size, color, bold, font, zhFont, latinFont, align, lineSpacing});
  return shape;
}

function styleText(shape, value, {size, color, bold = false, font,
  zhFont = fonts.zh, latinFont = fonts.latin, align = 'left', lineSpacing = 1.2}) {
  // Font choices belong to this call/deck; no shared mutable font configuration.
  shape.text.set(String(value).split('\n').map(paragraph => ({runs:
    (paragraph.match(/[\x20-\x7e]+|[^\x20-\x7e]+/g) ?? ['']).map(run => ({
      run, style: {typeface: font ?? (/^[\x20-\x7e]*$/.test(run) ? latinFont : zhFont)},
    })),
  })));
  shape.text.style = {fontSize: size, color, bold, alignment: align,
    wrap: 'square', autoFit: 'none', insets: 0, verticalAlignment: 'top', lineSpacing};
}

export function line(owner, {x, y, w, h = 0, color = colors.line, width = 1}) {
  return owner.shapes.add({geometry: 'line',
    position: {left: x, top: y, width: w, height: h}, line: {fill: color, width}});
}

export async function image(owner, file, {x, y, w, h, alt, fit = 'contain'}) {
  if (!alt) throw new Error('image requires a useful alt description.');
  const type = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}[path.extname(file).toLowerCase()];
  if (!type) throw new Error('image supports PNG or JPEG source files.');
  const bytes = await fs.readFile(file);
  return owner.images.add({blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: type, position: {left: x, top: y, width: w, height: h}, alt, fit});
}

export function nativeTable(slide, values, {x, y, w, h, columnWidths,
  rowHeights, size = 23, numericColumns = [], focusRow = -1,
  font, zhFont = fonts.zh, latinFont = fonts.latin} = {}) {
  if (!values.length || !values[0].length || values.some(row => row.length !== values[0].length)) {
    throw new Error('nativeTable requires a nonempty rectangular values array.');
  }
  if (!columnWidths || columnWidths.length !== values[0].length || columnWidths.some(v => !Number.isFinite(v) || v <= 0) ||
      Math.abs(columnWidths.reduce((a, b) => a + b, 0) - w) > 0.5) {
    throw new Error('Provide positive columnWidths based on the actual text; their sum must equal w.');
  }
  if (rowHeights && (rowHeights.length !== values.length || rowHeights.some(v => !Number.isFinite(v) || v <= 0) ||
      Math.abs(rowHeights.reduce((a, b) => a + b, 0) - h) > 0.5)) {
    throw new Error('rowHeights must match the row count and sum to h.');
  }
  const table = slide.tables.add({rows: values.length, columns: values[0].length,
    left: x, top: y, width: w, height: h, columnWidths, values: values.map(row => row.map(String))});
  table.borders.assign({fill: colors.line, width: 0.55, style: 'solid'});
  for (let r = 0; r < values.length; r++) {
    table.rows[r].height = rowHeights?.[r] ?? h / values.length;
    for (let c = 0; c < values[0].length; c++) {
      const cell = table.getCell(r, c);
      cell.fill = r === 0 ? colors.purple : r === focusRow ? colors.pale : colors.paper;
      styleText(cell, values[r][c], {size, font, zhFont, latinFont, color: r === 0 ? colors.white : colors.purple,
        bold: r === 0 || r === focusRow, align: r > 0 && numericColumns.includes(c) ? 'right' : 'left'});
      cell.text.style = {verticalAlignment: 'middle', insets: {left: 16, right: 16, top: 12, bottom: 12}};
    }
  }
  return table;
}

export function chart(slide, type, options, {font, zhFont = fonts.zh, latinFont = fonts.latin} = {}) {
  for (const axis of [options.xAxis, options.yAxis]) {
    if (axis && ('minimumScale' in axis || 'maximumScale' in axis)) {
      throw new Error('Chart numeric bounds use min and max, not minimumScale/maximumScale.');
    }
  }
  const axis = config => ({textStyle: {fontSize: 21, fill: colors.purple},
    majorGridlines: {fill: colors.line, width: 0.6}, ...config});
  const c = slide.charts.add(type, {chartFill: 'none', chartLine: noLine,
    plotAreaFill: 'none', plotAreaLine: noLine, hasLegend: false,
    titlePlacement: options.title ? 'aboveChart' : 'none', ...options,
    series: options.series?.map((s, i) => ({fill: [colors.purple, colors.secondary, colors.gold][i % 3], ...s})),
    xAxis: axis(options.xAxis), yAxis: axis(options.yAxis)});
  const styles = [c.legend?.textStyle, c.dataLabels?.textStyle, c.xAxis?.textStyle,
    c.yAxis?.textStyle];
  // Accessing titleTextStyle materializes an empty native chart title. Only set
  // its font when a real title was requested; a nearby slide heading may suffice.
  if (options.title) styles.push(c.titleTextStyle);
  for (const a of [c.xAxis, c.yAxis]) if (a?.title?.text) styles.push(a.title.textStyle);
  for (const style of styles) if (style) style.typeface = font ?? zhFont;
  // Axis identifiers describe OOXML categories/values; a horizontal bar still uses
  // xAxis for categories and yAxis for values. Scatter uses two numeric axes.
  if (type === 'scatter' || type === 'bubble') c.xAxis.textStyle.typeface = font ?? latinFont;
  if (c.yAxis?.textStyle) c.yAxis.textStyle.typeface = font ?? latinFont;
  if (c.dataLabels?.textStyle && !options.dataLabels?.showCategoryName && !options.dataLabels?.showSeriesName) {
    c.dataLabels.textStyle.typeface = font ?? latinFont;
  }
  return c;
}

export function arrow(slide, {from, to, fromSide = 'right', toSide = 'left',
  x, y, w, h = 0, kind = 'straight', color = colors.gold, width = 2.5} = {}) {
  const options = {kind, line: {fill: color, width}, tail: {type: 'triangle', width: 'med', length: 'med'}};
  if (from && to) return slide.shapes.connect(from, to, {...options, fromSide, toSide});
  if (from || to) throw new Error('Provide both from/to shapes, or provide an unattached position.');
  if (![x, y, w, h].every(Number.isFinite) || w < 0 || h < 0 || w + h <= 0) {
    throw new Error('An unattached arrow needs finite x/y/w/h and a positive extent.');
  }
  // geometry:'line' ignores arrowhead configuration in this runtime.
  return slide.shapes.add({geometry: 'connector',
    position: {left: x, top: y, width: w, height: h}, ...options});
}

export async function createDeck({skillDir, title, subtitle = '', presenter, date,
  zhFont = fonts.zh, latinFont = fonts.latin}) {
  if (!skillDir || !title) throw new Error('createDeck requires skillDir and the actual title.');
  if (!String(presenter ?? '').trim() || !String(date ?? '').trim()) {
    throw new Error('封面必须提供汇报人和汇报时间；缺项应明确核实，不能静默留空。');
  }
  const contract = JSON.parse(await fs.readFile(path.join(skillDir, 'assets/style-contract.json'), 'utf8'));
  const cv = contract.cover;
  if (![zhFont, latinFont].every(f => typeof f === 'string' && f.trim())) {
    throw new Error('zhFont and latinFont must be nonempty installed font family names.');
  }
  const fontOptions = {zhFont, latinFont};
  const deckText = (owner, value, options) => text(owner, value, {...fontOptions, ...options});
  const deckTable = (slide, values, options) => nativeTable(slide, values, {...fontOptions, ...options});
  const deckChart = (slide, type, options, overrides = {}) => chart(slide, type, options, {...fontOptions, ...overrides});
  const assets = path.join(skillDir, 'assets');
  const presentation = await PresentationFile.importPptx(await FileBlob.load(path.join(assets, 'source-original.pptx')));
  presentation.slides.keep([0]);
  presentation.theme.defaultFont = zhFont;
  presentation.theme.colorScheme = {name: 'Hualang Purple Gold', themeColors: {
    accent1: colors.purple, accent2: colors.gold, accent3: colors.secondary,
    accent4: colors.line, accent5: colors.pale, accent6: colors.paper,
    bg1: colors.paper, bg2: colors.purple, tx1: colors.purple, tx2: colors.secondary,
    dk1: colors.purple, dk2: colors.secondary, lt1: colors.white, lt2: colors.pale,
    hlink: colors.purple, folHlink: colors.secondary,
  }};
  // This preserved source has a single title shape on slide 0; pictures, the
  // original geometric cover and school artwork stay in the imported layout.
  const cover = presentation.slides.items[0];
  const coverLayout = presentation.layouts.getById('/ppt/slideLayouts/slideLayout1.xml');
  if (!coverLayout || coverLayout.shapes.items.length !== 2) {
    throw new Error('The source cover layout has changed; inspect its brand shapes before proceeding.');
  }
  coverLayout.background.fill = colors.purple;
  coverLayout.shapes.items[0].fill = colors.gold;
  coverLayout.shapes.items[1].fill = colors.purple;
  const coverTitle = cover.shapes.items[0];
  if (!coverTitle) throw new Error('The source cover title is missing; inspect the template before proceeding.');
  coverTitle.name = cv.title.name;
  coverTitle.position = {left: cv.title.x, top: cv.title.y, width: cv.title.w, height: cv.title.h};
  styleText(coverTitle, title, {...fontOptions, size: cv.title.size, color: colors.white, bold: true});
  const field = (key, value, extra = {}) => {
    const f = cv[key];
    return deckText(cover, value, {x:f.x,y:f.y,w:f.w,h:f.h,size:f.size,color:colors.white,name:f.name,...extra});
  };
  if (subtitle) field('subtitle', subtitle);
  field('presenter', '汇报人：' + String(presenter).replace(/^汇报人[：:]\s*/, ''));
  field('date', '汇报时间：' + String(date).replace(/^汇报时间[：:]\s*/, ''), {align:'right'});


  const brand = async (owner, dark = false) => image(owner,
    path.join(assets, dark ? 'logo-gold.png' : 'logo-horizontal.png'),
    {x: 1093, y: 25, w: 139, h: 49, alt: '深圳市华朗学校原始标识'});
  const layout = presentation.layouts.add('华朗统一紫金正文');
  layout.background.fill = colors.paper;
  await brand(layout);
  line(layout, {x: 48, y: 99, w: 1184, color: colors.gold, width: 1.4});

  const footer = (slide, section, dark = false) => {
    const color = dark ? colors.line : colors.secondary;
    if (section) deckText(slide, section, {x: 48, y: 679, w: 1090, h: 21, size: 14, color});
    deckText(slide, String(presentation.slides.items.length).padStart(2, '0'),
      {x: 1190, y: 677, w: 42, h: 24, size: 15, color, align: 'right'});
  };
  function addPage({title: pageTitle, summary = '', section = '', titleSize = 36, userSuppliedTitle = false}) {
    assertTopicTitle(pageTitle, {userSupplied:userSuppliedTitle});
    const slide = presentation.slides.add({layoutId: layout.id});
    deckText(slide, pageTitle, {x: 48, y: 32, w: 1010, h: 57, size: titleSize, bold: true, name: 'title'});
    if (summary) deckText(slide, summary, {x: 48, y: 120, w: 1184, h: 68, size: 25, name: 'summary'});
    footer(slide, section);
    return slide;
  }

  function addReportPage({title, summary, section = ''}) {
    const slide = addPage({title, summary, section});
    return {slide, areas:{evidence:{x:48,y:215,w:1184,h:335}, note:{x:48,y:578,w:1184,h:72}}};
  }
  // Observation is one lesson pattern. Mathematics and text analysis have
  // separate geometry below; callers must choose from their actual material.
  function addLessonPage({title, task, section = ''}) {
    if (!String(task ?? '').trim()) throw new Error('课堂观察页必须有完整学习任务。');
    const slide = addPage({title, section});
    deckText(slide, task, {x:48,y:126,w:1184,h:80,size:36,bold:true,name:'learning-task'});
    return {slide, areas:{visual:{x:48,y:228,w:740,h:405}, prompts:{x:838,y:228,w:394,h:405}}};
  }
  function addParentPage({title, headline, section = ''}) {
    if (!String(headline ?? '').trim()) throw new Error('家长图文页需要具体沟通主题。');
    const slide = addPage({title, section});
    deckText(slide, headline, {x:48,y:464,w:1184,h:54,size:34,bold:true,name:'parent-headline'});
    return {slide, areas:{visual:{x:48,y:130,w:1184,h:305}, support:{x:48,y:545,w:1184,h:100}}};
  }

  function addMathPage({title, mode = 'single', section = ''}) {
    if (!['single','pair','proof'].includes(mode)) throw new Error('Math mode: single, pair or proof.');
    const slide = addPage({title, section});
    if (mode === 'pair') {
      line(slide,{x:640,y:144,w:0,h:488,color:colors.line});
      return {slide, areas:{left:{x:48,y:140,w:552,h:500},right:{x:680,y:140,w:552,h:500}}};
    }
    return {slide, areas:{stem:{x:48,y:132,w:1184,h:146},
      work:{x:48,y:304,w:mode === 'proof' ? 1184 : 674,h:344},
      diagram:mode === 'proof' ? null : {x:770,y:304,w:462,h:344}}};
  }

  function addPhotoEssay({title, section = '', orientation = 'left'}) {
    if (!['left','right'].includes(orientation)) throw new Error('Photo essay orientation: left or right.');
    const slide = addPage({title,section});
    const flip = r => orientation === 'left' ? r : {...r,x:1280-r.x-r.w};
    return {slide,areas:{hero:flip({x:48,y:140,w:754,h:450}),
      detailTop:flip({x:826,y:140,w:406,h:210}),detailBottom:flip({x:826,y:376,w:406,h:214}),
      caption:{x:48,y:612,w:1184,h:42}}};
  }

  async function addEditorial({title, section = '', dark = false}) {
    assertTopicTitle(title);
    const slide = presentation.slides.add();
    slide.background.fill = dark ? colors.purple : colors.paper;
    await brand(slide,dark);
    deckText(slide,title,{x:48,y:30,w:920,h:46,size:29,bold:true,
      color:dark?colors.white:colors.purple,name:'scene-title'});
    footer(slide,section,dark);
    return slide;
  }

  const revealSlides = new Map();
  function registerReveal(slide, objects, {label = ''} = {}) {
    if (!objects?.length || objects.some(o => typeof o !== 'string' && (!o || !o.id))) throw new Error('A reveal step requires actual native objects or verified exported object names.');
    const index = presentation.slides.items.indexOf(slide)+1;
    if (!index) throw new Error('Reveal slide is not in this deck.');
    const steps = revealSlides.get(index) ?? [];
    const used = new Set(steps.flatMap(s=>s.objectIds));
    const ids=objects.map(o=>typeof o==='string'?'name:'+o:o.id);
    if (ids.some(id=>used.has(id)) || new Set(ids).size!==objects.length) throw new Error('An object can enter only once.');
    const names = objects.map((o,i)=>{
      if(typeof o==='string') return o;
      const name=`reveal-s${index}-step${steps.length+1}-${i+1}`;
      o.name=name; return name;
    });
    steps.push({label,objects:names,objectIds:ids});
    revealSlides.set(index,steps);
    return names;
  }
  async function writeRevealManifest(file) {
    const manifest={schemaVersion:1,effect:'appear',slides:[...revealSlides].map(([slide,steps])=>({slide,
      steps:steps.map(({label,objects})=>({label,objects}))}))};
    await fs.writeFile(file,JSON.stringify(manifest,null,2));return manifest;
  }

  function fraction(slide,numerator,denominator,{x,y,w=92,size=32,name='fraction',color=colors.purple}={}) {
    // Native text and rule stay editable. Suitable for a simple fraction only.
    const top=deckText(slide,numerator,{x,y,w,h:size*1.3,size,align:'center',font:'Times New Roman',name:name+'-num',color});
    const rule=line(slide,{x,y:y+size*1.33,w,color,width:1.5});
    const bottom=deckText(slide,denominator,{x,y:y+size*1.46,w,h:size*1.3,size,align:'center',font:'Times New Roman',name:name+'-den',color});
    return [top,rule,bottom];
  }

  async function addStage({title: pageTitle, subtitle: sub = '', section = '',
    imagePath, imageAlt, heading = '', titleSize = imagePath ? 64 : 78,
    subtitleSize = imagePath ? 38 : 40, brandBacking = true}) {
    if (!pageTitle) throw new Error('addStage requires the actual page title.');
    if (heading) assertTopicTitle(heading);
    if (/(^先|先.+再|然后|接着)/.test(pageTitle)) throw new Error('演讲主句不采用流程口播句式。');
    const slide = presentation.slides.add();
    slide.background.fill = colors.purple;
    if (imagePath) {
      await image(slide, imagePath, {x: 0, y: 0, w: 1280, h: 480, alt: imageAlt, fit: 'cover'});
      deckText(slide, pageTitle, {x: 55, y: 510, w: 1170, h: 92, size: titleSize, color: colors.white, bold: true});
      if (sub) deckText(slide, sub, {x: 59, y: 615, w: 1100, h: 56, size: subtitleSize, color: colors.white});
      if (brandBacking) slide.shapes.add({geometry: 'rect', name: 'brand-backing',
        position: {left: 1080, top: 12, width: 165, height: 74}, fill: colors.purple, line: noLine});
    } else {
      line(slide, {x: 60, y: 159, w: 1160, color: colors.gold, width: 2});
      deckText(slide, pageTitle, {x: 60, y: 250, w: 1130, h: 244, size: titleSize, color: colors.white, bold: true});
      if (sub) deckText(slide, sub, {x: 64, y: 555, w: 1110, h: 104, size: subtitleSize, color: colors.gold});
    }
    await brand(slide, true);
    if (heading) deckText(slide, heading, {x:48,y:32,w:900,h:50,size:32,color:colors.white,bold:true,name:'scene-title'});
    footer(slide, section, true);
    return slide;
  }
  async function writeDraft({candidatePath, renderDir, scale = 1.5}) {
    if (!candidatePath || !renderDir) throw new Error('writeDraft requires candidatePath and renderDir.');
    await fs.mkdir(path.dirname(candidatePath), {recursive: true});
    await fs.mkdir(renderDir, {recursive: true});
    await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
    const renderPaths = [];
    for (let i = 0; i < presentation.slides.items.length; i++) {
      const slide = presentation.slides.items[i], stem = `slide-${String(i + 1).padStart(2, '0')}`;
      const pngPath = path.join(renderDir, `${stem}.png`);
      const png = await presentation.export({slide, format: 'png', scale});
      await fs.writeFile(pngPath, new Uint8Array(await png.arrayBuffer()));
      await fs.writeFile(path.join(renderDir, `${stem}.layout.json`), await (await slide.export({format: 'layout'})).text());
      renderPaths.push(pngPath);
    }
    return {candidatePath, renderPaths, slideCount: presentation.slides.items.length};
  }
  return {presentation, cover, addPage, addReportPage, addLessonPage, addParentPage, addStage, addMathPage,
    addPhotoEssay,addEditorial,registerReveal,writeRevealManifest,fraction,text: deckText,image,
    nativeTable: deckTable, chart: deckChart, line, arrow, writeDraft};
}
