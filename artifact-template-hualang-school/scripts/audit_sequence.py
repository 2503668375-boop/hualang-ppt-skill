#!/usr/bin/env python3
"""Check actual PPTX page order, adjacent composition and native geometry.
The manifest supplies semantic layout families; visual review is still required.
"""
import argparse, collections, hashlib, json, zipfile
from pathlib import Path
import xml.etree.ElementTree as E
from check_style_contract import NS, slide_parts, shapes

def audit(pptx,manifest):
 errors=[];warnings=[];entries=manifest['slides'];by={r['slide']:r for r in entries};rows=[];sigs=[]
 with zipfile.ZipFile(pptx) as z:
  parts=slide_parts(z)
  if len(by)!=len(entries) or sorted(by)!=list(range(2,len(parts))):errors.append('构图清单必须覆盖全部正文页，页码不能重复或缺失')
  for i,part in enumerate(parts,1):
   root=E.fromstring(z.read(part));obs=shapes(z.read(part));body=[o for o in obs if o['position'] and 100<=o['position'][1]<666]
   boxes=[['text' if o['text'] else 'shape',*[round(v/8) for v in o['position']]] for o in body if o['position'][2]>3 and o['position'][3]>3]
   for n in root.findall('.//p:graphicFrame',NS):
    tr=n.find('p:xfrm',NS)
    if tr is not None:
     a=tr.find('a:off',NS);b=tr.find('a:ext',NS)
     boxes.append(['frame',*[round(int(v)/9525/8) for v in [a.get('x'),a.get('y'),b.get('cx'),b.get('cy')]]])
   sig=hashlib.sha256(json.dumps(sorted(boxes,key=str)).encode()).hexdigest();sigs.append(sig)
   rows.append({'slide':i,'family':by.get(i,{}).get('family'),'body_characters':sum(len(o['text']) for o in body),'text_boxes':sum(bool(o['text']) for o in body),'tables':len(root.findall('.//a:tbl',NS)),'charts':len(root.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/chart}chart')),'native_shapes':len(obs),'pictures':len(root.findall('.//p:pic',NS)),'geometry_signature':sig})
  families=[e.get('family') for e in entries]
  for i in range(len(entries)-1):
   a,b=entries[i:i+2]
   if a.get('family')==b.get('family') and not b.get('continuationReason'):warnings.append(f"第{a['slide']}、{b['slide']}页连续同构，实看学习连续性和内容负载；不要仅为换版式重排")
   if sigs[a['slide']-1]==sigs[b['slide']-1] and not b.get('continuationReason'):warnings.append(f"第{a['slide']}、{b['slide']}页正文原生几何完全重复，须复核是否为必要对照或套版")
  for i in range(len(entries)-3):
   f=families[i:i+4]
   if f[0]==f[2] and f[1]==f[3] and not all(e.get('continuationReason') for e in entries[i+1:i+4]):warnings.append(f"第{entries[i]['slide']}—{entries[i+3]['slide']}页存在ABAB重复，结合实际任务复核")
  for i in range(len(entries)-7):
   c=collections.Counter(families[i:i+8]);fam,count=c.most_common(1)[0]
   if count>4:warnings.append(f"第{entries[i]['slide']}—{entries[i+7]['slide']}页中，{fam}出现{count}次，须实看复核")
 times={}
 for e in entries:
  if e.get('lesson'):times[e['lesson']]=times.get(e['lesson'],0)+e.get('minutes',0)
 return {'ok':not errors,'slide_count':len(rows),'content_pages':len(entries),'layout_families':len(set(families)),'planned_minutes_by_lesson':times,'errors':errors,'warnings':warnings,'pages':rows,'scope':'原生文件与构图清单检查；不替代逐页、四至八页联排、教学和实际投影检查'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('pptx',type=Path);ap.add_argument('manifest',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=audit(a.pptx,json.loads(a.manifest.read_text()));v=json.dumps(r,ensure_ascii=False,indent=2)
 if a.output:a.output.write_text(v+'\n')
 print(json.dumps({k:v for k,v in r.items() if k!='pages'},ensure_ascii=False,indent=2));raise SystemExit(not r['ok'])
