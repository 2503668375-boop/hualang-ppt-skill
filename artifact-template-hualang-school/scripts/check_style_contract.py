#!/usr/bin/env python3
"""Check fixed cover, single page headings and original closing in a saved deck."""
import argparse,hashlib,json,posixpath,re,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
EMU=9525

def shapes(raw):
 root=E.fromstring(raw);out=[]
 for sp in root.findall('.//p:sp',NS):
  nv=sp.find('p:nvSpPr/p:cNvPr',NS);tr=sp.find('p:spPr/a:xfrm',NS);pos=None
  if tr is not None:
   o=tr.find('a:off',NS);e=tr.find('a:ext',NS)
   if o is not None and e is not None:pos=[int(o.get('x'))/EMU,int(o.get('y'))/EMU,int(e.get('cx'))/EMU,int(e.get('cy'))/EMU]
  out.append({'name':nv.get('name','') if nv is not None else '', 'text':''.join(t.text or '' for t in sp.findall('.//a:t',NS)), 'position':pos})
 return out

def relationships(z,part):
 name=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
 if name not in z.namelist():return []
 out=[]
 for rel in E.fromstring(z.read(name)):
  if rel.get('TargetMode')=='External':continue
  target=rel.get('Target');dest=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part),target))
  out.append((rel.get('Id'),rel.get('Type').rsplit('/',1)[-1],dest))
 return out

def slide_parts(z):
 rel={rid:dest for rid,typ,dest in relationships(z,'ppt/presentation.xml') if typ=='slide'}
 return [rel[s.get('{'+NS['r']+'}id')] for s in E.fromstring(z.read('ppt/presentation.xml')).find('p:sldIdLst',NS)]

def closing_check(z,part,expected_sha,contract=None):
 root=E.fromstring(z.read(part));tree=root.find('p:cSld/p:spTree',NS)
 added=[n.tag.rsplit('}',1)[-1] for n in tree if n.tag.rsplit('}',1)[-1] not in ['nvGrpSpPr','grpSpPr']]
 seen=set();hashes=[]
 def walk(p):
  if p in seen:return
  seen.add(p)
  for rid,typ,dest in relationships(z,p):
   if typ=='image':hashes.append(hashlib.sha256(z.read(dest)).hexdigest())
   elif typ in ['slideLayout','slideMaster']:walk(dest)
 walk(part)
 obs=shapes(z.read(part));valid=not added;detail=[]
 if contract and contract.get('allowAddedContent'):
  names=[o['name'] for o in obs];valid=sorted(names)==sorted(contract['allowedObjectNames']) and len(added)==2
  for ob in obs:
   x,y,w,h=ob['position'] or [-1,-1,-1,-1]
   sx,sy,sw,sh=contract['safeArea']
   valid=valid and x>=sx and y>=sy and x+w<=sx+sw and y+h<=sy+sh
   if ob['name']=='closing-motto':valid=valid and ob['text']==contract['motto']
   if ob['name']=='closing-message':valid=valid and bool(ob['text'].strip())
   detail.append({'name':ob['name'],'text':ob['text']})
 return {'original_asset_present':expected_sha in hashes,'added_objects':added,'text':detail,'passed':expected_sha in hashes and valid}

def check(pptx,c,title,presenter,date,template=False,allow_titles=(),allow_subtitle=False):
 errors=[];warnings=[];headers=[]
 expected={'title':title,'presenter':'汇报人：'+re.sub(r'^汇报人[：:]\s*','',presenter),'date':'汇报时间：'+re.sub(r'^汇报时间[：:]\s*','',date)}
 with zipfile.ZipFile(pptx) as z:
  parts=slide_parts(z);cover=shapes(z.read(parts[0]))
  for key,want_text in expected.items():
   rule=c['cover'][key];match=[o for o in cover if o['name']==rule['name']]
   if len(match)!=1:errors.append('封面固定字段缺失或重复：'+key);continue
   ob=match[0]
   if ob['text']!=want_text:errors.append('封面字段与要求不一致：'+key)
   if ob['position'] is None or any(abs(x-y)>1 for x,y in zip(ob['position'],[rule[k] for k in ['x','y','w','h']])):errors.append('封面字段位置错误：'+key)
   if not template and re.search(r'待补|待填|姓名或团队|按需填写|\[.+\]|［.+］',ob['text']):errors.append('正式封面仍有待补字段：'+key)
  if not allow_subtitle and any(o['name']=='cover-subtitle' and o['text'].strip() for o in cover):errors.append('封面存在未声明必要性的副题')
  for number,part in enumerate(parts[1:-1],2):
   titles=[o for o in shapes(z.read(part)) if o['name'] in ['title','scene-title']]
   if len(titles)>1:errors.append(f'第{number}页存在多个页标题')
   for ob in titles:
    t=ob['text'];headers.append({'slide':number,'title':t})
    if t in allow_titles:continue
    units=len(re.findall(r'[\u3400-\u9fff]|[A-Za-z0-9]+',t))
    if not t.strip():errors.append(f'第{number}页题名为空')
    if re.search(r'[\u3400-\u9fff]',t):
     if any(re.search(pattern,t) for pattern in c['heading'].get('forbiddenPatterns',[])):errors.append(f'第{number}页自动题名为口播或问句：{t}')
     if any(re.search(pattern,t) for pattern in c['heading'].get('reviewPatterns',[])):warnings.append(f'第{number}页题名需人工复核具体对象及信息量；句式本身不作禁用依据：{t}')
     if units>c['heading']['maxUnits']:warnings.append(f'第{number}页题名较长，结合学科术语和实际换行复核：{t}')
  closing=closing_check(z,parts[-1],c['closing']['assetSha256'],c['closing'])
  if not closing['passed']:errors.append('封尾原图、培养目标、结束语或安全区不符合规范')
 return {'ok':not errors,'cover_expected':expected,'headings':headers,'closing':closing,'errors':errors,'warnings':warnings,'scope':'首尾、字段、位置及已命名标题；短中文题名为偏好，学科和英文题名按语义与实际换行复核；仍需人工检查内容、重复语义、密度和视觉'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('pptx',type=Path);ap.add_argument('--title',required=True);ap.add_argument('--presenter',required=True);ap.add_argument('--date',required=True);ap.add_argument('--contract',type=Path,default=Path(__file__).resolve().parents[1]/'assets/style-contract.json');ap.add_argument('--template',action='store_true');ap.add_argument('--allow-title',action='append',default=[]);ap.add_argument('--allow-subtitle',action='store_true');a=ap.parse_args()
 result=check(a.pptx,json.loads(a.contract.read_text()),a.title,a.presenter,a.date,a.template,a.allow_title,a.allow_subtitle)
 print(json.dumps(result,ensure_ascii=False,indent=2));return int(not result['ok'])
if __name__=='__main__':sys.exit(main())
