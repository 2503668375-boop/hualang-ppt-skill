import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';

// Public demonstration: all quantities, cases and arrangements are simulated.
// Usage: node build_depth_demo.mjs --skillDir <skill> --outputDir <outputs>
const args = Object.fromEntries(process.argv.slice(2).reduce((a,v,i,all)=>{
  if(v.startsWith('--')) a.push([v.slice(2),all[i+1]]); return a;
},[]));
if(!args.skillDir || !args.outputDir) throw new Error('Provide --skillDir and --outputDir.');
const skillDir=path.resolve(args.skillDir), outputDir=path.resolve(args.outputDir);
const buildDir=path.resolve(outputDir,'..','build','forward');
const require=createRequire(import.meta.url);
const artifactEntry=require.resolve('@oai/artifact-tool');
const modulesDir=path.resolve(path.dirname(artifactEntry),'../../..');
await fs.mkdir(buildDir,{recursive:true}); await fs.mkdir(outputDir,{recursive:true});
try {await fs.symlink(modulesDir,path.join(buildDir,'node_modules'),'dir');} catch(e){if(e.code!=='EEXIST')throw e;}
const kitPath=path.join(buildDir,'hualang-kit.mjs');
await fs.copyFile(path.join(skillDir,'scripts/hualang-kit.mjs'),kitPath);
const {createDeck,colors:C}=await import(pathToFileURL(kitPath).href);
const {FileBlob,PresentationFile}=await import(pathToFileURL(artifactEntry).href);
const title='年度总结与下一年计划（模拟演示）', presenter='示例工作组', date='2026年11月7日';
const deck=await createDeck({skillDir,title,presenter,date,closingText:'示例汇报完毕，敬请审阅'});
const manifest={title,presenter,date,nature:'所有数字、案例和安排均为虚构演示，不代表华朗学校实绩。',slides:[]};
const section='年度总结与下一年计划｜虚构演示，不代表华朗学校实绩';
let current;
function page(title,summary,meta){
  const s=deck.addPage({title,summary,section,purpose:'report'});
  current={slide:deck.presentation.slides.items.indexOf(s)+1,title,summary,...meta,content:[]};
  manifest.slides.push(current); return s;
}
function tx(s,text,x,y,w,h,size=21,extra={}){
  current?.content.push(text); return deck.text(s,text,{x,y,w,h,size,...extra});
}
function label(s,t,x,y,w=400){return tx(s,t,x,y,w,30,22,{bold:true,color:C.purple});}
function ln(s,x,y,w,h=0,color=C.line,width=1){return deck.line(s,{x,y,w,h,color,width});}
function rect(s,x,y,w,h,fill=C.pale,stroke='none'){
  return s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:stroke==='none'?0:1}});
}
function table(s,values,x,y,w,h,widths,heights,opts={}){
  current?.content.push(...values.map(r=>r.join('｜')));
  return deck.nativeTable(s,values,{x,y,w,h,columnWidths:widths,rowHeights:heights,size:19,...opts});
}
function nativeBar(s,items,{x,y,w,h,max,ticks,unit='人',color=C.blue,numberSuffix=''}){
  const labelW=126,plotX=x+labelW,plotW=w-labelW-104,rowH=(h-48)/items.length;
  for(const v of ticks){const px=plotX+v/max*plotW;ln(s,px,y,0,h-30,C.line,.65);tx(s,String(v),px-25,y+h-23,50,22,16,{align:'center',color:C.secondary});}
  items.forEach((it,i)=>{const yy=y+i*rowH+12;tx(s,it.label,x,yy+3,labelW-10,30,21,{bold:true});
    rect(s,plotX,yy,it.value/max*plotW,28,it.color??color);
    tx(s,String(it.value)+numberSuffix,plotX+it.value/max*plotW+12,yy+2,92,28,20,{bold:true});
  });
  tx(s,'单位：'+unit,plotX,y-31,180,25,17,{color:C.secondary});
}
function callout(s,k,body,x,y,w,h=105){label(s,k,x,y,w);tx(s,body,x,y+38,w,h-38,20);}
function bridge(s,values,{x,y,w,h,max,unit,barW=112}){
  const base=y+h-42,top=y+20,plotH=base-top,step=w/values.length;
  for(const tick of [0,max/2,max]){const py=base-tick/max*plotH;ln(s,x,py,w,0,C.line,.7);tx(s,String(tick),x-45,py-11,38,22,16,{align:'right',color:C.secondary});}
  let running=0;
  values.forEach((v,i)=>{const start=v.total?0:running,end=v.total?v.value:running+v.value;
    const xx=x+i*step+(step-barW)/2,yy=base-Math.max(start,end)/max*plotH;
    const hh=Math.max(Math.abs(end-start)/max*plotH,2);
    rect(s,xx,yy,barW,hh,v.total?C.purple:v.value<0?C.red:C.blue);
    if(i<values.length-1){const py=base-end/max*plotH;ln(s,xx+barW,py,step-barW,0,C.secondary,1);}
    tx(s,(v.total?'':v.value>0?'+':'')+v.value,xx-20,yy-31,barW+40,28,22,{align:'center',bold:true,color:v.value<0?C.red:C.ink});
    tx(s,v.label,xx-20,base+12,barW+40,47,18,{align:'center'});running=end;
  });tx(s,'单位：'+unit,x,y-23,160,25,17,{color:C.secondary});
}

// 2. Annual scale and segment structure belong to the same comparison unit.
{
 const s=page('招生结构','年度新增500人，较上年增加80人；完成目标90.9%，仍差50人。增长与目标差距需要同时保留。',{
   task:'比较整体增长、分学段完成与差额构成',mainObject:'三个学段的共同数轴；完成率和缺口贡献直接邻接对应行',family:'共同数轴比较',
   conditions:['同一招生年度，单位为人','目标/实际/上年区分；分学段未给上年值','原因资料未给出，不作归因'],
   derivations:['500/550=90.9%','(500-420)/420=19.0%','初中/高中/国际高中完成率91.7%/93.8%/84.6%','三学段缺口15/15/20人，贡献30%/30%/40%'],
   reason:'整体增长与差额来源需同屏；季度变动在下一页展开。'});
 tx(s,'上年420人 → 本年500人（+19.0%）；年度目标550人。',48,198,1184,36,22,{bold:true,color:C.purple});
 deck.dotComparison(s,[{label:'初中',before:180,after:165},{label:'高中',before:240,after:225},{label:'国际高中',before:130,after:110}],{x:48,y:250,w:830,h:335,min:0,max:260,labelWidth:150,unit:'人'});
 tx(s,'完成率',926,250,126,30,20,{bold:true,color:C.purple});
 tx(s,'缺口贡献',1080,250,152,30,20,{bold:true,color:C.purple});
 [['91.7%','30.0%'],['93.8%','30.0%'],['84.6%','40.0%']].forEach((v,i)=>{
   const yy=250+46+(335-75)/3*(i+.5)-13;
   tx(s,v[0],926,yy,126,30,22,{bold:true});tx(s,v[1],1080,yy,152,30,22,{bold:true});
 });
 ln(s,48,605,1184,0,C.gold,1.2);
 tx(s,'国际高中同时呈现最低完成率和最大缺口贡献；高中实际新增最多，但仍未达到学段目标。\n完成率以各学段目标为分母，缺口贡献以总缺口50人为分母；现有分解尚不能解释招生原因。',48,622,1184,48,20);
}

// 3. Actual quarterly movement, completion and cumulative gap are distinct.
{
 const s=page('季度节奏','季度新增逐季增加，下半年贡献63.0%；四个季度均未达目标，累计缺口从20人扩大至50人。',{
  task:'追踪当季变化并核对累计差额',mainObject:'季度目标/实际共同坐标折线＋同列累计查数',family:'趋势与累计',
  conditions:['季度新增可加总；累计值不能再次相加','目标与实际同期间同单位','未提供渠道或转化记录，不解释季度原因'],
  derivations:['H1实际185，H2实际315；H2占比63.0%','当季差额-20/-15/-5/-10；累计差额-20/-35/-40/-50','完成率80.0%/87.5%/96.7%/94.4%'],reason:'趋势与累计缺口共同回答节奏问题，避免把四点图单独放大。'});
 deck.chart(s,'line',{position:{left:40,top:188,width:786,height:295},categories:['Q1','Q2','Q3','Q4'],
   series:[{name:'季度目标',values:[100,120,150,180],fill:C.secondary,line:{fill:C.secondary,width:2.1},marker:{symbol:'circle',size:6,fill:C.secondary},dataLabels:{showValue:true,position:'top',textStyle:{fontSize:18,fill:C.secondary}}},{name:'季度实际',values:[80,105,145,170],fill:C.blue,line:{fill:C.blue,width:3},marker:{symbol:'circle',size:7,fill:C.blue},dataLabels:{showValue:true,position:'bottom',textStyle:{fontSize:18,fill:C.blue}}}],
   hasLegend:true,legend:{position:'bottom',overlay:false,textStyle:{fontSize:18}},yAxis:{min:0,max:200,majorUnit:50},xAxis:{majorGridlines:null},dataLabels:{showValue:false}});
 callout(s,'后半年贡献', 'Q3与Q4合计315人，\n占全年63.0%，较上半年185人\n增加130人。规模向后半年集中，\n仍需逐季对照目标。',866,196,366,158);
 callout(s,'差距的含义','Q3当季差5人，为最小缺口；\nQ4新增170人，仍差10人。\n季度新增与完成率须分别读取。',866,375,366,132);
 table(s,[['季度','目标／实际','当季差额','完成率','累计目标／实际','累计差额'],['Q1','100／80','-20','80.0%','100／80','-20'],['Q2','120／105','-15','87.5%','220／185','-35'],['Q3','150／145','-5','96.7%','370／330','-40'],['Q4','180／170','-10','94.4%','550／500','-50']],48,508,1184,144,[110,206,170,160,328,210],[29,28,28,28,31],{numericColumns:[1,2,3,4,5],size:17});
}

// 4. A scale bridge explicitly separates admissions from leaving school.
{
 const s=page('在籍勾稽','期末在籍1430人，较期初净增230人、增长19.2%。新增、转入与离校共同形成规模变化。',{
  task:'沿期初至期末逐项勾稽',mainObject:'可编辑在籍贡献桥与入口/离校定义',family:'规模贡献桥',
  conditions:['单位为人；期初/期末为时点，流入流出为期间量','招生差额是目标对比，毕业与退学属于离校'],
  derivations:['1200+500+30-280-20=1430','流入530，离校300，净增230','230/1200=19.2%'],reason:'规模变化有加减关系，适宜在同一贡献桥内完整解释。'});
 bridge(s,[{label:'期初在籍',value:1200,total:true},{label:'本年新增',value:500},{label:'转入',value:30},{label:'毕业',value:-280},{label:'退学',value:-20},{label:'期末在籍',value:1430,total:true}],{x:94,y:220,w:1100,h:236,max:1800,unit:'人',barW:100});
 ln(s,48,480,1184,0,C.gold,1.2);
 callout(s,'净增关系','流入530人（新增500＋转入30）\n离校300人（毕业280＋退学20）\n两者相抵，期末较期初增加230人。',48,498,558,112);
 callout(s,'两类差额','招生目标差50人，用于判断招生完成；\n毕业280人与退学20人，用于解释在籍流出。\n二者比较基准不同，不能相互替代。',674,498,558,112);
 tx(s,'管理用途（建议）：2027年1月15日复核分学段需求时，分别核对招生目标缺口与在籍增减的影响。\n现有材料没有分学段在籍拆分，不能据总量直接分配课时或资源。',48,619,1184,48,20);
}

// 5. Budget variance and its effects on surplus, in one reading unit.
{
 const s=page('收支与配置','实际收支差780万元，较预算少420万元、完成65.0%；收入少于预算500万元，支出少80万元。\n四项支出合计8320万元；本例仅为收支口径，收入与到账分开。',{
  task:'查预算与实际、解释收支差偏差，并读取四项支出配置',mainObject:'收入支出三列查数表、支出结构条形与收支差贡献桥',family:'财务综合分析',
  conditions:['单位万元；预算/实际同口径','本例仅为收入与支出口径，不代表到账或现金余额','不推断收入与招生之间的因果','未给科目预算与成本—结果对应资料'],
  derivations:['9600-8400=1200','9100-8320=780','780-1200=-420','-500+80=-420','780/1200=65.0%','预算收支差率12.5%，实际8.6%','4800+1600+920+1000=8320','占比57.7%/19.2%/11.1%/12.0%','(4800+1600+920)/8320=88.0%'],reason:'预算比较、偏差形成与支出配置能在可读字号下同屏，不保留重复财务短页。'});
 label(s,'预算与实际（万元）',48,197,620);
 table(s,[['项目','预算','实际'],['收入','9,600','9,100'],['支出','8,400','8,320']],48,236,620,132,[210,205,205],[44,44,44],{numericColumns:[1,2],size:20});
 tx(s,'收入完成94.8%，支出执行99.0%。',48,385,620,30,20);
 label(s,'实际支出结构（万元）',730,197,502);
 const plotX=834,plotW=230;
 [0,2500,5000].forEach(v=>{const xx=plotX+v/5000*plotW;ln(s,xx,236,0,153,C.line,.65);tx(s,String(v),xx-28,398,56,23,16,{align:'center',color:C.secondary});});
 [['教学',4800,'57.7%'],['校园',1600,'19.2%'],['学生服务',920,'11.1%'],['行政',1000,'12.0%']].forEach((v,i)=>{
   const yy=241+i*40;tx(s,v[0],730,yy,98,29,20,{bold:true});rect(s,plotX,yy,v[1]/5000*plotW,25,C.blue);tx(s,`${v[1]}｜${v[2]}`,1075,yy,157,29,18,{bold:true});
 });
 ln(s,48,434,1184,0,C.gold,1.2);
 bridge(s,[{label:'预算收支差',value:1200,total:true},{label:'收入少于预算',value:-500},{label:'支出少于预算',value:80},{label:'实际收支差',value:780,total:true}],{x:94,y:473,w:600,h:164,max:1400,unit:'万元',barW:86});
 callout(s,'偏差与资源读取','支出少80万元仅抵消收入缺口的16.0%。\n预算收支差率12.5%，实际8.6%，\n下降约3.9个百分点（各以收入为分母）。\n教学、校园与学生服务合计占88.0%。\n科目预算与结果对应资料尚缺，\n单项偏差及使用成效仍需另行核对。',754,456,478,204);
}

// 7. The actual anonymous work is kept with aggregate evidence and limits.
{
 const s=page('测评与作答','同一批200名学生、同一能力框架下，达到标准者由120人增至150人，占比从60.0%升至75.0%，提升15个百分点。',{
  task:'读取总体变化并定位具体错误、修订和支持重点',mainObject:'同标准人数对照＋匿名原文的完整诊断',family:'分布与作品批注',
  conditions:['同一批200名学生；同一能力框架','模拟匿名作答，非华朗真实学生作品','总体净增30不等于已识别30名个体改善','无措施因果证据'],
  derivations:['120/200=60%，150/200=75%','未达标80→50；达标人数净增30','Δy=2Δx=2×3=6'],reason:'总体变化与具体学习对象共读，避免只有比例，或把单例推广为总体分布。'});
 const bx=48, bw=620;
 label(s,'达到标准与未达标准',48,199,620);
 [[120,80,'前次',60],[150,50,'后次',75]].forEach(([yes,no,t,p],i)=>{
  const yy=248+i*73;tx(s,t,48,yy+4,70,30,21,{bold:true});
  rect(s,126,yy,bw*yes/200,36,C.blue);rect(s,126+bw*yes/200,yy,bw*no/200,36,'#D5D8DD');
  tx(s,`${yes}人／${p}%`,136,yy+6,bw*yes/200-15,26,18,{color:C.white,bold:true});
  tx(s,`${no}人`,136+bw*yes/200,yy+6,bw*no/200-15,26,18);
 });
 tx(s,'深蓝：达到标准　灰色：未达标准｜总样本均为200人',48,398,720,28,18,{color:C.secondary});
 callout(s,'总体解释边界','达标人数净增加30人，未达标减少30人。\n现有汇总数不能辨认个体转变路径，\n也不能证明任何支持措施导致变化。',826,202,406,160);
 callout(s,'支持重点（建议）','核对学生能否解释系数2的作用，\n再用课堂任务和匿名作答检查理解。\n单个例子不代表全体错误比例。',826,380,406,135);
 ln(s,48,455,725,0,C.gold,1.2);
 label(s,'匿名作答原文与修订（模拟）',48,478,725);
 tx(s,'原文：“已知y=2x+1，x增加3，y也增加3”',48,523,724,34,22);
 tx(s,'修订：“Δy=2Δx=6，变化量由系数2决定”',48,570,724,34,22,{bold:true,color:C.blue});
 tx(s,'错误定位：把x的增量直接作为y的增量；计算时遗漏系数2。常数项1在前后相减时抵消。',48,616,1184,42,19);
}

// 8. Process evidence is separated from effectiveness; coordination is proposed.
{
 const s=page('教师与协作','180名教师中，26名新教师与导师结对，占教师总数14.4%；全年培训42次。\n现有记录只证明参与，下一步应核对课堂任务与学生作答的变化。',{
  task:'区分参与证据与效果证据，并追踪拟议岗位接口',mainObject:'教师记录证据条与四主体协作网络',family:'证据与责任接口',
  conditions:['180名教师、26名新教师结对、42次培训均为模拟','没有人均培训次数或总参与人次','协作机制全为拟议，不代表已经实施'],
  derivations:['26/180=14.4%'],reason:'教师数量没有独立效果解释，与证据检查和拟议接口合并成完整阅读单元。'});
 label(s,'参与记录与效果证据',48,198,430);
 tx(s,'模拟记录包括26名结对新教师，\n全年开展42次培训活动。\n现有记录未给每名教师参与次数。',48,241,422,94,21);
 tx(s,'参与记录可核对覆盖和活动发生。\n教学是否改善，还需比较课堂任务、\n评价标准与学生作答。',48,354,422,84,21);
 ln(s,505,202,0,430,C.gold,1.4);
 label(s,'校内支持协作（模拟拟议）',550,198,682);
 const a=rect(s,560,261,250,88,C.pale),b=rect(s,957,261,250,88,C.pale),c=rect(s,957,476,250,88,C.pale),d=rect(s,560,476,250,88,C.pale);
 tx(s,'学科组',584,276,202,30,24,{bold:true,color:C.purple});tx(s,'任务与评价标准',584,313,202,28,19);
 tx(s,'导师',981,276,202,30,24,{bold:true,color:C.purple});tx(s,'汇集个体反馈',981,313,202,28,19);
 tx(s,'学生服务组',981,491,202,30,24,{bold:true,color:C.purple});tx(s,'向家长提供支持安排',981,528,202,28,18);
 tx(s,'教务',584,491,202,30,24,{bold:true,color:C.purple});tx(s,'统筹课时与资源\n复核评价',584,523,202,40,17);
 deck.arrow(s,{from:a,to:b,color:C.gold,width:2});
 tx(s,'提供任务\n与标准',830,279,110,63,17,{align:'center'});
 deck.arrow(s,{from:b,to:c,fromSide:'bottom',toSide:'top',color:C.gold,width:2});
 tx(s,'交接个体反馈',1084,389,148,27,17);
 deck.arrow(s,{from:d,to:a,fromSide:'top',toSide:'bottom',color:C.gold,width:2});
 tx(s,'课时／资源\n评价复核',560,382,160,60,17);
 tx(s,'家长',1004,603,160,30,22,{bold:true,color:C.purple});deck.arrow(s,{from:c,to:deck.text(s,'',{x:1030,y:599,w:80,h:1}),fromSide:'bottom',toSide:'top',color:C.gold,width:2});
 tx(s,'拟议接口交付任务、标准、个体反馈\n和支持安排；后续需核对机制是否运行，\n以及学生表现是否变化。',48,566,422,94,20);
}

// 9. Same dimensions support resource choice; no invented group count or budget.
{
 const s=page('资源取舍','建议先落实共同备课时段，再据诊断决定专项培训范围。直接新增预算为0仍有时间代价，不能仅以费用判断方案价值。',{
  task:'按共同维度比较方案，并理解推荐的条件与代价',mainObject:'方案原生对照表＋有依赖的建议顺序',family:'选项比较与建议',
  conditions:['均为下一年度可比较资源安排，不代表已经批准','A覆盖26名新教师；B每组每周1小时','未给组数和周数，不估全年总工时','不承诺培训或备课造成成绩提升'],
  derivations:['120000/26≈4615元/名，仅为预算平均分摊'],reason:'费用、覆盖、时间与证据需同字段核对；推荐顺序贴近比较。'});
 table(s,[['比较维度','方案A｜导师专项培训','方案B｜共同备课时段'],['直接新增预算','12万元','0万元'],['覆盖／投入','覆盖26名新教师','每组每周1小时'],['可复算关系','预算均摊约4615元／名','全年总工时暂不能计算'],['资源条件','据诊断决定培训范围（建议）','需教务统筹课时与资源'],['检查证据（建议）','培训支持是否对应具体任务与错误','备课任务、评价与匿名作答的变化']],48,200,1184,279,[230,455,499],[43,42,42,46,46,60],{size:19,labelColumns:[0]});
 label(s,'建议推进顺序',48,507,250);
 const steps=[['1','落实共同备课','先统筹每组每周1小时，\n形成任务、评价与匿名作答记录。'],['2','依据诊断定培训','从任务和作答定位支持需要，\n再据诊断明确培训范围。'],['3','阶段复测再复盘','同标准复测核对变化，\n6月提出继续／调整建议及依据。']];
 steps.forEach((v,i)=>{const xx=48+i*410;deck.numberBadge(s,v[0],{x:xx,y:553,size:36});tx(s,v[1],xx+50,554,332,29,22,{bold:true,color:C.purple});tx(s,v[2],xx,598,370,62,20);if(i<2)ln(s,xx+380,571,24,0,C.gold,2);});
}

// 10. Dates use real spacing; the full responsibility lookup stays on this page.
{
 const s=page('节点责任','招生规模增长但仍差目标50人；达标比例提高15个百分点，尚无措施因果证据。\n下一年按需求、共同备课、同标准复测与资源复盘持续核对；以下均为模拟拟议安排。',{
  task:'按真实日期追踪任务，并查找责任和完成物',mainObject:'真实日期时间轴与四项完整责任原生表',family:'日期与责任台账',
  conditions:['2027年计划全部为模拟拟议，非学校已定承诺','3月1日启动与3月起持续记录分别保留','原材料没有新增审批和处置承诺'],
  derivations:[],reason:'日期与责任原为同一落实单元，合并后可在同页交叉查阅。'});
 deck.milestoneTimeline(s,[{date:'2027-01-15',label:'复核需求',detail:'教务',width:210,labelX:48,labelY:197},{date:'2027-03-01',label:'启动共同备课',detail:'学科组',width:240,labelX:337,labelY:315},{date:'2027-04-20',label:'同标准阶段复测',detail:'教务与学科组',width:260,labelX:680,labelY:197},{date:'2027-06-15',label:'复盘资源安排',detail:'校务工作组',width:220,labelX:1012,labelY:315}],{x:48,y:195,w:1184,h:191,start:'2027-01-01',end:'2027-06-30'});
 table(s,[['交付物','责任主体','时间','完整核对内容'],['需求清单','教务','1月15日','分学段需求与缺口'],['备课记录','学科组','3月起','任务、评价、匿名作答'],['阶段复测','教务／学科组','4月20日','同口径结果与限制'],['资源复盘','校务工作组','6月15日','继续／调整建议及依据']],48,427,1184,225,[210,245,180,549],[41,46,46,46,46],{size:20,labelColumns:[0]});
}

const pptx=path.join(outputDir,'华朗管理汇报_内容深化_V8.2.pptx');
await (await PresentationFile.exportPptx(deck.presentation)).save(pptx);
await fs.writeFile(path.join(buildDir,'逐页内容与构图清单.json'),JSON.stringify(manifest,null,2));
// Final previews come exclusively from the saved PPTX, never from memory state.
const imported=await PresentationFile.importPptx(await FileBlob.load(pptx));
const renderDir=path.join(buildDir,`final-render-${imported.slides.items.length}p`);await fs.mkdir(renderDir,{recursive:true});
for(let i=0;i<imported.slides.items.length;i++){
 const s=imported.slides.items[i],stem=`slide-${String(i+1).padStart(2,'0')}`;
 const png=await imported.export({slide:s,format:'png',scale:1.5});
 await fs.writeFile(path.join(renderDir,stem+'.png'),new Uint8Array(await png.arrayBuffer()));
 await fs.writeFile(path.join(renderDir,stem+'.layout.json'),await(await s.export({format:'layout'})).text());
}
console.log(JSON.stringify({pptx,slideCount:imported.slides.items.length,renderDir,manifest:path.join(buildDir,'逐页内容与构图清单.json')}));
