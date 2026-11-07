import copy,importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
from xml.etree import ElementTree as E
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'artifact-template-hualang-school'
spec=importlib.util.spec_from_file_location('contract',S/'scripts/check_style_contract.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name);self.source=S/'assets/reference.pptx';self.rules=json.loads((S/'assets/style-contract.json').read_text())
 def tearDown(self):self.tmp.cleanup()
 def check(self,p):return m.check(p,self.rules,'汇报主题','姓名或团队','日期待填',template=True)
 def edit(self,name,part_index,fn):
  dst=self.dir/name
  with zipfile.ZipFile(self.source) as z:
   parts=m.slide_parts(z);part=parts[part_index];root=E.fromstring(z.read(part));fn(root)
   with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as out:
    for entry in z.infolist():out.writestr(entry,E.tostring(root) if entry.filename==part else z.read(entry.filename))
  return dst
 def test_actual_brand_template(self):self.assertTrue(self.check(self.source)['ok'])
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
if __name__=='__main__':unittest.main()
