// Exercise scene selection in memory and preview one existing template page.
// This fixture deliberately never calls exportPptx or writeDraft.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createDeck, profiles, renderSavedDeck} from './hualang-kit.mjs';

const [skillDir, outputDir] = process.argv.slice(2);
if (!skillDir || !outputDir) throw new Error('Provide skillDir and outputDir.');
await fs.mkdir(outputDir,{recursive:true});
const deckArgs={skillDir,title:'预览接口验证',presenter:'测试用署名',date:'2026年11月7日'};
const mixed=await createDeck({...deckArgs,sceneMode:'mixed'});
const originalSlides=mixed.presentation.slides.items.length;
assert.throws(()=>mixed.addPage({title:'课堂例题'}),/混合场景.*purpose/);
assert.throws(()=>mixed.addSchoolScene({title:'学习反馈'}),/混合场景.*purpose/);
assert.throws(()=>mixed.addPage({title:'课堂例题',purpose:null}),/混合场景.*purpose/);
assert.throws(()=>mixed.addSchoolScene({title:'学习反馈',purpose:null}),/混合场景.*purpose/);
await assert.rejects(()=>createDeck({...deckArgs,sceneMode:'unknown'}),/sceneMode/);
await assert.rejects(()=>createDeck({...deckArgs,defaultPurpose:'unknown'}),/defaultPurpose/);
assert.equal(mixed.presentation.slides.items.length,originalSlides,'Rejected calls must not add a page.');
const classroom=mixed.addPage({title:'课堂例题',purpose:'classroom'});
const parent=mixed.addSchoolScene({title:'学习反馈',purpose:'parent'});
const bodySize=async(deck,slide)=>{
  deck.text(slide,'只在内存核对默认字号。',{x:48,y:120,w:700,h:60,name:'preview-fixture-body'});
  const layout=JSON.parse(await(await slide.export({format:'layout'})).text());
  const element=layout.elements.find(e=>e.name==='preview-fixture-body');
  assert.ok(element,'The in-memory body must appear in layout evidence.');
  return element.style.fontSize;
};
const observedFonts={classroom:await bodySize(mixed,classroom),parent:await bodySize(mixed,parent)};
assert.equal(observedFonts.classroom,profiles.classroom.body);
assert.equal(observedFonts.parent,profiles.parent.body);

const single=await createDeck({...deckArgs,sceneMode:'single',defaultPurpose:'parent'});
const defaultPage=single.addPage({title:'家长反馈'});
const defaultScene=single.addSchoolScene({title:'课程说明'});
observedFonts.singlePage=await bodySize(single,defaultPage);
observedFonts.singleScene=await bodySize(single,defaultScene);
assert.equal(observedFonts.singlePage,profiles.parent.body);
assert.equal(observedFonts.singleScene,profiles.parent.body);
const override=single.addPage({title:'教师备课',purpose:'lessonPlan'});
observedFonts.singleOverride=await bodySize(single,override);
assert.equal(observedFonts.singleOverride,profiles.lessonPlan.body);

const source=path.join(skillDir,'assets','source-original.pptx');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const sourceBefore=await fs.readFile(source), sourceSha256=sha(sourceBefore);
const renderArgs={candidatePath:source,renderDir:path.join(outputDir,'previews'),slides:[2],scale:.5,
  pageContexts:[{slide:2,scene:'existing-template'}]};
const first=await renderSavedDeck(renderArgs);
const second=await renderSavedDeck(renderArgs);
assert.notEqual(first.renderDir,second.renderDir,'Each preview invocation needs its own evidence directory.');
for(const result of [first,second]){
  assert.equal(result.reviewStatus,'unreviewed');
  const manifest=JSON.parse(await fs.readFile(result.renderManifestPath,'utf8'));
  assert.equal(manifest.status,'unreviewed');
  assert.equal(manifest.artifact.sha256,sourceSha256);
  assert.equal(manifest.renderSourceSha256,sourceSha256);
  assert.deepEqual(manifest.scope,[2]);
  assert.equal(manifest.pages.length,1);
  assert.equal(manifest.pages[0].slide,2);
  assert.equal(manifest.pages[0].scene,'existing-template');
  assert.equal(manifest.pages[0].verdict,'unverified');
  assert.equal(manifest.pages[0].renderSha256,sha(await fs.readFile(manifest.pages[0].render)));
}
assert.equal(sha(await fs.readFile(source)),sourceSha256,'Previewing must not change the source PPTX.');

const badScales=[0,-1,NaN,Infinity,'0.5'];
for(const scale of badScales){
  await assert.rejects(()=>renderSavedDeck({...renderArgs,scale}),/scale.*positive/i);
}
const badSelections=[[],[0],[999999],[2,2],[1.5],'2'];
for(const slides of badSelections){
  await assert.rejects(()=>renderSavedDeck({...renderArgs,slides}),/unique existing one-based page numbers/);
}
const record={source,sourceSha256,first,second,observedFonts,
  inMemoryChecks:{mixedOmissionRejected:['addPage','addSchoolScene'],
    explicitPurposes:['classroom','parent'],singleDefault:'parent',singleOverride:'lessonPlan'},
  invalidInputsRejected:{scales:badScales.length,slideSelections:badSelections.length}};
await fs.writeFile(path.join(outputDir,'fixture.json'),JSON.stringify(record,null,2)+'\n');
console.log(JSON.stringify({ok:true,sourceSha256,previewedPage:2,renderRuns:2,exportedNewPptx:false}));
