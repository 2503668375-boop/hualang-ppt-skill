// Original public demonstration materials; no machine paths or school records.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [skillArg,outArg]=process.argv.slice(2);
if(!skillArg||!outArg)throw Error('Usage: node build_v10_samples.mjs SKILL_DIR OUTPUT_DIR');
const S=path.resolve(skillArg),B=path.resolve(outArg);
await fs.mkdir(B,{recursive:true});
const kit=path.join(B,'hualang-kit.mjs');await fs.copyFile(path.join(S,'scripts/hualang-kit.mjs'),kit);
if(process.env.HUALANG_NODE_MODULES){try{await fs.symlink(process.env.HUALANG_NODE_MODULES,path.join(B,'node_modules'),'dir');}catch(e){if(e.code!=='EEXIST')throw e;}}
const {createDeck,colors:C}=await import(pathToFileURL(kit));
const d=await createDeck({skillDir:S,title:'华朗学校分场景应用样页',presenter:'示例工作组',date:'2026年11月8日',zhFont:process.env.HUALANG_ZH_FONT??'Noto Sans SC',sceneMode:'mixed',closingText:'样页演示完毕，敬请审阅'});
const T=(s,v,x,y,w,h,size=23,o={})=>d.text(s,v,{x,y,w,h,size,...o});
const H=(s,v,x,y,w,size=25)=>T(s,v,x,y,w,40,size,{bold:true,color:C.purple});
const R=(s,x,y,w,h,fill=C.pale,stroke='none',width=0)=>s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width}});
const L=(s,x1,y1,x2,y2,color=C.line,width=1.2)=>{const x=Math.min(x1,x2),y=Math.min(y1,y2),w=Math.max(1,Math.abs(x2-x1)),h=Math.max(1,Math.abs(y2-y1));return s.shapes.add({geometry:'custom',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width},customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-x,y:y1-y}},{lineTo:{x:x2-x,y:y2-y}}]}]});};
const DOT=(s,x,y,r=4,color=C.blue)=>s.shapes.add({geometry:'ellipse',position:{left:x-r,top:y-r,width:2*r,height:2*r},fill:color,line:{fill:'none',width:0}});
const context=(s,v,y=156)=>d.contextLine(s,v,{x:48,y,w:1184,h:28});
const seq=[];
function P(title,purpose,task,object,family,lead=''){const s=d.addPage({title,purpose,lead});seq.push({slide:d.presentation.slides.items.indexOf(s)+1,title,purpose,task,mainObject:object,family});return s;}
function RT(s,rows,x,y,w,h,size=23){const q=T(s,'',x,y,w,h,size);q.text.set(rows.map(r=>({runs:r.map(v=>typeof v==='string'?{run:v,style:{typeface:process.env.HUALANG_ZH_FONT??'Noto Sans SC'}}:{run:v.t,style:{typeface:process.env.HUALANG_ZH_FONT??'Noto Sans SC',bold:true,color:v.c??C.purple,fontSize:`${v.size??size}px`}})})));return q;}
function graph(s,{x,y,w,h,xmin=-1.3,xmax=4.3,ymin=-4,ymax=7,interval=[-1,4],labels=true,curve=C.blue}){
 const ml=40,mr=14,mt=12,mb=30,pw=w-ml-mr,ph=h-mt-mb;
 const X=a=>x+ml+(a-xmin)/(xmax-xmin)*pw,Y=a=>y+mt+(ymax-a)/(ymax-ymin)*ph;
 R(s,X(interval[0]),y+mt,X(interval[1])-X(interval[0]),ph,C.pale);
 for(let a=Math.ceil(xmin);a<=xmax;a++){L(s,X(a),y+mt,X(a),y+mt+ph,'#E4E1E8',0.8);if(labels)T(s,String(a).replace('-','−'),X(a)-15,Y(0)+8,30,24,17,{align:'center'});}
 for(let a=Math.ceil(ymin);a<=ymax;a+=2){L(s,x+ml,Y(a),x+ml+pw,Y(a),'#E4E1E8',0.8);if(labels&&a!==0)T(s,String(a).replace('-','−'),x,Y(a)-12,31,24,17,{align:'right'});}
 L(s,x+ml,Y(0),x+ml+pw,Y(0),C.ink,1.7);L(s,X(0),y+mt,X(0),y+mt+ph,C.ink,1.7);
 L(s,X(2),y+mt,X(2),y+mt+ph,C.gold,1.5);
 const pts=[];const start=Math.max(xmin,interval[0]),end=Math.min(xmax,interval[1]);for(let i=0;i<=240;i++){const a=start+(end-start)*i/240,val=a*a-4*a+1;if(val>=ymin&&val<=ymax)pts.push({x:X(a)-(x+ml),y:Y(val)-(y+mt)});}
 s.shapes.add({geometry:'custom',position:{left:x+ml,top:y+mt,width:pw,height:ph},fill:'none',line:{fill:curve,width:3},customPaths:[{width:pw,height:ph,commands:pts.map((q,i)=>i?{lineTo:q}:{moveTo:q})}]});
 T(s,'x',x+w-17,Y(0)-29,25,28,20);T(s,'f(x)',X(0)+9,y+mt-2,60,28,20);
 return {X,Y};
}
// 2. Same raw information as the rejected fee page; stronger decision and comparison.
{
 const s=P('开放日费用与到场','report','比较投入增幅、实到增幅与单位费用','完整费用及人数、同尺度增幅图与判断边界','判断统领与比较系统','费用增加25%，实到增加31.3%；B场每位实到费用约低4.8%');
 context(s,'模拟资料 · 非学校实绩；两场费用口径相同，比较基准均为A场');
 d.nativeTable(s,[['费用（元）','A场','B场','B−A'],['场地','6,000','6,000','0'],['物料','2,000','4,000','+2,000'],['师资','4,000','5,000','+1,000'],['合计','12,000','15,000','+3,000']],{x:48,y:202,w:682,h:260,columnWidths:[196,150,150,186],rowHeights:[52,52,52,52,52],size:22,numericColumns:[1,2,3],focusRow:4});
 R(s,772,202,460,260,C.purple);T(s,'A→B：两项增幅在同一尺度比较',794,218,416,37,22,{color:C.white,bold:true});
 d.chart(s,'bar',{position:{left:788,top:264,width:426,height:160},categories:['实到增幅','费用增幅'],series:[{name:'相对A场增幅',categories:['实到增幅','费用增幅'],values:[31.25,25],fill:C.gold,dataLabels:{showValue:true,position:'center',numberFormatCode:'0.0"%"',textStyle:{fontSize:25,fill:C.white,bold:true}}}],barOptions:{direction:'bar',grouping:'clustered',gapWidth:75},xAxis:{textStyle:{fontSize:21,fill:C.white},line:{fill:'none',width:0},majorGridlines:{fill:'none',width:0}},yAxis:{min:0,max:40,visible:false,majorGridlines:{fill:'none',width:0}}});
 T(s,'实到增长快于费用增长，单位投入略降。',794,424,416,30,20,{color:C.white});
 d.nativeTable(s,[['活动','预约（人）','实到（人）','到场率'],['A场','120','96','80%'],['B场','180','126','70%']],{x:48,y:501,w:682,h:147,columnWidths:[196,150,150,186],rowHeights:[49,49,49],size:22,numericColumns:[1,2,3],headerStyle:'tint'});
 H(s,'125 → 119.05 元/人',772,496,460,28);T(s,'每位实到费用＝费用÷实到人数',772,540,460,31,21);
 T(s,'到场率降低10个百分点，需单独关注。',772,581,460,37,23,{bold:true,color:C.red});T(s,'缺少后续报名记录，不能判断招生转化。',772,623,460,30,20);
}
// 3. A teacher can use the actual task, expected response and feedback relationship.
{
 const s=P('区间最值教学设计','lessonPlan','组织任务、预期错误和针对性再教','20分钟计划中的真实设问、回应与判别','教学活动与回应查阅','让学生用顶点位置与距离解释最值，避免只算端点或混淆量词');
 context(s,'原创高中学习单元 · 约20分钟计划，非完整课时或真实授课记录');
 H(s,'前置检查',48,201,170,24);T(s,'将x²−4x＋1配方，定位顶点；判断顶点是否在[−1,4]内。\n若配方困难，展开(x−2)²−3回检常数项。',229,200,1003,70,23);
 d.nativeTable(s,[['环节','任务与材料','预期回应／困难','判别与处理'],['4分钟\n固定区间','f(x)＝x²−4x＋1，x∈[−1,4]。\n配方并在图上定位最值。','可能只比较−1与4的大小，\n把较大x当最大值位置。','让学生比较端点到x＝2的距离，\n用平方项与图像共同说明。'],['6分钟\n移动端点','定义域改为[−1,t]，t>−1；\n顶点何时进入区间？','可能一直取m(t)＝f(t)，\n没有检查内部顶点。','用t＝4反查；要求写分类依据，\n在t＝2核对两支衔接。'],['5分钟\n任意成立','对任意x，f(x)≥−2；\n先写等价的最值条件。','可能直接查端点，\n或解出t≤1后忘记原范围。','核对m(t)≥−2；\n用t＝1检验等号与t>−1。'],['5分钟\n独立迁移','比较任意>与存在≤；\n构造端点判断法的反例。','量词变了却照抄范围，\n或反例没有内部失败点。','保留条件、理由与反例三项产出；\n按具体错误回到图像重试。']],{x:48,y:294,w:1184,h:355,columnWidths:[132,348,328,376],rowHeights:[47,77,77,77,77],size:20,headerStyle:'purple',cellPadding:{left:10,right:10,top:6,bottom:6}});
}
// 4. Complete learning object, representation, proof, changed condition and feedback.
{
 const s=P('区间、顶点与最值','classroom','联系配方、图像与端点距离','真实XY图形、完整题干、理由和短变式','函数图与推理相邻');
 R(s,48,112,1184,96,C.purple);T(s,'已知 f(x)＝x²−4x＋1，x∈[−1,4]。\n求函数的值域，并说明最值为何在相应位置取得。',71,119,1138,85,26,{color:C.white,bold:true});
 const g=graph(s,{x:48,y:224,w:522,h:306});
 [[-1,6],[2,-3],[4,1]].forEach(([a,v])=>DOT(s,g.X(a),g.Y(v),5,C.red));
 T(s,'(−1,6)',g.X(-1)+10,g.Y(6)-26,105,28,20,{bold:true,color:C.red});T(s,'(2,−3)',g.X(2)+10,g.Y(-3)-4,100,28,20,{bold:true,color:C.red});T(s,'(4,1)',g.X(4)-78,g.Y(1)-33,90,28,20,{bold:true,color:C.red});
 H(s,'f(x)＝(x−2)²−3',624,216,608,32);
 const steps=[['顶点在区间内','2∈[−1,4]，平方项可取0；\n最小值−3，在x＝2处取得。'],['最大值看距离','左端到对称轴距离3，右端距离2；\n平方项越大，函数值越大。'],['回到原式核对','f(−1)＝6，f(4)＝1；\n最大值6，值域为[−3,6]。']];
 steps.forEach((a,i)=>{let y=268+i*94;T(s,String(i+1),624,y,35,35,25,{bold:true,color:C.purple});H(s,a[0],672,y,560,23);T(s,a[1],672,y+34,560,59,22,{lineSpacing:1.15});});
 R(s,48,558,1184,94,C.pale);H(s,'独立变式',68,572,160,23);T(s,'x∈[0,3]时的值域？说明依据。',68,609,514,36,21);
 const ans=T(s,'值域[−3,1]；f(0)＝1，f(3)＝−2。\n若误取右端点，回到对称轴两侧的距离核对。',630,580,576,66,22,{bold:true});d.registerReveal(s,[ans],{label:'独立变式作答后显示反馈'});
}
// 5. The classification comes from the vertex entering the interval.
{
 const s=P('移动端点与恒成立','classroom','建立区间位置分类与任意量词的最值等价','两种区间位置及完整分支证明','条件分支与阈值证明','顶点进入区间前看右端点，进入后看顶点；任意成立要检查最小值');
 R(s,48,182,1184,90,C.pale);T(s,'仍设 f(x)＝x²−4x＋1，定义域[−1,t]，t>−1。\n求最小值m(t)；若任意x均有f(x)≥−2，求t的范围。',69,189,1142,79,25);
 H(s,'区间位置决定最小值',48,278,540,25);
 const lineX=a=>84+(a+1)/5*454;
 [[326,1,'−1<t<2：区间在对称轴左侧','m(t)＝(t−2)²−3'],[495,3,'t≥2：顶点进入区间','m(t)＝−3']].forEach(([y,t,cond,formula])=>{L(s,lineX(-1),y,lineX(4),y,C.line,1.7);L(s,lineX(-1),y,lineX(t),y,C.purple,8);for(const [a,label] of [[-1,'−1'],[2,'2'],[t,'t']]){DOT(s,lineX(a),y,5,a===t?C.red:C.purple);T(s,label,lineX(a)-15,y+12,36,30,23,{align:'center',bold:true,color:a===t?C.red:C.ink});}T(s,cond,48,y+50,540,35,24,{bold:true});T(s,formula,48,y+89,540,34,25);T(s,t<2?'在此区间递减，最小值在右端t取得。':'平方项可取0，最小值在顶点取得。',48,y+125,540,31,20);});
 L(s,600,278,600,648,C.line,1.2);
 H(s,'对任意x，f(x)≥−2',648,278,584,27);T(s,'⇔ m(t)≥−2',648,326,584,45,33,{bold:true,color:C.red});
 T(s,'若t≥2，m(t)＝−3，不满足。\n若−1<t<2：\n(t−2)²−3≥−2 ⇔ |t−2|≥1。\n结合t<2，得t≤1。',648,390,584,145,25);
 T(s,'所以 −1<t≤1',648,559,584,49,35,{bold:true,color:C.purple});T(s,'t＝1时恰取−2；t＝2时两支m(t)均为−3。',648,620,584,34,22);
}
// 6. Independent work and its feedback stay paired; feedback appears by task.
{
 const s=P('量词变化与反例检验','worksheet','独立写最值条件并用边界或反例核对','三题任务链及逐题诊断','共同题干与纵向问题反馈');
 R(s,48,112,1184,96,C.purple);T(s,'f(x)＝x²−4x＋1，x∈[−1,t]，t>−1。\n先写m(t)与−2的关系，再按区间位置求参数范围。',70,120,1140,83,25,{color:C.white,bold:true});
 H(s,'独立作答',48,217,592,24);H(s,'作答后核对理由与错误',692,217,540,24);L(s,650,221,650,651,C.line,1.2);
 const rows=[
 {y:264,k:'A',q:'对任意x，f(x)>−2，求t的范围。\n与“≥−2”相比，哪处边界改变？',a:'m(t)>−2 ⇒ −1<t<1。\nt＝1时可取−2，严格不等号排除1。',f:'若仍保留1：回代x＝1检验。'},
 {y:400,k:'B',q:'存在x，使f(x)≤−2，求t的范围。\n先写m(t)与−2的关系。',a:'m(t)≤−2：t<2时得1≤t<2；\nt≥2时均满足，合并t≥1。',f:'若照搬A：对比“所有点”与“至少一点”。'},
 {y:536,k:'C',q:'“只查两个端点就能判断f(x)≥−2。”\n构造反例，写出漏查的位置。',a:'取t＝4：f(−1)＝6、f(4)＝1；\n但f(2)＝−3<−2，内部顶点使判断失败。',f:'反例需同时给t、端点值及内部失败点。'}];
 rows.forEach((r,i)=>{H(s,r.k,48,r.y,48,27);T(s,r.q,111,r.y,510,78,25);const objs=[T(s,r.a,692,r.y,540,74,24,{bold:true}),T(s,r.f,692,r.y+82,540,33,20,{color:C.purple})];d.registerReveal(s,objs,{label:`${r.k}题独立作答后的理由与诊断`});if(i<2)L(s,48,r.y+123,1232,r.y+123,C.line,1);});
}
// 7. Whole original text; action lines and annotations share their reading order.
{
 const s=P('动作与人物关系','classroom','用前后动作解释人物间回应并保留判断限度','完整原创语境、动作证据与删句检验','原文与就近证据解释','把前后动作连起来解释，人物关系才能从文本证据中显现');
 context(s,'初中阅读 · 原创文本与示范分析，非教材选文');
 R(s,48,201,678,315,C.pale);
 const lines=['晚自习后，雨还没停。林宁推开门，','父亲正坐在门边的小凳上，裤脚湿了一圈。','“等久了吧？”她问。父亲把手机扣在膝上，','说：“刚到。”她看见屏幕上那盘棋还停在','下午自己教他的那一步。','回家路上，父亲把伞往她那边推了推，','自己半边肩膀露在雨里。林宁想说什么，','张了张嘴，却只把书包换到靠外的一侧，','腾出手，将伞柄轻轻拨回两人中间。'];
 lines.forEach((v,i)=>T(s,v,72,218+i*31,630,33,22.8,{bold:[5,7,8].includes(i),color:[5,7,8].includes(i)?C.purple:C.ink}));
 H(s,'先区分事实与推测',774,201,458,24);T(s,'“刚到”与湿裤脚暗示等待；\n具体时长未交代，不能补写“两小时”。',774,245,458,85,22);
 H(s,'推伞：照顾的空间后果',774,347,458,24);T(s,'父亲让自己的半边肩膀露在雨里，\n动作后果支持他优先照顾女儿的判断。',774,391,458,82,23);
 H(s,'拨回：对前一动作的回应',774,492,458,24);T(s,'“换—腾—拨回”与推伞照应，\n把关心写成父女之间的双向动作；\n人物没有直接说出心情。',774,536,458,109,23);
 H(s,'删句检验',48,549,678,24);T(s,'删去末句，女儿回应的依据怎样变化？',48,590,678,33,23,{bold:true});
 const answer=T(s,'父亲的关心仍有依据，女儿回应的动作证据减少。',48,628,678,30,21);d.registerReveal(s,[answer],{label:'删句判断后核对证据变化'});
}
// 8. A new text withdraws scaffolding and tests evidence, relation and certainty.
{
 const s=P('证据、解释与分寸','classroom','在新文本独立表达并修订过度推断','新原文、待修回应及逐项修订理由','新材料与回应修订');
 R(s,48,112,1184,145,C.purple);T(s,'比赛失利后，陈越把奖牌盒推到桌角。母亲没有问名次，只把台灯转向他摊开的草稿纸。\n第二天，盒子仍在原处，旁边多了一张写着“先改这一题”的便签。',71,139,1138,96,26,{color:C.white});
 context(s,'原创迁移文本 · 非教材选文',273);
 H(s,'独立任务',48,327,400,26);T(s,'结合两处细节解释支持方式，\n并保留一处尚不能确定的信息。\n说明你保留判断的原因。',48,375,400,117,26);
 T(s,'先独立写两三句，再核对示范。',48,505,400,35,22,{bold:true});H(s,'核对自己的回应',48,554,400,24);T(s,'引用准确　｜　解释细节联系\n区分事实与推断',48,598,400,64,21);
 H(s,'待修订回应',510,327,722,25);
 const flawed=RT(s,[['母亲很温柔，',{t:'她一定写了便签'},'鼓励儿子，'],[{t:'陈越马上振作起来'},'。']],510,376,722,73,28);d.registerReveal(s,[flawed],{label:'独立回应后再比较待修订回应'});
 const objs=[T(s,'“没有问名次”与转向草稿纸相连，关注落在下一步问题上。\n“先改这一题”把支持落实为行动，并与草稿纸呼应。',510,477,722,80,23,{bold:true}),T(s,'便签作者、陈越此后的反应均未交代。\n保留支持的判断，删除“一定”和“马上振作”的断言。',510,574,722,77,23,{color:C.purple})];
 d.registerReveal(s,objs,{label:'新材料独立回应后的依据与分寸核对'});
}
// 9. Same source and responses as rejected P9, with actual reading and support.
{
 const s=P('阅读反馈与家庭支持','parent','依据原文和单次修订解释变化并安排复核','完整原文、初修稿与具体家庭支持','材料与作品对照','这次修订补上了动作依据，下一步检验能否独立解释');
 context(s,'虚构学生案例 · 单次指导记录，不代表学校实绩');
 R(s,48,200,355,405,C.purple);T(s,'本次阅读材料',70,221,311,42,25,{color:C.white,bold:true});T(s,'他走到门口，\n回头看了看乱放的书，\n便折回去把书\n一一整理好。',70,291,311,165,27,{color:C.white});T(s,'任务：引用动作，\n说明对人物的判断。',70,508,311,76,23,{color:C.white});
 H(s,'初稿',449,201,200,23);T(s,'他很认真。',449,245,783,49,35);L(s,449,309,1232,309,C.line,1.2);
 H(s,'修订后',449,335,783,23);R(s,449,383,783,104,C.pale);T(s,'他走到门口又折回去，\n愿意把整理书的事情做完。',470,397,741,83,31,{bold:true});
 H(s,'已经补上',449,503,408,23);T(s,'“折回去”提供动作依据，\n并把动作与判断连起来。',449,546,408,64,22);
 H(s,'仍需观察',930,503,302,23);T(s,'一次指导后的修订，\n还不能证明稳定掌握。',930,546,302,64,22);
 T(s,'家庭建议：换文独立答“哪句话支持？为什么？”，再看能否自行引用并解释。',48,625,1184,32,21,{bold:true,color:C.purple});
}
// 10. The learning artefact, rather than an unrelated building, carries the experience.
{
 const s=P('走进一段学习过程','parent','判断拟议体验中孩子做什么、家长观察什么','拟议30分钟任务体验、图像及理由对照','学习体验与参与顺序');
 context(s,'拟议体验方案 · 非已公布活动；适用对象、时间及入学条件需另行确认',112);
 R(s,48,168,355,483,C.purple);T(s,'先独立判断，\n再解释依据。',70,198,311,133,39,{color:C.white,bold:true});T(s,'30分钟二次函数微课堂',70,381,311,77,29,{color:C.white,bold:true});T(s,'建议面向已认识\n抛物线顶点的高中学生\n及希望观察学习过程的家长。',70,495,311,126,23,{color:C.white});
 H(s,'孩子写下理由，家长看见思考过程',439,169,793,27);
 T(s,'f(x)＝x²−4x＋1，x∈[−1,4]',439,216,793,31,21,{bold:true});
 const g=graph(s,{x:439,y:253,w:350,h:244,labels:true});
 [[-1,6],[2,-3],[4,1]].forEach(([a,v])=>DOT(s,g.X(a),g.Y(v),4,C.red));
 H(s,'最大值在哪取得？',826,225,406,23);
 T(s,'凭直觉：x＝4更大，\n就把f(4)当最大值。',826,270,406,75,24,{color:C.red});
 T(s,'看依据：左端到轴距离3，\n右端距离2；因此最大值在左端。',826,367,406,79,23,{bold:true});
 T(s,'体验题例为原创，作答为示意。',826,460,406,28,18,{color:C.secondary});
 const a=[['5分钟','观察图像'],['12分钟','独立作答'],['8分钟','比较理由'],['5分钟','反馈交流']];
 a.forEach((v,i)=>{let x=439+i*199;H(s,v[0],x,528,180,24);T(s,v[1],x,574,180,34,23,{bold:true});});
 T(s,'带走的成果：一个值域判断、一段理由和一次针对性反馈。',439,624,793,34,22,{color:C.purple,bold:true});
}
const pptx=path.join(B,'华朗学校分场景应用样页_V10.pptx');
await d.writeRevealManifest(path.join(B,'reveals.json'));
const rendered=await d.writeDraft({candidatePath:pptx,renderDir:path.join(B,'render'),scale:1.5});
await fs.writeFile(path.join(B,'render-result.json'),JSON.stringify(rendered,null,2));
await fs.writeFile(path.join(B,'sequence.json'),JSON.stringify({slides:seq},null,2));
console.log(JSON.stringify({pptx,slideCount:d.presentation.slides.items.length,renderDir:rendered.renderDir}));
