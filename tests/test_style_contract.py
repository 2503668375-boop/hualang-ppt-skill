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
if __name__=='__main__':unittest.main()
