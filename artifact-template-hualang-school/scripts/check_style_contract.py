#!/usr/bin/env python3
"""Check a saved full deck, or explicitly scoped content-only pages."""
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
 obs=shapes(z.read(part));valid=not added;detail=[];layout_profile='original'
 if contract and contract.get('allowAddedContent'):
  names=[o['name'] for o in obs]
  required=set(contract.get('requiredObjectNames',contract['allowedObjectNames']))
  optional=set(contract.get('optionalObjectNames',[]))
  valid=(required.issubset(names) and set(names).issubset(required|optional)
         and len(names)==len(set(names)) and len(added)==len(names))
  legacy=valid and bool(optional) and not optional.issubset(names)
  layout_profile='legacy' if legacy else 'current' if valid else 'invalid'
  for ob in obs:
   x,y,w,h=ob['position'] or [-1,-1,-1,-1]
   sx,sy,sw,sh=contract['safeArea']
   valid=valid and x>=sx and y>=sy and x+w<=sx+sw and y+h<=sy+sh
   if ob['name']=='closing-motto':valid=valid and ob['text']==contract['motto']
   if ob['name']=='closing-message':valid=valid and bool(ob['text'].strip())
   detail.append({'name':ob['name'],'text':ob['text']})
 return {'original_asset_present':expected_sha in hashes,'added_objects':added,'text':detail,'layout_profile':layout_profile,'passed':expected_sha in hashes and valid}


def full_bleed(raw, canvas=(1280,720), tol=2):
 """识别有主张和品牌标记的出血候选；不认证实际图像或视觉。"""
 root=E.fromstring(raw)
 W,H=canvas
 tree=root.find('p:cSld/p:spTree',NS)
 if tree is None:return False
 def box(node):
  tr=node.find('p:spPr/a:xfrm',NS)
  if tr is None:return None
  o=tr.find('a:off',NS);e=tr.find('a:ext',NS)
  if o is None or e is None:return None
  return tuple(int(v)/EMU for v in (o.get('x'),o.get('y'),e.get('cx'),e.get('cy')))
 def inside(b):
  return b is not None and b[2]>0 and b[3]>0 and b[0]>=-tol and b[1]>=-tol and b[0]+b[2]<=W+tol and b[1]+b[3]<=H+tol
 def covers(b):
  return b is not None and all(abs(a-bb)<=tol for a,bb in zip(b,(0,0,W,H)))
 def dark_fill(parent):
  if parent is None:return False
  fill=parent.find('a:solidFill/a:srgbClr',NS)
  if fill is None:return False
  value=fill.get('val','')
  if not re.fullmatch(r'[0-9A-Fa-f]{6}',value):return False
  alpha=fill.find('a:alpha',NS)
  if alpha is not None and int(alpha.get('val','100000'))<100000:return False
  rgb=[int(value[n:n+2],16) for n in (0,2,4)]
  return sum(a*b for a,b in zip(rgb,(.2126,.7152,.0722)))<140
 # A plain white/transparent backdrop is also common on framed pages. It is
 # not evidence that the page deliberately uses the far-distance exception.
 backdrop=dark_fill(root.find('p:cSld/p:bg/p:bgPr',NS))
 brand=False;headline=False
 for node in tree:
  b=box(node)
  if node.tag=='{'+NS['p']+'}pic':
   blip=node.find('p:blipFill/a:blip',NS)
   has_image=blip is not None and bool(blip.get('{'+NS['r']+'}embed'))
   nv=node.find('p:nvPicPr/p:cNvPr',NS)
   brand=brand or (has_image and inside(b) and nv is not None and nv.get('name')=='brand-mark')
   backdrop=backdrop or (has_image and covers(b))
  elif node.tag=='{'+NS['p']+'}sp':
   backdrop=backdrop or (covers(b) and dark_fill(node.find('p:spPr',NS)))
   text=''.join(t.text or '' for t in node.findall('.//a:t',NS)).strip()
   sizes=[int(n.get('sz')) for n in node.findall('.//a:rPr',NS) if n.get('sz')]
   headline=headline or (inside(b) and bool(re.search(r'[^\d\s/]',text)) and bool(sizes) and max(sizes)>=44*75)
 return bool(backdrop and brand and headline)

def check(pptx,c,title='',presenter='',date='',template=False,allow_titles=(),allow_subtitle=False,content_only=False):
 errors=[];warnings=[];headers=[]
 expected=None if content_only else {'title':title,'presenter':'汇报人：'+re.sub(r'^汇报人[：:]\s*','',presenter),'date':'汇报时间：'+re.sub(r'^汇报时间[：:]\s*','',date)}
 closing=None
 if not content_only and not all(str(v).strip() for v in (title,presenter,date)):errors.append('完整稿须提供题名、汇报人和日期')
 with zipfile.ZipFile(pptx) as z:
  parts=slide_parts(z)
  if not parts:errors.append('没有可检查的页面')
  if not content_only and parts:
   cover=shapes(z.read(parts[0]))
   for key,want_text in expected.items():
    rule=c['cover'][key];match=[o for o in cover if o['name']==rule['name']]
    if len(match)!=1:errors.append('封面固定字段缺失或重复：'+key);continue
    ob=match[0]
    if ob['text']!=want_text:errors.append('封面字段与要求不一致：'+key)
    if ob['position'] is None or any(abs(x-y)>1 for x,y in zip(ob['position'],[rule[k] for k in ['x','y','w','h']])):errors.append('封面字段位置错误：'+key)
    if not template and re.search(r'待补|待填|姓名或团队|按需填写|\[.+\]|［.+］',ob['text']):errors.append('正式封面仍有待补字段：'+key)
   if not allow_subtitle and any(o['name']=='cover-subtitle' and o['text'].strip() for o in cover):errors.append('封面存在未声明必要性的副题')
  body_parts=enumerate(parts,1) if content_only else enumerate(parts[1:-1],2)
  banned=[w for w in (c.get('bannedTerms') or [])]
  for number,part in body_parts:
   raw=z.read(part)
   bleed=full_bleed(raw)
   titles=[o for o in shapes(raw) if o['name'] in ['title','scene-title']]
   for ob in shapes(raw):
    for word in banned:
     if word and word in (ob['text'] or ''):
      warnings.append(f'第{number}页用词“{word}”需结合学科术语、引文及语境复核：{ob["text"][:30]}')
   if not titles and not bleed:errors.append(f'第{number}页缺少正文页标题或有效出血主张')
   if len(titles)>1:errors.append(f'第{number}页存在多个页标题')
   for ob in titles:
    t=ob['text'];headers.append({'slide':number,'title':t})
    if content_only and not bleed:
     frame=c.get('implementation',{}).get('bodyFrame',{}).get('title')
     if frame and (ob['position'] is None or any(abs(x-y)>1 for x,y in zip(ob['position'],[frame[k] for k in ['x','y','w','h']]))):errors.append(f'第{number}页正文题名位置不符合页眉框架')
    if t in allow_titles:continue
    units=len(re.findall(r'[\u3400-\u9fff]|[A-Za-z0-9]+',t))
    if not t.strip():errors.append(f'第{number}页题名为空')
    if re.search(r'[\u3400-\u9fff]',t):
     if any(re.search(pattern,t) for pattern in c['heading'].get('forbiddenPatterns',[])):errors.append(f'第{number}页自动题名为口播或问句：{t}')
     if any(re.search(pattern,t) for pattern in c['heading'].get('reviewPatterns',[])):warnings.append(f'第{number}页题名需人工复核具体对象及信息量；句式本身不作禁用依据：{t}')
     if units>c['heading']['maxUnits']:warnings.append(f'第{number}页题名较长，结合学科术语和实际换行复核：{t}')
  if not content_only and parts:
   closing=closing_check(z,parts[-1],c['closing']['assetSha256'],c['closing'])
   if not closing['passed']:errors.append('封尾原图、培养目标、结束语或安全区不符合规范')
   elif closing.get('layout_profile')=='legacy':warnings.append('封尾为历史合法两项文字样式；新稿采用现行居中样式，保留原底图。')
 scope='全部现有正文页的题名及其页眉位置；含画布齐边背景、原生主张大字和brand-mark的出血候选可无页眉；不要求封面、封尾、署名或日期，不认证校徽内容、金线或实际视觉' if content_only else '首尾、字段、位置及正文标题/出血候选；短中文题名为偏好，学科和英文题名按语义与实际换行复核；仍需人工检查内容、重复语义、密度和视觉'
 return {'ok':not errors,'content_only':content_only,'cover_expected':expected,'headings':headers,'closing':closing,'errors':errors,'warnings':warnings,'scope':scope}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('pptx',type=Path);ap.add_argument('--title',default='');ap.add_argument('--presenter',default='');ap.add_argument('--date',default='');ap.add_argument('--content-only',action='store_true',help='仅检查文件中现有正文页的题名和页眉位置，不要求首尾、署名日期');ap.add_argument('--contract',type=Path,default=Path(__file__).resolve().parents[1]/'assets/style-contract.json');ap.add_argument('--template',action='store_true');ap.add_argument('--allow-title',action='append',default=[]);ap.add_argument('--allow-subtitle',action='store_true');a=ap.parse_args()
 if not a.content_only and not all(v.strip() for v in (a.title,a.presenter,a.date)):ap.error('完整稿必须提供--title、--presenter和--date；仅正文文件须显式使用--content-only')
 result=check(a.pptx,json.loads(a.contract.read_text()),a.title,a.presenter,a.date,a.template,a.allow_title,a.allow_subtitle,a.content_only)
 print(json.dumps(result,ensure_ascii=False,indent=2));return int(not result['ok'])
if __name__=='__main__':sys.exit(main())
