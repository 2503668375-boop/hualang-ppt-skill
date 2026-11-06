// Simulated management report. Run: node build_layout_demo.mjs skillDir outputDir
// Install @oai/artifact-tool in outputDir or an ancestor before running.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';

const [skillArg, outputArg] = process.argv.slice(2);
if (!skillArg || !outputArg) throw new Error('Provide skillDir and outputDir.');
const skillDir=path.resolve(skillArg), outputDir=path.resolve(outputArg);
await fs.mkdir(outputDir,{recursive:true});
const runtimeKit=path.join(outputDir,'hualang-kit.mjs');
await fs.copyFile(path.join(skillDir,'scripts/hualang-kit.mjs'),runtimeKit);
const {createDeck,colors:C}=await import(pathToFileURL(runtimeKit));
const require=createRequire(pathToFileURL(runtimeKit));
const {FileBlob,PresentationFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const deck=await createDeck({skillDir,title:'年度总结与计划（模拟）',presenter:'示例工作组',date:'2026年11月7日'});
const section='模拟数据与拟议安排｜仅作演示，不代表华朗学校实绩';
const seq=[];
function page(title,summary,family,action,object,conditions){
  const slide=deck.addPage({title,summary,section,purpose:'report'});
  seq.push({slide:seq.length+2,title,family,readerAction:action,primaryEvidence:object,conditions});
  return slide;
}
const tx=(s,v,x,y,w,h,size=21,extra={})=>deck.text(s,v,{x,y,w,h,size,...extra});
const rule=(s,x,y,w,color=C.line,width=1)=>deck.line(s,{x,y,w,color,width});
const rect=(s,x,y,w,h,fill,stroke='none')=>s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:stroke==='none'?0:1}});
const seg=(s,x1,y1,x2,y2,color=C.line,width=1.4)=>{
  const x=Math.min(x1,x2),y=Math.min(y1,y2),w=Math.max(1,Math.abs(x2-x1)),h=Math.max(1,Math.abs(y2-y1));
  return s.shapes.add({geometry:'custom',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width},customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-x,y:y1-y}},{lineTo:{x:x2-x,y:y2-y}}]}]});
};

// 2: Open hierarchy, with one dominant result and explicit evidence boundaries.
{
  const s=page('年度概览','规模保持增长，年度目标仍有差距；教学模拟表现改善，下一年度安排须以持续核对为基础。','open-results-hierarchy','判断全年结果与计划边界','招生主结果与财务、教学层级说明','全部为虚构演示；实绩/目标/拟议与归因边界分清');
  deck.metricInline(s,'500','年度新增学生',{x:48,y:205,w:340,unit:'人',context:'目标550人；上年420人',size:78});
  tx(s,'同比增加80人（+19.0%）\n完成目标90.9%，仍差50人。',48,435,345,100,23);
  tx(s,'1,430 人',48,555,345,42,32,{bold:true,color:C.blue});
  tx(s,'期末在籍；期初1,200人，净增230人。',48,606,345,48,18,{color:C.secondary});
  rule(s,425,202,0,C.line); seg(s,425,202,425,649);
  const items=[
    ['经营结果','实际收入9,100万元、支出8,320万元，收支差780万元，较预算少420万元。收入按本例收支口径表达，不能据此判断到账。'],
    ['教学证据','同一批200人、同一能力框架下，达到标准比例由60%升至75%，提高15个百分点；现有比较不能证明措施因果。'],
    ['下一年方向','建议先统筹共同备课时段，再按诊断决定导师培训范围。以需求复核、阶段复测和资源复盘检验安排；均为模拟拟议。'],
  ];
  items.forEach(([label,body],i)=>{const y=205+i*147;tx(s,label,470,y,744,32,23,{bold:true,color:C.purple});tx(s,body,470,y+42,744,93,21);if(i<2)rule(s,470,y+131,744);});
}
// 3: Shared-scale comparison, with target gaps adjacent to actual values.
{
  const s=page('招生差距','年度招生500人，较上年增加80人；对550人目标仍差50人，三个学段均未达标。','shared-axis-dot-comparison','比较同单位目标与实际，定位缺口','三个学段共用人数轴，端点与差额直接标注','同期新增人数；缺口不等于离校人数；未提供原因资料');
  deck.dotComparison(s,[{label:'初中',before:180,after:165},{label:'高中',before:240,after:225},{label:'国际高中',before:130,after:110}],{x:48,y:205,w:1184,h:315,min:0,max:260,unit:'人',labelWidth:180});
  tx(s,'合计：目标550人　实际500人　差额−50人',48,543,1184,36,24,{bold:true});
  tx(s,'国际高中缺口20人，占总缺口40%；初中与高中各差15人，各占30%。三学段实际合计500人，目标合计550人。',48,592,1184,58,20);
}
// 4: Native data chart for continuous quarterly change, plus exact gaps.
{
  const s=page('季度走势','季度新增人数持续上升，目标差额从一季度20人收窄至四季度10人；全年累计仍差50人。','native-quarterly-trend','追踪年度过程并对照目标','通栏原生折线图与逐季差额','季度实际合计500、目标550；趋势不能直接说明原因');
  deck.chart(s,'line',{position:{left:48,top:198,width:1184,height:325},categories:['Q1','Q2','Q3','Q4'],series:[
    {name:'实际',values:[80,105,145,170],line:{fill:C.blue,width:3},marker:{symbol:'circle',size:7,fill:C.blue},dataLabels:{showValue:true,position:'bottom',textStyle:{fontSize:18,fill:C.blue}}},
    {name:'目标',values:[100,120,150,180],line:{fill:C.secondary,width:2},marker:{symbol:'circle',size:6,fill:C.paper},dataLabels:{showValue:true,position:'top',textStyle:{fontSize:18,fill:C.secondary}}},
  ],hasLegend:true,legend:{position:'top',textStyle:{fontSize:18}},yAxis:{min:0,max:200,majorUnit:50,title:{text:'新增人数（人）'}},xAxis:{majorGridlines:{fill:'none',width:0}},lineOptions:{smooth:false}});
  ['Q1差20人','Q2差15人','Q3差5人','Q4差10人'].forEach((v,i)=>tx(s,v,85+i*289,545,260,35,21,{align:'center',bold:true,color:i===3?C.red:C.ink}));
  tx(s,'Q3差额最小，Q4新增人数最高但缺口较Q3扩大5人。现有材料未包含渠道、转化或家庭选择证据，暂不能解释季度变化原因。',48,602,1184,56,20);
}
// 5: Editable numeric contribution bridge, using one common value scale.
{
  const s=page('在籍勾稽','期末在籍1,430人，由期初1,200人及四项期间增减形成；毕业与退学均属于离校。','enrollment-contribution-bridge','核对规模增减与统计边界','可加总贡献桥与完整算式','新增/转入与毕业/退学分列；招生目标差额不能混入');
  const xs=[145,337,529,721,913,1105],bw=92,top=230,bottom=520,max=1800,py=v=>bottom-v/max*(bottom-top);
  [0,600,1200,1800].forEach(v=>{rule(s,88,py(v),1105,C.line,.6);tx(s,String(v),48,py(v)-12,34,26,15,{color:C.secondary,align:'right'});});
  const data=[['期初',0,1200,'1,200'],['新增',1200,1700,'+500'],['转入',1700,1730,'+30'],['毕业',1450,1730,'−280'],['退学',1430,1450,'−20'],['期末',0,1430,'1,430']];
  data.forEach(([label,lo,hi,value],i)=>{const x=xs[i]-bw/2,y=py(hi),h=Math.max(3,py(lo)-py(hi));rect(s,x,y,bw,h,i===0||i===5?C.purple:i<3?C.blue:C.secondary);tx(s,value,x-20,y-34,bw+40,28,21,{align:'center',bold:true,color:i===5?C.purple:C.ink});tx(s,label,x-12,538,bw+24,30,21,{align:'center'});if(i<5){const end=i===0?1200:i===1?1700:i===2?1730:i===3?1450:1430;rule(s,x+bw,py(end),xs[i+1]-xs[i]-bw,C.gold,1.4);}});
  tx(s,'1,200 + 500 + 30 − 280 − 20 = 1,430 人',48,589,1184,36,25,{bold:true,color:C.blue});
  tx(s,'年度净增230人；离校合计300人（毕业280、退学20）。上述流量用于在籍勾稽，与招生目标未完成50人的含义不同。',48,635,1184,31,19);
}
// 6: Finance table for cross lookup; actual expenditure bars explain scale.
{
  const s=page('收支偏差','实际收支差780万元，较预算少420万元；收入少500万元，支出少80万元，合计形成净差。','finance-table-and-composition','查预算偏差与支出构成','原生预算/实际表及共用比例的科目条形','单位万元；实际/预算同口径；收入不等同到账');
  deck.nativeTable(s,[['项目','预算','实际','实际−预算'],['收入','9,600','9,100','−500'],['支出','8,400','8,320','−80'],['收支差','1,200','780','−420']],{x:48,y:210,w:650,h:265,columnWidths:[180,145,145,180],rowHeights:[55,70,70,70],size:20,numericColumns:[1,2,3],focusRow:3});
  tx(s,'实际支出构成（万元）',748,208,484,31,23,{bold:true,color:C.purple});
  const rows=[['教学',4800],['校园',1600],['学生服务',920],['行政',1000]];
  rows.forEach(([label,value],i)=>{const y=263+i*61;tx(s,label,748,y,105,29,20);rect(s,861,y+6,value/4800*250,16,i===0?C.blue:'#A6A8AD');tx(s,value.toLocaleString('en-US'),1125,y-1,107,30,20,{align:'right'});});
  tx(s,'支出分项合计：8,320万元',748,515,484,32,20,{bold:true});
  rule(s,48,570,1184);
  tx(s,'净差核对：−500 −（−80）= −420万元。支出低于预算仅部分抵消收入缺口，不能将其直接解释为效率改善。',48,588,1184,58,21);
  tx(s,'本例仅采用收支口径，未给出到账与承诺支出资料；不据此判断现金收付或持续性成本。',48,648,1184,28,18,{color:C.secondary});
}
// 7: A concrete written response is the primary object, with a nearby diagnosis.
{
  const s=page('教学证据','模拟同标测评达到标准者从120人增至150人；匿名作答揭示“变化量与系数”仍需具体支持。','response-evidence-annotation','观察具体错误，区分表现变化与归因','匿名作答原文、修订及同标测评比例','同一批200人/同一能力框架；不能证明措施因果；作答为虚构');
  tx(s,'同标测评｜同一批200人',48,205,400,32,23,{bold:true,color:C.purple});
  [['前测',120,60],['后测',150,75]].forEach(([label,n,p],i)=>{const y=278+i*92;tx(s,label,48,y,82,30,22);rect(s,142,y+6,300,22,C.pale);rect(s,142,y+6,p/100*300,22,i?C.blue:C.secondary);tx(s,`${n}人 / ${p}%`,48,y+41,394,30,22,{bold:true,align:'right'});});
  tx(s,'提升15个百分点',48,493,394,36,26,{bold:true,color:C.red});
  tx(s,'比较反映达标比例变化。\n现有证据不能将变化归因于\n培训、结对或某项具体措施。',48,549,394,92,21);
  tx(s,'匿名作答（模拟）',500,205,732,32,23,{bold:true,color:C.purple});
  rect(s,500,250,732,105,C.pale);
  tx(s,'“已知y=2x+1，x增加3，y也增加3”',520,271,691,67,25);
  rule(s,858,324,191,C.red,2);
  deck.evidenceNote(s,'把两个变量的变化量直接等同，忽略系数2。',{x:500,y:384,w:732,h:82,title:'错误定位',anchor:{x:956,y:327},size:21});
  tx(s,'修订：Δy = 2Δx = 6',500,490,732,42,29,{bold:true,color:C.blue});
  tx(s,'变化量由系数2决定。\n支持重点：解释“乘2”的依据，\n并用新的变化量独立验证。',500,551,732,90,22);
}
// 8: Native relation network; lines identify real proposed deliverables.
{
  const s=page('支持协作','拟由学科组、导师、学生服务与教务承接任务、反馈和资源；过程参与仍需与学习证据分别核对。','labeled-support-network','追踪主体之间的交付接口','有名称与交付内容的协作网络','全部拟议；教师培训只有参与记录，不能认定效果');
  const node=(title,body,x,y,w=300)=>{tx(s,title,x,y,w,34,25,{bold:true,color:C.purple});tx(s,body,x,y+43,w,70,21);};
  node('学科组','提供任务与评价标准',48,223,310);
  node('导师','汇集个体反馈',455,223,310);
  node('学生服务组','向家长提供支持安排',880,223,352);
  deck.arrow(s,{x:359,y:279,w:65,color:C.gold});
  tx(s,'任务/标准',339,332,112,26,17,{align:'center',color:C.secondary});
  deck.arrow(s,{x:766,y:279,w:82,color:C.gold});
  tx(s,'个体反馈',750,332,124,26,17,{align:'center',color:C.secondary});
  rule(s,48,391,1184);
  node('教务','统筹课时与资源，复核评价',455,431,480);
  seg(s,605,420,605,378,C.purple,1.7);seg(s,200,378,1055,378,C.purple,1.7);
  [200,605,1055].forEach(x=>seg(s,x,378,x,359,C.purple,1.7));
  tx(s,'资源与评价统筹',48,423,325,32,21,{color:C.purple});
  tx(s,'教师模拟情况：180名教师；26名新教师与导师结对；全年42次培训。',48,580,1184,35,23,{bold:true});
  tx(s,'现有记录只证明参与。下一步应检查课堂任务、评价标准与学生作答的变化，再判断支持机制是否需要调整。',48,626,1184,42,21);
}
// 9: Native option table with unequal field widths and explicit opportunity cost.
{
  const s=page('资源取舍','建议先落实共同备课时段，再按诊断决定导师培训范围；直接新增预算为0仍需要课时统筹。','resource-options-with-tradeoff','同字段比较投入、对象与实施条件','A/B原生比较表与优先次序说明','两方案均为模拟选项；没有虚构审批结果');
  deck.nativeTable(s,[['比较维度','方案A：导师专项培训','方案B：共同备课时段'],['资源投入','追加12万元','直接新增预算0'],['适用对象','26名新教师','各学科组'],['资源代价与条件','需据诊断明确培训范围','每组每周占用1小时；需课时统筹'],['证据要求','检查课堂任务与学生作答变化','保留任务、评价标准与匿名作答']],{x:48,y:204,w:1184,h:330,columnWidths:[202,430,552],rowHeights:[58,58,58,78,78],size:20});
  tx(s,'建议顺序',48,570,180,34,24,{bold:true,color:C.purple});
  tx(s,'先落实共同备课 → 依据诊断确定培训范围 → 结合阶段复测复盘资源安排',235,570,997,36,23,{bold:true});
  tx(s,'方案B减少直接新增费用，但占用现有教学组织时间。\n方案A投入12万元、覆盖26名新教师；是否实施及范围仍须诊断支持，本报告不预设审批。',48,620,1184,51,20);
}
// 10: Date-proportional timeline, with staggered labels and actual named owners.
{
  const s=page('推进节点','拟在2027年上半年依次完成需求复核、共同备课、阶段复测和资源复盘；日期与责任均为模拟拟议。','date-proportional-milestones','按真实时间间距追踪计划','日期轴与近邻责任/交付说明','全部拟议，非学校已定承诺；原始精确日期保留');
  deck.milestoneTimeline(s,[
    {date:'2027-01-15',label:'复核需求',detail:'教务\n分学段需求与缺口',width:240,labelX:48,labelY:215},
    {date:'2027-03-01',label:'共同备课',detail:'学科组\n任务、评价与匿名作答',width:250,labelX:340,labelY:456},
    {date:'2027-04-20',label:'阶段复测',detail:'教务与学科组\n同口径结果与限制',width:264,labelX:640,labelY:215},
    {date:'2027-06-15',label:'资源复盘',detail:'校务工作组\n继续/调整建议及依据',width:264,labelX:968,labelY:456},
  ],{x:48,y:215,w:1184,h:360,start:'2027-01-01',end:'2027-06-30',size:23});
  tx(s,'衔接条件：共同备课须统筹每组每周1小时；阶段复测沿用同一能力框架与可比口径；资源复盘依据阶段材料形成建议。',48,612,1184,58,21);
}
// 11: Lookup table remains a table because complete responsibility fields matter.
{
  const s=page('责任查阅','以可查阅的交付物持续核对计划执行；复盘结论须同时保留规模差额、教学边界与资源条件。','complete-responsibility-register','查阅责任、日期和完成物','四项原生责任台账与前文结论承接','拟议责任与时间，不代表已实施；结论不超出模拟材料');
  deck.nativeTable(s,[['交付物','责任','节点（2027）','核对内容'],['需求清单','教务','1月15日','分学段需求与缺口'],['备课记录','学科组','3月起','任务、评价、匿名作答'],['阶段复测','教务/学科组','4月20日','同口径结果与限制'],['资源复盘','校务工作组','6月15日','继续/调整建议及依据']],{x:48,y:205,w:1184,h:315,columnWidths:[202,222,220,540],rowHeights:[55,65,65,65,65],size:21});
  tx(s,'管理结论',48,555,175,34,24,{bold:true,color:C.purple});
  tx(s,'规模增长，招生目标仍差50人。\n教学模拟达标比例上升，成效归因尚无证据。\n下一年按需求、共同备课、复测与资源复盘持续核对。',235,554,997,84,22);
  tx(s,'以上数字、案例、机制、责任及日期全部为虚构演示，不作为华朗学校实绩或已定承诺。',48,645,1184,29,19,{color:C.red});
}

const candidatePath=path.join(outputDir,'华朗管理汇报_版式验证_V8.1.pptx');
await (await PresentationFile.exportPptx(deck.presentation)).save(candidatePath);
await fs.writeFile(path.join(outputDir,'report-layout-sequence.json'),JSON.stringify({simulated:true,slides:seq},null,2)+'\n');
// Always inspect the exported artifact, including inherited template layers.
const saved=await PresentationFile.importPptx(await FileBlob.load(candidatePath));
const renderDir=path.join(outputDir,'render-final');
await fs.mkdir(renderDir,{recursive:true});
for (let i=0;i<saved.slides.items.length;i++){
  const slide=saved.slides.items[i],stem=`slide-${String(i+1).padStart(2,'0')}`;
  const png=await saved.export({slide,format:'png',scale:1.2});
  await fs.writeFile(path.join(renderDir,stem+'.png'),new Uint8Array(await png.arrayBuffer()));
  await fs.writeFile(path.join(renderDir,stem+'.layout.json'),await(await slide.export({format:'layout'})).text());
}
console.log(JSON.stringify({pptx:candidatePath,slideCount:saved.slides.items.length,renderDir}));
