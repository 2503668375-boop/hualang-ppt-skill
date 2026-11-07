import fs from 'node:fs/promises';
import path from 'node:path';
import {PresentationFile} from '@oai/artifact-tool';
import {createDeck,renderSavedDeck,colors} from './hualang-kit.mjs';
const [skillDir,out]=process.argv.slice(2);
const d=await createDeck({skillDir,title:'组件细节验证',presenter:'示例工作组',date:'2026年11月7日',zhFont:'Noto Sans SC'});
const s=d.addPage({title:'标签与内容'});
d.methodStrip(s,'判断成立的条件','同一指标、同一期间与同一统计范围。\n先保留比较条件，再说明差异。',
  {x:48,y:150,w:1184,labelWidth:210,labelSize:23,size:24,padding:{x:20,y:16},gap:28});
d.lessonBand(s,'课前任务','阅读两份匿名作答，指出理由从哪里来。\n保留原文，并标出支撑判断的具体词句。',
  {x:48,y:325,w:980,labelWidth:144,labelSize:24,labelPadding:18,size:25,padding:{x:24,y:18},gap:24});
d.lessonBand(s,'观察','单行任务与标签共用垂直中心。',{x:48,y:485,w:860,h:126,labelWidth:100,size:26});
const a=d.addPage({title:'证据与批注'});
d.text(a,'原方案：两场活动均已确定。\n\n报价：A场12,000元，B场15,000元。\n\n尚未给出后续到访与报名记录。',{x:48,y:200,w:620,h:310,size:27});
d.evidenceNote(a,'已确认事项保留原状态，\n不另写成待选方案。',{x:830,y:205,w:350,h:120,title:'事实状态',anchor:{x:420,y:234},size:23});
d.evidenceNote(a,'原始数据不支持成效判断，\n待补资料另行说明。',{x:830,y:422,w:350,h:120,title:'结论边界',anchor:{x:450,y:375},attach:{x:830,y:437},route:'elbow',elbow:750,gap:12,marker:false,size:23});
const h=d.addPage({title:'共同支持'});
d.hubSpoke(h,{center:{x:640,y:385,r:92,title:'学习任务',body:'共同支持'},nodes:[
  {x:70,y:220,w:325,h:160,title:'教师',relation:'提供反馈',body:'依据作答定位具体困难，\n安排新的检验任务。',anchor:{x:395,y:300}},
  {x:890,y:440,w:320,h:160,title:'家庭',relation:'支持练习',body:'提供安静环境与观察反馈，\n保留孩子的独立作答。',anchor:{x:890,y:480}}
]});
const n=d.addPage({title:'窄幅与多行'});
d.methodStrip(n,'家庭共读\n建议','追问哪句话支持判断，\n保留孩子独立解释的时间。',{x:48,y:150,labelWidth:150,labelSize:23,size:24});
d.lessonBand(n,'独立\n作答','比较两份材料，\n说明相同条件下的变化。',{x:48,y:330,w:720,labelWidth:144,labelSize:24,size:26});
const left=d.addPage({title:'左侧批注'});
d.text(left,'修订作答加入了具体词句与理由。',{x:670,y:230,w:562,h:90,size:27});
d.evidenceNote(left,'这份回答能用词句支持判断，\n后续仍需新任务检验。',{x:48,y:200,w:390,h:130,title:'观察到的变化',anchor:{x:670,y:250},size:23,marker:false});
const rejected=[];
function invalid(name,fn){const before=s.shapes.items.length;let threw=false;try{fn()}catch{threw=true}rejected.push({name,threw,unchanged:before===s.shapes.items.length});}
invalid('label-consumes-width',()=>d.methodStrip(s,'条件','正文',{x:48,y:500,w:200,labelWidth:190}));
invalid('multiline-height-too-small',()=>d.methodStrip(s,'条件','第一行\n第二行',{x:48,y:500,w:700,h:40}));
invalid('band-outside-canvas',()=>d.lessonBand(s,'任务','正文',{x:48,y:690,w:700,h:80}));
invalid('attach-not-boundary',()=>d.evidenceNote(s,'正文',{x:700,y:200,w:350,h:100,anchor:{x:400,y:200},attach:{x:710,y:220}}));
invalid('elbow-crosses-note',()=>d.evidenceNote(s,'正文',{x:700,y:200,w:350,h:100,anchor:{x:400,y:230},attach:{x:700,y:220},route:'elbow',elbow:900}));
invalid('connection-inverted',()=>d.hubSpoke(s,{center:{x:640,y:385,r:92,title:'对象'},nodes:[{x:70,y:220,w:325,h:160,title:'角色',relation:'支持',body:'说明'}],connection:{centerGap:500,nodeGap:500}}));
const file=path.join(out,'component-detail.pptx');
await(await PresentationFile.exportPptx(d.presentation)).save(file);
const result={rejected,file};
if(process.env.HUALANG_TEST_OUTPUT)result.preview=await renderSavedDeck({candidatePath:file,renderDir:path.join(out,'render'),slides:[2,3,4,5,6],scale:1});
await fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2));
