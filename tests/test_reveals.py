"""Functional checks for answer visibility, targets, ordering and refusal paths."""
import copy
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reveals',ROOT/'artifact-template-hualang-school/scripts/apply_reveals.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RevealTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name)
        self.base=self.dir/'base.pptx'
        P,A,R=m.P,m.A,m.R
        slide=f'''<p:sld xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree>
        <p:sp><p:nvSpPr><p:cNvPr id="2" name="stem"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>完整题干</a:t></a:r></a:p></p:txBody></p:sp>
        <p:sp><p:nvSpPr><p:cNvPr id="3" name="alpha"/></p:nvSpPr></p:sp>
        <p:sp><p:nvSpPr><p:cNvPr id="4" name="beta"/></p:nvSpPr></p:sp>
        <p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="5" name="curve"/></p:nvGraphicFramePr></p:graphicFrame>
        </p:spTree></p:cSld></p:sld>'''
        with zipfile.ZipFile(self.base,'w') as z:
            z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="256" r:id="second"/><p:sldId id="257" r:id="first"/></p:sldIdLst></p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="first" Target="slides/slide1.xml"/><Relationship Id="second" Target="slides/slide2.xml"/></Relationships>')
            z.writestr('ppt/slides/slide1.xml',slide);z.writestr('ppt/slides/slide2.xml',slide)
            z.writestr('untouched.bin',b'preserve byte-for-byte')
        self.plan={'schemaVersion':1,'effect':'appear','slides':[{'slide':1,'steps':[{'objects':['alpha','beta']},{'objects':['curve']}]}]}
    def tearDown(self):self.tmp.cleanup()
    def read(self,p):
        with zipfile.ZipFile(p) as z:return E.fromstring(z.read('ppt/slides/slide2.xml'))
    def test_click_groups_and_native_chart(self):
        out=self.dir/'animated.pptx';m.transform(self.base,out,self.plan)
        r=self.read(out);ns=m.NS
        self.assertEqual(len(r.findall('.//p:cTn[@nodeType="clickEffect"]',ns)),2)
        self.assertEqual(len(r.findall('.//p:cTn[@nodeType="withEffect"]',ns)),1)
        self.assertEqual([x.get('spid') for x in r.findall('.//p:set/p:cBhvr/p:tgtEl/p:spTgt',ns)],['3','4','5'])
        self.assertIsNotNone(r.find('.//p:bldGraphic[@spid="5"]/p:bldAsOne',ns))
        with zipfile.ZipFile(self.base) as a,zipfile.ZipFile(out) as b:
            self.assertEqual(a.read('ppt/slides/slide1.xml'),b.read('ppt/slides/slide1.xml'))
            self.assertEqual(a.read('untouched.bin'),b.read('untouched.bin'))
    def test_initial_intermediate_and_complete(self):
        for k,want in [(0,{'stem'}),(1,{'stem','alpha','beta'}),(2,{'stem','alpha','beta','curve'})]:
            out=self.dir/f'state-{k}.pptx';m.transform(self.base,out,self.plan,k)
            r=self.read(out);self.assertEqual({x.get('name') for x in r.findall('.//p:cNvPr',m.NS)},want)
            self.assertIsNone(r.find('p:timing',m.NS))
    def test_missing_duplicate_and_invalid_slide(self):
        for name,change in [('missing',lambda p:p['slides'][0]['steps'][0]['objects'].append('absent')),
                            ('duplicate',lambda p:p['slides'][0]['steps'][1]['objects'].append('alpha')),
                            ('slide',lambda p:p['slides'][0].update(slide=3))]:
            plan=copy.deepcopy(self.plan);change(plan);out=self.dir/(name+'.pptx')
            with self.assertRaises(ValueError):m.transform(self.base,out,plan)
            self.assertFalse(out.exists())
    def test_refuses_overwrite_and_existing_animation(self):
        with self.assertRaises(ValueError):m.transform(self.base,self.base,self.plan)
        out=self.dir/'once.pptx';m.transform(self.base,out,self.plan)
        with self.assertRaises(ValueError):m.transform(self.base,out,self.plan)
        with self.assertRaises(ValueError):m.transform(out,self.dir/'twice.pptx',self.plan)

if __name__=='__main__':unittest.main()
