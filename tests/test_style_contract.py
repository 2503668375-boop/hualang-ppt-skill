import copy,importlib.util,json,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from xml.etree import ElementTree as E
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'artifact-template-hualang-school'
spec=importlib.util.spec_from_file_location('contract',S/'scripts/check_style_contract.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name);self.source=S/'assets/reference.pptx';self.rules=json.loads((S/'assets/style-contract.json').read_text())
 def tearDown(self):self.tmp.cleanup()
 def check(self,p):return m.check(p,self.rules,'汇报主题','姓名或团队','日期待填',template=True)
 def edit(self,name,part_index,fn,source=None):
  dst=self.dir/name
  with zipfile.ZipFile(source or self.source) as z:
   parts=m.slide_parts(z);part=parts[part_index];root=E.fromstring(z.read(part));fn(root)
   with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as out:
    for entry in z.infolist():out.writestr(entry,E.tostring(root) if entry.filename==part else z.read(entry.filename))
  return dst
 def content_fixture(self):
  """Retain two real body slides; do not synthesize cover-shaped placeholders."""
  src=S/'assets/design-craft-v9.2.pptx';dst=self.dir/'content-only.pptx'
  with zipfile.ZipFile(src) as z:
   root=E.fromstring(z.read('ppt/presentation.xml'));listing=root.find('p:sldIdLst',m.NS)
   for slide in list(listing)[2:]:listing.remove(slide)
   with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as out:
    for entry in z.infolist():out.writestr(entry,E.tostring(root) if entry.filename=='ppt/presentation.xml' else z.read(entry.filename))
  return dst
 def test_actual_brand_template(self):self.assertTrue(self.check(self.source)['ok'])
 def test_content_only_accepts_actual_two_page_body_without_cover_fields(self):
  fixture=self.content_fixture();result=m.check(fixture,self.rules,content_only=True)
  self.assertTrue(result['ok'],result['errors'])
  self.assertTrue(result['content_only'])
  self.assertIsNone(result['cover_expected']);self.assertIsNone(result['closing'])
  self.assertEqual([row['slide'] for row in result['headings']],[1,2])
  run=subprocess.run([sys.executable,str(S/'scripts/check_style_contract.py'),str(fixture),'--content-only'],capture_output=True,text=True)
  self.assertEqual(run.returncode,0,run.stderr+run.stdout)
  self.assertTrue(json.loads(run.stdout)['content_only'])
 def test_content_only_checks_first_and_last_body_header_positions(self):
  fixture=self.content_fixture()
  def move(root):
   for sp in root.findall('.//p:sp',m.NS):
    nv=sp.find('p:nvSpPr/p:cNvPr',m.NS)
    if nv is not None and nv.get('name') in ['title','scene-title']:sp.find('p:spPr/a:xfrm/a:off',m.NS).set('x',str(840*m.EMU))
  for index in (0,1):
   with self.subTest(slide=index+1):
    modified=self.edit(f'body-position-{index}.pptx',index,move,source=fixture)
    result=m.check(modified,self.rules,content_only=True)
    self.assertFalse(result['ok'])
    self.assertTrue(any(f'第{index+1}页正文题名位置' in message for message in result['errors']))
 def test_default_full_deck_mode_still_rejects_missing_cover_fields(self):
  fixture=self.content_fixture()
  result=m.check(fixture,self.rules,'正式汇报','示例工作组','2026年11月8日')
  self.assertFalse(result['ok'])
  self.assertTrue(any('封面固定字段缺失' in message for message in result['errors']))
  run=subprocess.run([sys.executable,str(S/'scripts/check_style_contract.py'),str(fixture)],capture_output=True,text=True)
  self.assertNotEqual(run.returncode,0)
  self.assertIn('完整稿必须提供',run.stderr)
 def test_date_cannot_return_to_seam(self):
  def move(root):
   for sp in root.findall('.//p:sp',m.NS):
    nv=sp.find('p:nvSpPr/p:cNvPr',m.NS)
    if nv is not None and nv.get('name')=='cover-date':sp.find('p:spPr/a:xfrm/a:off',m.NS).set('x',str(940*m.EMU))
  self.assertFalse(self.check(self.edit('date.pptx',0,move))['ok'])
 def test_extra_cover_subtitle_is_rejected(self):
  def add(root):
   tree=root.find('p:cSld/p:spTree',m.NS);sp=copy.deepcopy(root.find('.//p:sp',m.NS));sp.find('p:nvSpPr/p:cNvPr',m.NS).set('name','cover-subtitle');tree.append(sp)
  self.assertFalse(self.check(self.edit('subtitle.pptx',0,add))['ok'])
 def test_custom_content_cannot_replace_closing(self):
  def add(root):
   tree=root.find('p:cSld/p:spTree',m.NS);E.SubElement(tree,'{'+m.NS['p']+'}sp')
  r=self.check(self.edit('closing.pptx',-1,add));self.assertFalse(r['closing']['passed'])
 def test_duplicate_page_heading(self):
  def add(root):
   tree=root.find('p:cSld/p:spTree',m.NS);tree.append(copy.deepcopy(root.find('.//p:sp',m.NS)))
  self.assertFalse(self.check(self.edit('duplicate.pptx',1,add))['ok'])
 def heading(self,title):
  def change(root):
   for sp in root.findall('.//p:sp',m.NS):
    nv=sp.find('p:nvSpPr/p:cNvPr',m.NS)
    if nv is not None and nv.get('name') in ['title','scene-title']:
     texts=sp.findall('.//a:t',m.NS)
     for index,t in enumerate(texts):t.text=title if index==0 else ''
  return self.edit('heading.pptx',1,change)
 def test_concrete_start_title_requests_review_without_rejection(self):
  r=self.check(self.heading('从一条请求开始'))
  self.assertTrue(r['ok'],r['errors'])
  self.assertTrue(any('人工复核' in text for text in r['warnings']))
 def test_question_heading_remains_rejected(self):
  self.assertFalse(self.check(self.heading('怎么制作课件'))['ok'])
 def test_legitimate_term_is_reviewed_not_blindly_banned(self):
  self.rules['bannedTerms']=['闭环']
  result=self.check(self.heading('闭环电路'))
  self.assertTrue(result['ok'],result['errors'])
  self.assertTrue(any('闭环' in message for message in result['warnings']))
 def test_heading_rules_come_from_contract(self):
  self.rules['heading']['forbiddenPatterns']=['^具体标题$']
  self.assertFalse(self.check(self.heading('具体标题'))['ok'])
  self.assertTrue(self.check(self.heading('怎么制作课件'))['ok'])
 def test_cross_tool_units_match_actual_template(self):
  with zipfile.ZipFile(self.source) as z:
   root=E.fromstring(z.read('ppt/presentation.xml'))
   size=root.find('p:sldSz',m.NS)
  impl=self.rules['implementation'];units=impl['unitConversion']
  self.assertEqual(int(size.get('cx')),impl['slideSizeEmu']['width'])
  self.assertEqual(int(size.get('cy')),impl['slideSizeEmu']['height'])
  for dimension in ('width','height'):
   self.assertEqual(impl['slideSizeEmu'][dimension]/self.rules['canvas'][dimension],units['emuPerLogicalPx'])
  self.assertEqual(units['emuPerLogicalPx']/units['emuPerPt'],units['ptPerLogicalPx'])

 def bleed_xml(self, fill='403653', picture=False, position=(0,0,1280,720),
               brand=True, headline=True, background=False):
  p,a,r=(m.NS[k] for k in ('p','a','r'))
  root=E.Element('{'+p+'}sld');slide=E.SubElement(root,'{'+p+'}cSld')
  def solid(parent,color):
   sf=E.SubElement(parent,'{'+a+'}solidFill')
   return E.SubElement(sf,'{'+a+'}srgbClr',val=color)
  if background:
   solid(E.SubElement(E.SubElement(slide,'{'+p+'}bg'),'{'+p+'}bgPr'),fill)
  tree=E.SubElement(slide,'{'+p+'}spTree')
  def shape(tag,name,bounds):
   node=E.SubElement(tree,'{'+p+'}'+tag)
   nv=E.SubElement(node,'{'+p+'}'+('nvPicPr' if tag=='pic' else 'nvSpPr'))
   E.SubElement(nv,'{'+p+'}cNvPr',id=str(len(tree)),name=name)
   sp=E.SubElement(node,'{'+p+'}spPr');tr=E.SubElement(sp,'{'+a+'}xfrm')
   x,y,w,h=bounds
   E.SubElement(tr,'{'+a+'}off',x=str(int(x*m.EMU)),y=str(int(y*m.EMU)))
   E.SubElement(tr,'{'+a+'}ext',cx=str(int(w*m.EMU)),cy=str(int(h*m.EMU)))
   if tag=='pic':
    blip=E.SubElement(E.SubElement(node,'{'+p+'}blipFill'),'{'+a+'}blip')
    blip.set('{'+r+'}embed','rId1')
   return node,sp
  if not background:
   node,sp=shape('pic' if picture else 'sp','backdrop',position)
   if not picture:
    rgb=solid(sp,fill)
    if fill=='FFFFFF':E.SubElement(rgb,'{'+a+'}alpha',val='0')
  if brand:shape('pic','brand-mark',(148,44,132,78))
  if headline:
   node,_=shape('sp','lead',(148,176,600,190))
   paragraph=E.SubElement(E.SubElement(node,'{'+p+'}txBody'),'{'+a+'}p')
   run=E.SubElement(paragraph,'{'+a+'}r')
   E.SubElement(run,'{'+a+'}rPr',sz='4800')
   E.SubElement(run,'{'+a+'}t').text='让思考清晰可见'
  return E.tostring(root)

 def test_bleed_accepts_branded_picture_and_dark_background_with_headline(self):
  self.assertTrue(m.full_bleed(self.bleed_xml(picture=True)))
  self.assertTrue(m.full_bleed(self.bleed_xml()))
  self.assertTrue(m.full_bleed(self.bleed_xml(background=True)))

 def test_blank_or_transparent_full_page_shape_cannot_bypass_title(self):
  self.assertFalse(m.full_bleed(self.bleed_xml(fill='FDFDFE')))
  self.assertFalse(m.full_bleed(self.bleed_xml(fill='FFFFFF')))
  self.assertFalse(m.full_bleed(self.bleed_xml(brand=False)))
  self.assertFalse(m.full_bleed(self.bleed_xml(headline=False)))
  raw=self.bleed_xml(fill='FDFDFE')
  def replace(root):
   root.clear();new=E.fromstring(raw)
   root.extend(list(new))
  fixture=self.edit('blank-background.pptx',0,replace,source=self.content_fixture())
  result=m.check(fixture,self.rules,content_only=True)
  self.assertFalse(result['ok'])
  self.assertTrue(any('第1页缺少正文页标题' in error for error in result['errors']))

 def test_small_shifted_or_oversized_picture_is_not_a_bleed_exception(self):
  for bounds in [(0,0,100,100),(-1000,-1000,1280,720),(0,0,2560,1440),(10,0,1280,720)]:
   with self.subTest(bounds=bounds):
    self.assertFalse(m.full_bleed(self.bleed_xml(picture=True,position=bounds)))
if __name__=='__main__':unittest.main()
