import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob, PresentationFile} from '@oai/artifact-tool';

export const colors = Object.freeze({
  purple: '#403653', ink: '#222222', secondary: '#666666', gold: '#BCA36D',
  red: '#B4232C', blue: '#1B385B', paper: '#FDFDFE', pale: '#F0ECF5',
  line: '#D8D8D8', white: '#FFFFFF',
});
export const fonts = Object.freeze({zh: 'PingFang SC', latin: 'Arial'});
export const canvas = Object.freeze({width: 1280, height: 720});
export const profiles = Object.freeze({
  report:{title:28,body:21,summary:22,table:19},
  lessonPlan:{title:28,body:20,summary:21,table:19},
  classroom:{title:30,body:25,summary:25,table:23},
  worksheet:{title:28,body:24,summary:24,table:22},
  parent:{title:28,body:28,summary:28,table:24},
  stage:{title:28,body:30,summary:30,table:26},
});
const noLine = {fill: 'none', width: 0};

export function assertTopicTitle(value, {userSupplied = false} = {}) {
  const title = String(value ?? '').trim();
  if (!title) throw new Error('页面题名不能为空。');
  if (userSupplied) return title;
  // Short Chinese phrases are an editorial preference, not a word limit for
  // subject terminology, formulas or English headings. Check fit after export.
  const conversational = /^(先.+再|然后|接着|怎样|怎么|如何|本页|我们|你[们的要可]|哪些|什么|它[的是]|从.+开始)/;
  if (/[\u3400-\u9fff]/.test(title) && (conversational.test(title) || /[？?]/.test(title))) {
    throw new Error('自动题名使用具体议题短语，课堂问句放在任务区：' + title);
  }
  return title;
}


// CSS pixels at 96 dpi. Keep the content geometry under the caller's control.
export function text(owner, value, {x, y, w, h, size = 22, color = colors.ink,
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
  rowHeights, size = 20, numericColumns = [], focusRow = -1,
  headerStyle = 'purple', labelColumns = [], cellPadding = {left:12,right:12,top:6,bottom:6},
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
      cell.fill = r === 0 ? (headerStyle === 'purple' ? colors.purple : colors.pale) : r === focusRow ? colors.pale : colors.paper;
      styleText(cell, values[r][c], {size, font, zhFont, latinFont, lineSpacing:1.12,
        color:r === 0 ? (headerStyle === 'purple' ? colors.white : colors.purple) : labelColumns.includes(c) ? colors.purple : colors.ink,
        bold: r === 0 || r === focusRow || labelColumns.includes(c), align: r > 0 && numericColumns.includes(c) ? 'right' : 'left'});
      cell.text.style = {verticalAlignment: 'middle', insets:cellPadding};
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
  const axis = config => ({textStyle: {fontSize: 19, fill: colors.ink},
    majorGridlines: {fill: colors.line, width: 0.6}, ...config});
  const c = slide.charts.add(type, {chartFill: 'none', chartLine: noLine,
    plotAreaFill: 'none', plotAreaLine: noLine, hasLegend: false,
    titlePlacement: options.title ? 'aboveChart' : 'none', ...options,
    series: options.series?.map((s, i) => ({fill: [colors.blue, colors.secondary, colors.red][i % 3], ...s})),
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
  options.series?.forEach((s,i)=>{if(s.dataLabels)c.series.getItemAt(i).dataLabels.textStyle.typeface=font ?? latinFont;});
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

export async function createDeck({skillDir, title, subtitle = '', subtitlePurpose = '', presenter, date,
  zhFont = fonts.zh, latinFont = fonts.latin, mathFont = 'Times New Roman',
  closingText = '汇报完毕，敬请指导', closingMotto = '华夏俊采，朗若星辰'}) {
  if (!skillDir || !title) throw new Error('createDeck requires skillDir and the actual title.');
  if (!String(presenter ?? '').trim() || !String(date ?? '').trim()) {
    throw new Error('封面必须提供汇报人和汇报时间；缺项应明确核实，不能静默留空。');
  }
  const contract = JSON.parse(await fs.readFile(path.join(skillDir, 'assets/style-contract.json'), 'utf8'));
  const cv = contract.cover;
  if (![zhFont, latinFont].every(f => typeof f === 'string' && f.trim())) {
    throw new Error('zhFont and latinFont must be nonempty installed font family names.');
  }
  if (subtitle && !['scope','user_request'].includes(subtitlePurpose)) {
    throw new Error('封面默认一个主标题；副题需填写独立范围或用户明确要求的 subtitlePurpose。');
  }
  const fontOptions = {zhFont, latinFont};
  const pageProfiles = new Map();
  const deckText = (owner,value,options={}) => text(owner,value,
    {size:profiles[pageProfiles.get(owner.id) ?? 'report'].body,color:colors.ink,...fontOptions,...options});
  const deckTable = (slide, values, options={}) => nativeTable(slide, values,
    {size:profiles[pageProfiles.get(slide.id) ?? 'report'].table,...fontOptions,...options});
  const deckChart = (slide, type, options, overrides = {}) => chart(slide, type, options, {...fontOptions, ...overrides});
  const assets = path.join(skillDir, 'assets');
  const presentation = await PresentationFile.importPptx(await FileBlob.load(path.join(assets, 'source-original.pptx')));
  const closingIndex = contract.closing.sourceSlide-1;
  if (!presentation.slides.items[closingIndex]) throw new Error('原模板封尾缺失。');
  presentation.slides.keep([0,closingIndex]);
  const closing = presentation.slides.items[1];
  deckText(closing,closingMotto,{x:100,y:220,w:1080,h:74,size:48,bold:true,color:colors.white,align:'center',name:'closing-motto'});
  deckText(closing,closingText,{x:100,y:340,w:1080,h:52,size:28,color:colors.white,align:'center',name:'closing-message'});
  const ensureClosing = () => {
    if (!presentation.slides.items.includes(closing)) throw new Error('固定封尾被移除，请恢复原模板封尾。');
    presentation.slides.reorder([...presentation.slides.items.filter(s=>s!==closing).map(s=>s.id),closing.id]);
  };
  const addContentSlide = (options={}) => {
    const slide=presentation.slides.add(options);ensureClosing();return slide;
  };
  presentation.theme.defaultFont = zhFont;
  presentation.theme.colorScheme = {name: 'Hualang Purple Gold', themeColors: {
    accent1: colors.blue, accent2: colors.red, accent3: colors.secondary,
    accent4: colors.line, accent5: colors.pale, accent6: colors.paper,
    bg1: colors.paper, bg2: colors.purple, tx1: colors.ink, tx2: colors.secondary,
    dk1: colors.ink, dk2: colors.secondary, lt1: colors.white, lt2: colors.pale,
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
  field('date', '汇报时间：' + String(date).replace(/^汇报时间[：:]\s*/, ''), {align:'left'});


  const brand = async (owner, dark = false) => image(owner,
    path.join(assets, dark ? 'logo-gold.png' : 'logo-horizontal.png'),
    {x: 1093, y: 25, w: 139, h: 49, alt: '深圳市华朗学校原始标识'});
  const layout = presentation.layouts.add('华朗统一紫金正文');
  layout.background.fill = colors.paper;
  // Materialize the unchanged brand on each content slide. Some renderers omit
  // inherited layout objects on shape-only pages, including after re-import.
  const bodyLogo = await fs.readFile(path.join(assets, 'logo-horizontal.png'));
  const bodyLogoBlob = bodyLogo.buffer.slice(bodyLogo.byteOffset, bodyLogo.byteOffset + bodyLogo.byteLength);
  const pageBrand = slide => {
    slide.images.add({blob:bodyLogoBlob,contentType:'image/png',
      position:{left:1093,top:25,width:139,height:49},alt:'深圳市华朗学校原始标识',fit:'contain'});
    line(slide,{x:48,y:86,w:1184,color:colors.gold,width:1.4});
  };

  const footer = (slide, section, dark = false) => {
    const color = dark ? colors.line : colors.secondary;
    if (section) deckText(slide, section, {x: 48, y: 679, w: 1090, h: 21, size: 14, color});
    deckText(slide, String(presentation.slides.items.indexOf(slide)+1).padStart(2, '0'),
      {x: 1190, y: 677, w: 42, h: 24, size: 15, color, align: 'right'});
  };
  function addPage({title: pageTitle, summary = '', section = '', titleSize, purpose = 'report', userSuppliedTitle = false}) {
    assertTopicTitle(pageTitle, {userSupplied:userSuppliedTitle});
    if (!profiles[purpose]) throw new Error('Unknown page purpose: '+purpose);
    const slide=addContentSlide({layoutId:layout.id});pageProfiles.set(slide.id,purpose);
    pageBrand(slide);
    deckText(slide,pageTitle,{x:48,y:30,w:1010,h:43,size:titleSize ?? profiles[purpose].title,bold:true,color:colors.purple,name:'title'});
    if(summary) deckText(slide,summary,{x:48,y:108,w:1184,h:70,size:profiles[purpose].summary,name:'summary'});
    footer(slide, section);
    return slide;
  }

  function addSchoolScene({title,summary='',section='',purpose='report',userSuppliedTitle=false}) {
    return addPage({title,summary,section,purpose,userSuppliedTitle});
  }
  function addReportPage({title, summary, section = ''}) {
    const slide=addPage({title,summary,section,purpose:'report'});
    // content is the open working area; evidence/note remain for older callers.
    return {slide,areas:{content:{x:48,y:summary?196:108,w:1184,h:summary?456:544},
      evidence:{x:48,y:196,w:1184,h:356},note:{x:48,y:572,w:1184,h:80}}};
  }
  // Observation is one lesson pattern. Mathematics and text analysis have
  // separate geometry below; callers must choose from their actual material.
  function addLessonPage({title, task, section = ''}) {
    if (!String(task ?? '').trim()) throw new Error('课堂观察页必须有完整学习任务。');
    const slide = addPage({title,section,purpose:'classroom'});
    deckText(slide, task, {x:48,y:112,w:1184,h:75,size:26,bold:true,name:'learning-task'});
    return {slide, areas:{visual:{x:48,y:228,w:740,h:405}, prompts:{x:838,y:228,w:394,h:405}}};
  }
  function addParentPage({title, headline, section = ''}) {
    if (!String(headline ?? '').trim()) throw new Error('家长图文页需要具体沟通主题。');
    const slide = addPage({title,section,purpose:'parent'});
    deckText(slide, headline, {x:48,y:464,w:1184,h:54,size:34,bold:true,name:'parent-headline'});
    return {slide, areas:{visual:{x:48,y:130,w:1184,h:305}, support:{x:48,y:545,w:1184,h:100}}};
  }

  function addMathPage({title, mode = 'single', section = '', purpose = 'classroom'}) {
    if (!['single','pair','proof'].includes(mode)) throw new Error('Math mode: single, pair or proof.');
    const slide = addPage({title, section,purpose});
    if (mode === 'pair') {
      line(slide,{x:640,y:112,w:0,h:532,color:colors.line});
      return {slide, areas:{left:{x:48,y:112,w:568,h:532},right:{x:664,y:112,w:568,h:532}}};
    }
    return {slide, areas:{stem:{x:48,y:112,w:1184,h:104},
      work:{x:48,y:236,w:mode === 'proof' ? 1184 : 744,h:416},
      diagram:mode === 'proof' ? null : {x:824,y:236,w:408,h:416}}};
  }

  function lessonBand(slide,label,body,{x=48,y=108,w=1184,h=100,size=24,labelWidth=78}={}) {
    const bg=slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:colors.pale,line:noLine});
    const tab=slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:labelWidth,height:h},fill:colors.purple,line:noLine});
    const tag=deckText(slide,label,{x:x+12,y:y+(h-31)/2,w:labelWidth-24,h:31,size:20,bold:true,color:colors.white,align:'center'});
    const content=deckText(slide,body,{x:x+labelWidth+20,y:y+14,w:w-labelWidth-38,h:h-24,size,color:colors.ink});
    return [bg,tab,tag,content];
  }
  function methodStrip(slide,label,body,{x=48,y=602,w=1184,h=50,size=21}={}) {
    const bg=slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:colors.pale,line:noLine});
    const rule=line(slide,{x,y,w:0,h,color:colors.purple,width:3});
    const tag=deckText(slide,label,{x:x+14,y:y+10,w:76,h:h-14,size,bold:true,color:colors.purple});
    const content=deckText(slide,body,{x:x+102,y:y+10,w:w-118,h:h-14,size,color:colors.ink});
    return [bg,rule,tag,content];
  }
  function stepMarker(slide,label,{x=48,y,w=38,size=22}={}) {
    return deckText(slide,label,{x,y,w,h:35,size,bold:true,color:colors.purple});
  }

  function addLessonPlanPage({title,section=''}) {
    const slide=addPage({title,section,purpose:'lessonPlan'});
    return {slide,areas:{context:{x:48,y:108,w:1184,h:124},sequence:{x:48,y:254,w:1184,h:326},assessment:{x:48,y:602,w:1184,h:50}}};
  }

  function addPhotoEssay({title, section = '', orientation = 'left'}) {
    if (!['left','right'].includes(orientation)) throw new Error('Photo essay orientation: left or right.');
    const slide = addPage({title,section,purpose:'parent'});
    const flip = r => orientation === 'left' ? r : {...r,x:1280-r.x-r.w};
    return {slide,areas:{hero:flip({x:48,y:140,w:754,h:450}),
      detailTop:flip({x:826,y:140,w:406,h:210}),detailBottom:flip({x:826,y:376,w:406,h:214}),
      caption:{x:48,y:612,w:1184,h:42}}};
  }

  async function addEditorial({title, section = '', dark = false}) {
    assertTopicTitle(title);
    const slide = addContentSlide();
    slide.background.fill = dark ? colors.purple : colors.paper;
    await brand(slide,dark);
    deckText(slide,title,{x:48,y:30,w:920,h:46,size:29,bold:true,
      color:dark?colors.white:colors.ink,name:'scene-title'});
    footer(slide,section,dark);
    return slide;
  }

  const revealSlides = new Map();
  function registerReveal(slide, objects, {label = ''} = {}) {
    if (!objects?.length || objects.some(o => typeof o !== 'string' && (!o || !o.id))) throw new Error('A reveal step requires actual native objects or verified exported object names.');
    ensureClosing();
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

  function fraction(slide,numerator,denominator,{x,y,w=92,size=32,name='fraction',color=colors.ink}={}) {
    // Native text and rule stay editable. Suitable for a simple fraction only.
    const top=deckText(slide,numerator,{x,y,w,h:size*1.3,size,align:'center',font:mathFont,name:name+'-num',color});
    const rule=line(slide,{x,y:y+size*1.33,w,color,width:1.5});
    const bottom=deckText(slide,denominator,{x,y:y+size*1.46,w,h:size*1.3,size,align:'center',font:mathFont,name:name+'-den',color});
    return [top,rule,bottom];
  }

  function schoolIcon(slide,kind,{x,y,size=52,color=colors.purple,badge=false,fill=colors.purple}={}){
    const out=[],scale=size/64;
    if(badge)out.push(slide.shapes.add({geometry:'ellipse',position:{left:x-13*scale,top:y-13*scale,width:size+26*scale,height:size+26*scale},fill,line:noLine}));
    const stroke=badge?colors.white:color;
    const ln=(a,b,c,d)=>out.push(slide.shapes.add({geometry:'custom',position:{left:x,top:y,width:size,height:size},fill:'none',line:{fill:stroke,width:2.4*scale},customPaths:[{width:64,height:64,commands:[{moveTo:{x:a,y:b}},{lineTo:{x:c,y:d}}]}]}));
    const rect=(a,b,w,h)=>out.push(slide.shapes.add({geometry:'rect',position:{left:x+a*scale,top:y+b*scale,width:w*scale,height:h*scale},fill:'none',line:{fill:stroke,width:2.4*scale}}));
    const circle=(a,b,r)=>out.push(slide.shapes.add({geometry:'ellipse',position:{left:x+(a-r)*scale,top:y+(b-r)*scale,width:r*2*scale,height:r*2*scale},fill:'none',line:{fill:stroke,width:2.4*scale}}));
    const poly=(p,closed=false)=>out.push(slide.shapes.add({geometry:'custom',position:{left:x,top:y,width:size,height:size},fill:'none',line:{fill:stroke,width:2.4*scale},customPaths:[{width:64,height:64,commands:[{moveTo:{x:p[0][0],y:p[0][1]}},...p.slice(1).map(v=>({lineTo:{x:v[0],y:v[1]}})),...(closed?[{close:{}}]:[])]}]}));
    if(kind==='book'){poly([[8,15],[27,15],[32,20],[37,15],[56,15],[56,51],[37,51],[32,56],[27,51],[8,51]],true);ln(32,20,32,56);ln(14,25,25,25);ln(14,32,25,32);ln(39,25,50,25);ln(39,32,50,32);}
    else if(kind==='people'){circle(24,18,9);circle(46,21,7);poly([[7,54],[7,43],[14,34],[34,34],[41,43],[41,54]],false);poly([[42,36],[50,36],[57,44],[57,54]],false);}
    else if(kind==='target'){circle(32,32,23);circle(32,32,14);circle(32,32,4);ln(32,32,54,10);poly([[45,10],[54,10],[54,19]],false);}
    else if(kind==='globe'){circle(32,32,24);out.push(slide.shapes.add({geometry:'ellipse',position:{left:x+21*scale,top:y+8*scale,width:22*scale,height:48*scale},fill:'none',line:{fill:stroke,width:2*scale}}));ln(8,32,56,32);ln(13,19,51,19);ln(13,45,51,45);}
    else if(kind==='chart'){ln(9,9,9,56);ln(9,56,59,56);rect(17,35,8,21);rect(32,24,8,32);rect(47,12,8,44);}
    else if(kind==='cap'){poly([[6,24],[32,10],[58,24],[32,38]],true);poly([[17,31],[17,45],[32,52],[47,45],[47,31]],false);ln(58,24,58,47);circle(58,50,3);}
    else if(kind==='case'){rect(7,21,50,33);poly([[22,21],[22,12],[42,12],[42,21]],false);ln(7,35,57,35);rect(28,31,8,9);}
    else if(kind==='calendar'){rect(8,14,48,43);ln(8,27,56,27);ln(19,7,19,21);ln(45,7,45,21);rect(18,35,8,8);rect(36,35,8,8);}
    else if(kind==='science'){poly([[23,8],[41,8],[41,13],[37,13],[37,27],[53,52],[50,57],[14,57],[11,52],[27,27],[27,13],[23,13]],true);ln(19,42,45,42);circle(32,48,2);}
    else throw new Error('Unknown school icon '+kind);
    return out;
  }
  function numberBadge(slide,label,{x,y,size=56,fill=colors.purple,color=colors.white}={}){
    return [slide.shapes.add({geometry:'ellipse',position:{left:x,top:y,width:size,height:size},fill,line:noLine}),deckText(slide,label,{x,y:y+size*.23,w:size,h:size*.5,size:size*.35,bold:true,color,font:latinFont,align:'center'})];
  }
  function iconLabel(slide,kind,title,body,{x,y,w=340,iconSize=42,fill=colors.purple}={}){
    const out=schoolIcon(slide,kind,{x:x+10,y:y+10,size:iconSize,badge:true,fill});
    out.push(deckText(slide,title,{x:x+iconSize+38,y:y-1,w:w-iconSize-38,h:42,size:27,bold:true,color:colors.purple}));
    if(body)out.push(deckText(slide,body,{x:x+iconSize+38,y:y+48,w:w-iconSize-38,h:70,size:22,color:colors.ink}));return out;
  }
  function sectionRule(slide,label,{x=48,y=109,w=1184,size=41}={}){
    const out=[slide.shapes.add({geometry:'rect',position:{left:x,top:y+5,width:7,height:46},fill:colors.purple,line:noLine}),deckText(slide,label,{x:x+23,y,w:w-23,h:66,size,bold:true,color:colors.purple})];return out;
  }
  function photoLabel(slide,label,{x,y,w,h=42,fill=colors.purple}={}){
    return [slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:noLine}),deckText(slide,label,{x:x+17,y:y+9,w:w-34,h:h-12,size:20,bold:true,color:colors.white})];
  }
  function pointBand(slide,items,{x=48,y=570,w=1184,h=90,fill=colors.purple}={}){
    const out=[slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:noLine})],cw=w/items.length;
    items.forEach((it,i)=>{const sx=x+i*cw;out.push(...schoolIcon(slide,it.icon,{x:sx+30,y:y+25,size:40,color:colors.white}),deckText(slide,it.text,{x:sx+92,y:y+27,w:cw-118,h:45,size:27,bold:true,color:colors.white}));if(i)out.push(line(slide,{x:sx,y:y+20,w:0,h:h-40,color:'#796A91',width:1}));});return out;
  }

  function purpleRibbon(slide,label,{x,y,w,h=54,size=25,fill=colors.purple}={}){
    const bg=slide.shapes.add({geometry:'parallelogram',position:{left:x,top:y,width:w,height:h},fill,line:noLine});
    const tx=deckText(slide,label,{x:x+28,y:y+(h-size*1.2)/2,w:w-56,h:size*1.35,size,bold:true,color:colors.white});return [bg,tx];
  }
  function lightFrame(slide,{x,y,w,h,offset=15,color=colors.purple}={}){
    return [line(slide,{x,y,w,color,width:3}),line(slide,{x,y,w:0,h,color,width:3}),
      line(slide,{x:x+w,y:y+offset,w:0,h:h-offset,color,width:3}),
      line(slide,{x:x+offset,y:y+h,w:w-offset,color,width:3}),
      line(slide,{x:x-offset,y:y+offset,w:0,h:h-2*offset,color:colors.gold,width:5})];
  }
  function focusPanel(slide,{x,y,w,h,kicker='',main,detail='',size=42}={}){
    const out=[slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:colors.purple,line:noLine})];
    if(kicker)out.push(deckText(slide,kicker,{x:x+28,y:y+23,w:w-56,h:30,size:20,color:colors.gold}));
    out.push(deckText(slide,main,{x:x+28,y:y+(kicker?70:26),w:w-56,h:h-(detail?95:40),size,bold:true,color:colors.white}));
    if(detail)out.push(deckText(slide,detail,{x:x+28,y:y+h-60,w:w-56,h:42,size:20,color:colors.white}));return out;
  }
  function numberFlag(slide,value,label,{x,y,w=315,h=300,caption=''}={}){
    const out=[slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:colors.purple,line:noLine}),line(slide,{x:x+25,y:y+30,w:65,color:colors.gold,width:4}),
      deckText(slide,value,{x:x+25,y:y+55,w:w-50,h:135,size:96,bold:true,color:colors.white,font:latinFont}),
      deckText(slide,label,{x:x+25,y:y+198,w:w-50,h:60,size:30,bold:true,color:colors.white})];
    if(caption)out.push(deckText(slide,caption,{x:x+25,y:y+h-43,w:w-50,h:31,size:18,color:colors.white}));return out;
  }
  function starOrbit(slide,{cx,cy,r=170,main='每生\n一案',nodes=[]}={}){
    const out=[slide.shapes.add({geometry:'ellipse',position:{left:cx-r,top:cy-r,width:r*2,height:r*2},fill:'none',line:{fill:colors.gold,width:2}}),
      slide.shapes.add({geometry:'ellipse',position:{left:cx-109,top:cy-109,width:218,height:218},fill:colors.purple,line:noLine}),
      deckText(slide,main,{x:cx-95,y:cy-62,w:190,h:145,size:43,bold:true,color:colors.white,align:'center'})];
    for(const n of nodes){const a=n.angle*Math.PI/180,x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r;
      out.push(slide.shapes.add({geometry:'ellipse',position:{left:x-11,top:y-11,width:22,height:22},fill:colors.purple,line:{fill:colors.paper,width:3}}),deckText(slide,n.text,{x:n.tx,y:n.ty,w:n.tw??230,h:45,size:27,bold:true,color:colors.purple,align:n.align??'center'}));
    }return out;
  }
  function stepBands(slide,stages,{x=48,y=520,w=1184,rise=52,boxHeight=122}={}){
    const gap=20,cw=(w-gap*(stages.length-1))/stages.length,out=[];
    stages.forEach((st,i)=>{const sx=x+i*(cw+gap),sy=y-i*rise;
      out.push(slide.shapes.add({geometry:'rect',position:{left:sx,top:sy,width:cw,height:boxHeight},fill:i<2?'#796A91':colors.purple,line:noLine}),
        deckText(slide,st.title,{x:sx+20,y:sy+20,w:cw-40,h:48,size:32,bold:true,color:colors.white}),
        deckText(slide,st.body,{x:sx+20,y:sy+76,w:cw-40,h:36,size:21,color:colors.white}));
      if(i<stages.length-1)out.push(line(slide,{x:sx+cw,y:sy+boxHeight/2,w:gap,color:colors.gold,width:3}));
    });return out;
  }
  function evidenceStrip(slide,label,body,{x=48,y=608,w=1184,h=52}={}){
    const labelW=190;return [slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:labelW,height:h},fill:colors.purple,line:noLine}),
      deckText(slide,label,{x:x+18,y:y+12,w:labelW-36,h:33,size:23,bold:true,color:colors.white}),
      line(slide,{x:x+labelW,y:y+h,w:w-labelW,color:colors.purple,width:2}),
      deckText(slide,body,{x:x+labelW+22,y:y+11,w:w-labelW-30,h:36,size:23,color:colors.ink})];
  }
  function facetCorner(slide,{x,y,w=220,h=100,color=colors.purple}={}){
    return slide.shapes.add({geometry:'parallelogram',position:{left:x,top:y,width:w,height:h},fill:color,line:noLine});
  }

  // Open components: no enclosing panels or page-level grid is added.
  function metricInline(slide,value,label,{x,y,w=310,unit='',context='',size=64}={}) {
    if(value == null || !String(value).trim() || !String(label??'').trim()) throw new Error('metricInline requires value and meaning.');
    return [deckText(slide,String(value)+(unit?' '+unit:''),{x,y,w,h:size*1.35,size,bold:true,color:colors.purple,name:'metric-value'}),
      deckText(slide,label,{x,y:y+size*1.4,w,h:32,size:22,bold:true,name:'metric-label'}),
      ...(context?[deckText(slide,context,{x,y:y+size*1.4+40,w,h:58,size:18,color:colors.secondary,name:'metric-context'})]:[])];
  }
  function segment(slide,x1,y1,x2,y2,{color=colors.line,width=1.5}={}) {
    const left=Math.min(x1,x2),top=Math.min(y1,y2),w=Math.max(Math.abs(x2-x1),1),h=Math.max(Math.abs(y2-y1),1);
    return slide.shapes.add({geometry:'custom',position:{left,top,width:w,height:h},fill:'none',line:{fill:color,width},
      customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-left,y:y1-top}},{lineTo:{x:x2-left,y:y2-top}}]}]});
  }
  function evidenceNote(slide,body,{x,y,w=280,h=96,anchor,title='',size=21}={}) {
    if(!String(body??'').trim()) throw new Error('evidenceNote requires an explanation.');
    const out=[];
    if(anchor){
      if(!Number.isFinite(anchor.x)||!Number.isFinite(anchor.y)) throw new Error('evidenceNote anchor must be finite.');
      if(anchor.x>=x && anchor.x<=x+w && anchor.y>=y && anchor.y<=y+h) throw new Error('evidenceNote anchor must point outside its text area.');
      const endX=Math.max(x-10,Math.min(x+w+10,anchor.x)),endY=Math.max(y-8,Math.min(y+h+8,anchor.y));
      out.push(segment(slide,anchor.x,anchor.y,endX,endY,{color:colors.purple}),
        slide.shapes.add({geometry:'ellipse',position:{left:anchor.x-3,top:anchor.y-3,width:6,height:6},fill:colors.purple,line:noLine}));
    }
    if(title)out.push(deckText(slide,title,{x,y,w,h:30,size:22,bold:true,color:colors.purple,name:'evidence-note-title'}));
    out.push(deckText(slide,body,{x,y:y+(title?36:0),w,h:h-(title?36:0),size,name:'evidence-note-body'}));
    return out;
  }
  function dotComparison(slide,rows,{x=48,y=196,w=1184,h=360,min=0,max,unit='',
    beforeLabel='目标',afterLabel='实际',labelWidth=170,size=21}={}) {
    if(!rows?.length || !Number.isFinite(min) || !Number.isFinite(max) || max<=min) throw new Error('dotComparison requires rows and a finite increasing domain.');
    for(const r of rows)if(!r.label || ![r.before,r.after].every(v=>Number.isFinite(v)&&v>=min&&v<=max)) throw new Error('dotComparison values must lie in the shared domain.');
    const out=[],plotX=x+labelWidth,plotW=w-labelWidth-100,rowH=(h-75)/rows.length;
    if(plotW<=0 || rowH<44)throw new Error('dotComparison needs enough space for labels and rows.');
    const px=v=>plotX+(v-min)/(max-min)*plotW;
    out.push(deckText(slide,`${beforeLabel} ○　${afterLabel} ●${unit?'　单位：'+unit:''}`,{x:plotX,y,w:plotW,h:30,size:18,color:colors.secondary}),
      deckText(slide,'差额',{x:plotX+plotW+20,y,w:80,h:30,size:18,color:colors.secondary}));
    for(let i=0;i<=4;i++){
      const value=min+(max-min)*i/4,sx=px(value);
      out.push(line(slide,{x:sx,y:y+38,w:0,h:h-67,color:colors.line,width:0.7}),
        deckText(slide,String(Number(value.toFixed(2))),{x:sx-38,y:y+h-25,w:76,h:24,size:16,align:'center',color:colors.secondary}));
    }
    rows.forEach((r,i)=>{
      const sy=y+46+rowH*(i+.5),bx=px(r.before),ax=px(r.after);
      out.push(deckText(slide,r.label,{x,y:sy-14,w:labelWidth-20,h:34,size,bold:true}),
        segment(slide,bx,sy,ax,sy,{color:colors.gold,width:4}),
        slide.shapes.add({geometry:'ellipse',position:{left:bx-6,top:sy-6,width:12,height:12},fill:colors.paper,line:{fill:colors.secondary,width:2}}),
        slide.shapes.add({geometry:'ellipse',position:{left:ax-6,top:sy-6,width:12,height:12},fill:colors.purple,line:noLine}),
        deckText(slide,String(r.before),{x:bx-40,y:sy-31,w:80,h:23,size:17,align:'center',color:colors.secondary}),
        deckText(slide,String(r.after),{x:ax-40,y:sy+9,w:80,h:23,size:17,align:'center',color:colors.purple}),
        deckText(slide,`${r.after-r.before>0?'+':''}${Number((r.after-r.before).toFixed(2))}`,{x:plotX+plotW+20,y:sy-13,w:80,h:30,size:20,bold:true,color:colors.ink}));
    });
    return out;
  }
  function milestoneTimeline(slide,events,{x=48,y=210,w=1184,h=330,start,end,size=21}={}) {
    const iso=v=>{
      if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))throw new Error('Timeline dates require YYYY-MM-DD.');
      const t=Date.parse(v+'T00:00:00Z');
      if(!Number.isFinite(t)||new Date(t).toISOString().slice(0,10)!==v)throw new Error('Invalid timeline date.');
      return t;
    };
    const lo=iso(start),hi=iso(end);
    if(hi<=lo||!events?.length)throw new Error('Timeline requires events and an increasing date range.');
    const located=events.map(e=>({...e,t:iso(e.date)}));
    if(located.some(e=>e.t<lo||e.t>hi||!e.label))throw new Error('Timeline events need labels and dates within range.');
    const axisY=y+h*.47,left=x+30,right=x+w-30,out=[line(slide,{x:left,y:axisY,w:right-left,color:colors.gold,width:2})];
    located.forEach((e,i)=>{
      const cx=left+(e.t-lo)/(hi-lo)*(right-left),tw=e.width??220;
      const tx=e.labelX??Math.max(x,Math.min(x+w-tw,cx-tw/2)),ty=e.labelY??(i%2?axisY+65:y);
      const textH=e.detail?105:34,below=ty>=axisY;
      const endpointY=below?ty-8:ty+textH+8;
      out.push(slide.shapes.add({geometry:'ellipse',position:{left:cx-6,top:axisY-6,width:12,height:12},fill:colors.purple,line:noLine}),
        segment(slide,cx,below?axisY+43:axisY-8,Math.max(tx,Math.min(tx+tw,cx)),endpointY,{color:colors.purple,width:1}),
        deckText(slide,e.date,{x:cx-65,y:axisY+14,w:130,h:25,size:17,align:'center',color:colors.secondary}),
        deckText(slide,e.label,{x:tx,y:ty,w:tw,h:34,size,bold:true,color:colors.purple}),
        ...(e.detail?[deckText(slide,e.detail,{x:tx,y:ty+39,w:tw,h:66,size:size-2})]:[]));
    });
    return out;
  }

  async function addCanvas({purpose='stage',section=''}={}) {
    const slide=addContentSlide();pageProfiles.set(slide.id,purpose);
    slide.background.fill=colors.paper;
    await brand(slide,false);
    if(section) footer(slide,section,false);
    return slide;
  }
  async function addStage({title:pageTitle,subtitle:sub='',section='',imagePath,imageAlt,
    titleSize=76,subtitleSize=28,stageLayout=imagePath?'hero':'statement',imageFit='cover'}) {
    if(!pageTitle) throw new Error('addStage requires the actual main phrase.');
    const slide=await addCanvas({purpose:'stage',section});
    if(imagePath){
      await image(slide,imagePath,{x:48,y:190,w:1184,h:456,alt:imageAlt,fit:imageFit});
      deckText(slide,pageTitle,{x:48,y:92,w:1184,h:90,size:titleSize,bold:true,color:colors.ink,name:'stage-phrase'});
      if(sub) deckText(slide,sub,{x:48,y:654,w:1130,h:28,size:18,color:colors.secondary});
    }else{
      deckText(slide,pageTitle,{x:80,y:215,w:1120,h:240,size:titleSize,bold:true,color:colors.ink,name:'stage-phrase',align:stageLayout==='statement'?'center':'left'});
      if(sub) deckText(slide,sub,{x:90,y:510,w:1100,h:95,size:subtitleSize,color:colors.secondary,align:'center'});
    }
    return slide;
  }
  async function writeDraft({candidatePath, renderDir, scale = 1.5}) {
    if (!candidatePath || !renderDir) throw new Error('writeDraft requires candidatePath and renderDir.');
    ensureClosing();
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
  return {presentation, cover, closing, lessonBand, methodStrip, stepMarker, addLessonPlanPage, addPage, addReportPage, addLessonPage, addParentPage, addStage, addMathPage,
    addPhotoEssay,addEditorial,addCanvas,addSchoolScene,schoolIcon,numberBadge,iconLabel,sectionRule,photoLabel,pointBand,purpleRibbon,lightFrame,focusPanel,numberFlag,starOrbit,stepBands,evidenceStrip,facetCorner,metricInline,evidenceNote,dotComparison,milestoneTimeline,registerReveal,writeRevealManifest,fraction,text: deckText,image,
    nativeTable: deckTable, chart: deckChart, line, arrow, writeDraft};
}
