// Original simulated material. Pass the skill folder and a temporary output folder.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const [skillArg,outArg]=process.argv.slice(2);
if(!skillArg||!outArg)throw new Error('Provide skillDir and outputDir.');
const skillDir=path.resolve(skillArg),out=path.resolve(outArg);
await fs.mkdir(out,{recursive:true});
const kit=path.join(out,'hualang-kit.mjs');
await fs.copyFile(path.join(skillDir,'scripts/hualang-kit.mjs'),kit);
const {createDeck,colors:C}=await import(pathToFileURL(kit));
const require=createRequire(pathToFileURL(kit));
const {PresentationFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const deck=await createDeck({skillDir,title:'学习支持设计样张',presenter:'示例工作组',date:'2026年11月7日',zhFont:'Microsoft YaHei',latinFont:'Arial',sceneMode:'mixed'});
const sequence=[];
const tx=(s,v,x,y,w,h,size=21,extra={})=>deck.text(s,v,{x,y,w,h,size,...extra});
const block=(s,x,y,w,h,fill)=>s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:'none',width:0}});
const ellipse=(s,x,y,w,h,fill)=>s.shapes.add({geometry:'ellipse',position:{left:x,top:y,width:w,height:h},fill,line:{fill:'none',width:0}});
const page=(title,lead,family,task,object,purpose='report')=>{
 const s=deck.addPage({title,section:'学习支持方案（模拟） · 拟议安排，供讨论',purpose});
 if(lead)tx(s,lead,48,112,1184,60,21);
 sequence.push({slide:sequence.length+2,title,family,task,mainObject:object});return s;
};
// Common-object support: compact geometry, explicit attachment points, calm text hierarchy.
{
 const s=page('支持分工','围绕同一学生分配支持责任，用具体行动与学习证据核对执行。','center-support','理解共同对象与角色支撑','中心对象、关系词与四类具体支持');
 deck.hubSpoke(s,{center:{x:640,y:370,r:82,title:'同一学生',body:'个人目标\n学习证据',size:27},nodes:[
  {x:100,y:198,w:325,h:140,title:'学科教师',relation:'练习反馈',anchor:{x:425,y:244},label:{x:461,y:266,w:76,h:28},body:'依据匿名作答定位困难，\n安排对应练习，保留新作答，\n复核能否解释依据。'},
  {x:855,y:198,w:325,h:140,title:'导师',relation:'目标跟进',anchor:{x:855,y:244},label:{x:744,y:266,w:76,h:28},body:'核对个人目标、任务与执行，\n记录障碍，再与学生商定调整。'},
  {x:100,y:415,w:325,h:140,title:'学生服务组',relation:'条件协调',anchor:{x:425,y:458},label:{x:461,y:418,w:76,h:28},body:'识别影响参与的条件，\n协调时间与材料，再交回导师。'},
  {x:855,y:415,w:325,h:140,title:'家庭',relation:'环境观察',anchor:{x:855,y:458},label:{x:744,y:418,w:76,h:28},body:'提供稳定学习条件，\n反馈居家观察与具体困难，\n观察与学习表现分别记录。'}
 ],size:20,titleSize:24});
 tx(s,'复核依据',100,596,164,32,22,{bold:true,color:C.purple});
 tx(s,'参与记录说明执行情况；独立作答反映理解。\n分工本身不能证明支持已经产生效果。',282,594,898,63,20,{color:C.secondary});
}
// Set inclusion: containment is visible, prose describes entry/exit rather than floating labels.
{
 const s=page('支持范围','基础学习覆盖全体，专项支持随诊断进入与退出，不预设固定人数。','nested-scope','辨认支持范围与进入条件','三层支持范围与对应条件');
 ellipse(s,96,180,456,456,'#F1EDF6');
 ellipse(s,164,284,320,320,'#DFD6EA');
 ellipse(s,236,398,176,176,C.purple);
 tx(s,'基础学习',156,212,336,39,26,{bold:true,color:C.purple,align:'center'});
 tx(s,'全体学生',156,258,336,30,20,{align:'center'});
 tx(s,'专项支持',208,317,232,39,25,{bold:true,color:C.purple,align:'center'});
 tx(s,'按具体困难进入',196,362,256,30,20,{align:'center'});
 tx(s,'个别评估',246,435,156,35,24,{bold:true,color:C.white,align:'center'});
 tx(s,'仍有困难者',246,482,156,30,18,{color:C.white,align:'center'});
 const groups=[
  ['共享基础','完整任务与同一评价标准供全体使用，\n先观察作答，再判断具体困难。',208],
  ['进入条件','有明确困难时进入短期支持；\n并非每位学生都要依次走完三层。',350],
  ['调整依据','用新任务检验能否独立解释与完成，\n再决定继续、调整或回到基础安排。',492]
 ];
 for(const [title,body,y] of groups){tx(s,title,680,y,536,34,24,{bold:true,color:C.purple});tx(s,body,680,y+47,536,65,21);}
 tx(s,'范围示意，面积不代表人数或资源比例。',96,650,1120,26,17,{color:C.secondary});
}
// A restrained ascending base supports actual evidence; no oversized empty steps.
{
 const s=page('阶段递进','诊断、练习与迁移各自留下可复核材料；证据满足要求后，再推进下一阶段。','evidence-progression','理解阶段动作与推进依据','三阶段任务、具体材料与低阶台基');
 const cols=[
  {x:48,y:204,title:'诊断',object:'原题：y = 2x + 1',example:'“x 增加3，y 也增加3”',body:'定位两个变化量被直接等同的困难，\n保留原作答与学生解释。',criterion:'推进依据\n困难及其条件能够说明',baseY:574,baseH:64,fill:'#E4DCEB',out:'形成困难清单',outColor:C.purple},
  {x:456,y:204,title:'练习',object:'修订与方法解释',example:'Δy = 2Δx',body:'安排对应练习，解释系数的作用；\n留下新的作答与理由。',criterion:'推进依据\n方法、理由与结果对应',baseY:548,baseH:90,fill:'#79678F',out:'形成解释证据'},
  {x:864,y:204,title:'迁移',object:'新情境独立作答',example:'y = −3x + 2，Δx = −2',body:'改变情境与符号，先独立作答；\n检查条件判断能否迁移。',criterion:'复核依据\n新条件下仍能独立应用',baseY:522,baseH:116,fill:C.purple,out:'形成迁移证据'}
 ];
 for(const c of cols){
  tx(s,c.title,c.x,c.y,368,41,28,{bold:true,color:C.purple});
  tx(s,c.object,c.x,c.y+68,368,30,20,{color:C.secondary});
  tx(s,c.example,c.x,c.y+107,368,61,25,{bold:true,color:C.blue});
  tx(s,c.body,c.x,c.y+180,368,61,20);
  tx(s,c.criterion,c.x,c.y+252,368,56,18,{color:C.secondary});
  block(s,c.x,c.baseY,368,c.baseH,c.fill);
  tx(s,c.out,c.x+22,c.baseY+17,324,32,21,{bold:true,color:c.outColor??C.white});
 }
 tx(s,'具体日期未定；未达到要求时，回到对应困难继续支持。',48,650,1184,25,17,{color:C.secondary});
}
// Shared work surface makes the actual correction the principal object.
{
 const s=page('作答修订','一次修订须说明变化量的依据，再用新情境检验理解。','work-comparison','定位错误并比较依据','共享题干下的初稿、修订和独立检验');
 tx(s,'已知 y = 2x + 1，x 增加3，y 增加多少？',48,188,1184,49,28,{bold:true});
 block(s,48,268,1184,246,'#F3F0F7');
 tx(s,'匿名初稿',76,292,330,30,19,{color:C.secondary});
 tx(s,'Δy = 3',76,341,330,56,38,{bold:true,color:C.red});
 tx(s,'把两个变量的变化量直接等同，\n遗漏了系数的作用。',76,425,340,64,20);
 tx(s,'修订',496,292,708,30,19,{color:C.secondary});
 tx(s,'Δy = 2Δx',496,341,708,56,38,{bold:true,color:C.blue});
 tx(s,'= 2 × 3 = 6',496,405,708,46,30,{color:C.blue});
 tx(s,'常数项不改变，系数2决定变化量的倍数。',496,467,708,31,20);
 tx(s,'独立检验',48,560,180,33,24,{bold:true,color:C.purple});
 tx(s,'y = −3x + 2，x 减少2。先独立作答，再解释符号。',256,559,976,35,23);
 tx(s,'核对：Δy = −3 × (−2) = 6。结论与理由都需成立。',256,608,976,34,21);
}
// Architecture photographs carry the composition; captions sit outside the image.
{
 const s=page('空间观察','光廊的纵深与光庭的开敞，形成两种可观察的空间尺度。','editorial-evidence','观察主场景与补充细节','光廊主照片、光庭局部与近邻图注','parent');
 await deck.image(s,path.join(skillDir,'assets/hualang-light-corridor.jpg'),{x:48,y:180,w:760,h:396,fit:'cover',alt:'华朗光廊，保留顶部光线和建筑进深'});
 await deck.image(s,path.join(skillDir,'assets/hualang-light-court.jpg'),{x:848,y:180,w:384,h:214,fit:'cover',alt:'华朗光庭局部，展示阶梯、连廊和开敞空间'});
 tx(s,'光廊的纵深',48,597,344,35,24,{bold:true,color:C.purple});
 tx(s,'连续的立柱与顶部采光，强化路径的方向感。',48,640,760,31,19);
 tx(s,'光庭的开敞',848,419,384,35,24,{bold:true,color:C.purple});
 tx(s,'阶梯与连廊共同界定开敞节点，\n不同高度的空间关系清楚可见。',848,466,384,76,21);
 tx(s,'照片呈现空间条件；\n学习成效需要另行验证。',848,587,384,66,18,{color:C.secondary});
}
// A shared 50-person scale directly connects attainment and the remaining group.
{
 const s=page('学习变化','同一班50人、同一标准，达标人数增加，仍有学生需要具体支持。','native-data-and-interpretation','比较人数、比例与支持余量','共同50人尺度的原生堆叠条形及近邻解读');
 tx(s,'同一班50人',48,196,720,34,24,{bold:true,color:C.purple});
 deck.chart(s,'bar',{position:{left:48,top:254,width:788,height:242},categories:['后测','前测'],series:[
  {name:'达标',values:[39,32],fill:C.blue,dataLabels:{showValue:true,position:'center',textStyle:{fontSize:23,fill:C.white,bold:true}}},
  {name:'未达标',values:[11,18],fill:'#E4DDEB',dataLabels:{showValue:true,position:'center',textStyle:{fontSize:23,fill:C.purple}}}
 ],barOptions:{direction:'bar',grouping:'stacked',gapWidth:160,overlap:100},hasLegend:false,
 xAxis:{visible:true,line:{fill:'none',width:0},majorGridlines:{fill:'none',width:0},textStyle:{fontSize:22,fill:C.ink}},
 yAxis:{visible:false,min:0,max:50,majorGridlines:{fill:'none',width:0}}});
 block(s,48,521,17,17,C.blue);tx(s,'达标',78,517,115,29,18,{color:C.secondary});
 block(s,202,521,17,17,'#E4DDEB');tx(s,'未达标',232,517,160,29,18,{color:C.secondary});
 tx(s,'+7',920,191,290,85,64,{bold:true,color:C.purple});
 tx(s,'达标人数净增',920,285,290,34,22);
 tx(s,'64% → 78%',920,363,290,41,28,{bold:true,color:C.blue});
 tx(s,'提高14个百分点',920,415,290,32,20);
 tx(s,'仍有11人未达标',48,584,322,34,23,{bold:true,color:C.red});
 tx(s,'按具体困难安排后续支持，并沿同一标准复核。',408,585,824,33,21);
 tx(s,'汇总人数无法识别具体学生的前后转变；现有比较也不能将变化归因于某项措施。',48,641,1184,31,19,{color:C.secondary});
}
const candidatePath=path.join(out,'composition-atlas-candidate.pptx');
await (await PresentationFile.exportPptx(deck.presentation)).save(candidatePath);
await fs.writeFile(path.join(out,'sequence.json'),JSON.stringify({slides:sequence},null,2));
console.log(JSON.stringify({candidatePath,slides:deck.presentation.slides.items.length}));
