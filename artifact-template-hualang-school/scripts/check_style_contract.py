#!/usr/bin/env python3
"""Read fixed cover fields and generated topic headings from an actual PPTX."""
import argparse,json,re,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
EMU=9525

def shapes(raw):
 root=E.fromstring(raw);out=[]
 for sp in root.findall('.//p:sp',NS):
  nv=sp.find('p:nvSpPr/p:cNvPr',NS);tr=sp.find('p:spPr/a:xfrm',NS)
  pos=None
  if tr is not None:
   o=tr.find('a:off',NS);e=tr.find('a:ext',NS)
   if o is not None and e is not None:pos=[int(o.get('x'))/EMU,int(o.get('y'))/EMU,int(e.get('cx'))/EMU,int(e.get('cy'))/EMU]
  out.append({'name':nv.get('name','') if nv is not None else '', 'text':''.join(t.text or '' for t in sp.findall('.//a:t',NS)), 'position':pos})
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('pptx',type=Path);ap.add_argument('--title',required=True);ap.add_argument('--presenter',required=True);ap.add_argument('--date',required=True);ap.add_argument('--contract',type=Path,default=Path(__file__).resolve().parents[1]/'assets/style-contract.json');ap.add_argument('--template',action='store_true');ap.add_argument('--allow-title',action='append',default=[]);a=ap.parse_args()
 c=json.loads(a.contract.read_text());errors=[];headers=[]
 with zipfile.ZipFile(a.pptx) as z:
  cover=shapes(z.read('ppt/slides/slide1.xml'))
  expected={'title':a.title,'presenter':'汇报人：'+re.sub(r'^汇报人[：:]\s*','',a.presenter),'date':'汇报时间：'+re.sub(r'^汇报时间[：:]\s*','',a.date)}
  for key in expected:
   rule=c['cover'][key];match=[x for x in cover if x['name']==rule['name']]
   if len(match)!=1:errors.append('封面固定字段缺失或重复：'+key);continue
   ob=match[0]
   if ob['text']!=expected[key]:errors.append('封面字段与本次要求不一致：'+key)
   want=[rule[k] for k in ['x','y','w','h']]
   if ob['position'] is None or any(abs(x-y)>1 for x,y in zip(ob['position'],want)):errors.append('封面字段偏离固定区域：'+key)
   if not a.template and re.search(r'待补|待填|姓名或团队|按需填写|\[.+\]|［.+］',ob['text']):errors.append('正式封面仍含待补字段：'+key)
  slide_names=sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)),key=lambda x:int(re.search(r'slide(\d+)',x).group(1)))
  for number,n in enumerate(slide_names[1:],2):
   for ob in shapes(z.read(n)):
    if ob['name'] not in ['title','scene-title']:continue
    t=ob['text'];headers.append({'slide':number,'title':t})
    if t in a.allow_title:continue
    units=len(re.findall(r'[\u3400-\u9fff]|[A-Za-z0-9]+',t))
    if units>c['heading']['maxUnits'] or re.search(r'[：:？?，,；;]',t) or any(re.search(p,t) for p in c['heading']['forbiddenPatterns']):errors.append(f'第{number}页题名不符合短题名规范：{t}')
 result={'ok':not errors,'cover_expected':expected,'headings':headers,'errors':errors,'scope':'字段、位置及题名检查；不替代事实、排版与视觉审查'}
 print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
