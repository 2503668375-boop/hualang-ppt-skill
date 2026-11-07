import fs from 'node:fs/promises';
import path from 'node:path';
import {PresentationFile} from '@oai/artifact-tool';
import {createDeck,renderSavedDeck} from './hualang-kit.mjs';
const [skillDir,out]=process.argv.slice(2);
const d=await createDeck({skillDir,title:'图片留位验证',presenter:'示例工作组',date:'2026年11月7日',zhFont:'Noto Sans SC'});
const s=d.addPage({title:'横竖图位'});
const landscape=d.imageSlot(s,{x:48,y:190,w:720,h:405,title:'课堂操作现场',
  brief:'保留双手、器材与操作过程，\n让读者看见具体任务。',name:'landscape',fit:'cover'});
const portrait=d.imageSlot(s,{x:840,y:150,w:344,h:468,title:'学生作品局部',
  brief:'保留题目与关键作答。\n遮去姓名与学号。',name:'portrait',fit:'contain'});
const originalPhoto=d.addPage({title:'实图原位'});
await d.image(originalPhoto,path.join(skillDir,'assets/hualang-light-corridor.jpg'),
  {...landscape.frame,fit:landscape.fit,alt:'既有校园素材，用于验证原位填图的边界'});
d.text(originalPhoto,'既有校园素材\n替换范围与横图留位一致。',
  {x:840,y:222,w:344,h:120,size:25});
const rejected=[];
for(const [name,change] of [
  ['outside-canvas',{x:1200}],['negative-size',{w:-1}],['nan',{h:NaN}],
  ['empty-title',{title:''}],['empty-brief',{brief:''}],['unknown-fit',{fit:'stretch'}],
  ['too-short',{h:130}],['too-narrow',{w:100}],['invalid-padding',{padding:-1}],
  ['invalid-line-height',{lineHeight:0.5}]
]){
  const before=s.shapes.items.length;let threw=false;
  try{d.imageSlot(s,{x:48,y:190,w:720,h:405,title:'所需图片',brief:'明确画面中的内容。',...change})}catch{threw=true}
  rejected.push({name,threw,unchanged:s.shapes.items.length===before});
}
const file=path.join(out,'image-slot.pptx');
await(await PresentationFile.exportPptx(d.presentation)).save(file);
const result={file,landscape:{frame:landscape.frame,fit:landscape.fit,objects:landscape.objects.length},
  portrait:{frame:portrait.frame,fit:portrait.fit,objects:portrait.objects.length},rejected};
if(process.env.HUALANG_TEST_OUTPUT)result.preview=await renderSavedDeck({candidatePath:file,renderDir:path.join(out,'render'),slides:[2,3],scale:1});
await fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2));
