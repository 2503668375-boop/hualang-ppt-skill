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
    plotAreaFill: 'none', plotAreaLine: noLine, hasLegend: false, ...options,
    series: options.series?.map((s, i) => ({fill: [colors.purple, colors.secondary, colors.gold][i % 3], ...s})),
    xAxis: axis(options.xAxis), yAxis: axis(options.yAxis)});
  const styles = [c.legend?.textStyle, c.dataLabels?.textStyle, c.xAxis?.textStyle,
    c.yAxis?.textStyle, c.titleTextStyle];
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

export async function createDeck({skillDir, title, subtitle = '', presenter = '', date = '',
  zhFont = fonts.zh, latinFont = fonts.latin}) {
  if (!skillDir || !title) throw new Error('createDeck requires skillDir and the actual title.');
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
  coverTitle.position = {left: 60, top: 488, width: 1120, height: 70};
  styleText(coverTitle, title, {...fontOptions, size: 45, color: colors.white, bold: true});
  if (subtitle) deckText(cover, subtitle, {x: 64, y: 568, w: 1100, h: 50, size: 31, color: colors.white});
  if (presenter) deckText(cover, presenter, {x: 65, y: 638, w: 880, h: 36, size: 21, color: colors.white});
  if (date) deckText(cover, date, {x: 1000, y: 640, w: 230, h: 30, size: 20, color: colors.white, align: 'right'});

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
  function addPage({title: pageTitle, summary = '', section = '', titleSize = 36}) {
    if (!pageTitle) throw new Error('addPage requires the actual page title.');
    const slide = presentation.slides.add({layoutId: layout.id});
    deckText(slide, pageTitle, {x: 48, y: 32, w: 1010, h: 57, size: titleSize, bold: true, name: 'title'});
    if (summary) deckText(slide, summary, {x: 48, y: 120, w: 1184, h: 68, size: 25, name: 'summary'});
    footer(slide, section);
    return slide;
  }
  async function addStage({title: pageTitle, subtitle: sub = '', section = '',
    imagePath, imageAlt, titleSize = imagePath ? 64 : 78,
    subtitleSize = imagePath ? 38 : 40, brandBacking = true}) {
    if (!pageTitle) throw new Error('addStage requires the actual page title.');
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
  return {presentation, cover, addPage, addStage, text: deckText, image,
    nativeTable: deckTable, chart: deckChart, line, arrow, writeDraft};
}
