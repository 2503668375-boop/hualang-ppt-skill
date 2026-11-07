"""Saved editable image reservations and original-position image fill."""
import json
import os
from pathlib import Path
import posixpath
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as E
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

class ImageSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node,modules=os.environ.get('HUALANG_NODE'),os.environ.get('HUALANG_NODE_MODULES')
        if not node or not modules:raise unittest.SkipTest('Set discovered HUALANG_NODE and HUALANG_NODE_MODULES.')
        cls.temp=tempfile.TemporaryDirectory(prefix='hualang-image-slot-');cls.addClassCleanup(cls.temp.cleanup)
        cls.work=Path(cls.temp.name)
        shutil.copy2(ROOT/'artifact-template-hualang-school/scripts/hualang-kit.mjs',cls.work/'hualang-kit.mjs')
        shutil.copy2(Path(__file__).with_name('image-slot-fixture.mjs'),cls.work/'fixture.mjs')
        (cls.work/'node_modules').symlink_to(modules,target_is_directory=True)
        run=subprocess.run([node,str(cls.work/'fixture.mjs'),str(ROOT/'artifact-template-hualang-school'),str(cls.work)],
                           capture_output=True,text=True,timeout=180)
        if run.returncode:raise AssertionError(run.stdout+run.stderr)
        cls.result=json.loads((cls.work/'result.json').read_text())
        with zipfile.ZipFile(cls.work/'image-slot.pptx') as z:
            rels=E.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
            mapping={r.get('Id'):r.get('Target') for r in rels}
            ids=E.fromstring(z.read('ppt/presentation.xml')).findall('p:sldIdLst/p:sldId',NS)
            parts=[]
            for item in ids:
                target=mapping[item.get('{'+NS['r']+'}id')]
                parts.append(target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/'+target))
            cls.slot_page=E.fromstring(z.read(parts[1]));cls.filled_page=E.fromstring(z.read(parts[2]))
        retain=os.environ.get('HUALANG_TEST_OUTPUT')
        if retain:
            dst=Path(retain)/'image-slot';dst.mkdir(parents=True,exist_ok=True)
            for name in ['image-slot.pptx','result.json']:shutil.copy2(cls.work/name,dst/name)
            shutil.copytree(cls.work/'render',dst/'render',dirs_exist_ok=True)
            def relocate(value):
                if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
                if isinstance(value,list):return [relocate(v) for v in value]
                if isinstance(value,str) and value.startswith(str(cls.work)+os.sep):return str(dst/value[len(str(cls.work))+1:])
                return value
            for file in [dst/'result.json',*dst.rglob('render-manifest.json')]:
                file.write_text(json.dumps(relocate(json.loads(file.read_text())),ensure_ascii=False,indent=2))

    def box(self,shape):
        transform=shape.find('p:spPr/a:xfrm',NS)
        off,ext=transform.find('a:off',NS),transform.find('a:ext',NS)
        return tuple(int(v)/9525 for v in [off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy')])

    def slot(self,prefix):
        return {shape.find('p:nvSpPr/p:cNvPr',NS).get('name'):shape
                for shape in self.slot_page.findall('.//p:sp',NS)
                if shape.find('p:nvSpPr/p:cNvPr',NS).get('name','').startswith(prefix+'-')}

    def test_landscape_and_portrait_frames_preserve_requested_geometry(self):
        for name,expected in [('landscape',(48,190,720,405)),('portrait',(840,150,344,468))]:
            shapes=self.slot(name)
            self.assertEqual(len(shapes),4)
            self.assertEqual(self.box(shapes[name+'-frame']),expected)
            self.assertEqual(shapes[name+'-frame'].find('p:spPr/a:prstGeom',NS).get('prst'),'rect')
            self.assertEqual(self.result[name]['objects'],4)

    def test_missing_status_and_brief_are_editable_and_inside_frame(self):
        for name in ['landscape','portrait']:
            shapes=self.slot(name);x,y,w,h=self.box(shapes[name+'-frame'])
            status=''.join(t.text or '' for t in shapes[name+'-status'].findall('.//a:t',NS))
            self.assertEqual(status,'待补图片')
            for suffix in ['status','title','brief']:
                shape=shapes[name+'-'+suffix]
                self.assertTrue(shape.findall('.//a:t',NS))
                bx,by,bw,bh=self.box(shape)
                self.assertGreaterEqual(bx,x);self.assertGreaterEqual(by,y)
                self.assertLessEqual(bx+bw,x+w+.01);self.assertLessEqual(by+bh,y+h+.01)
            self.assertIsNone(shapes[name+'-frame'].find('.//a:blip',NS))
            self.assertIsNone(shapes[name+'-frame'].find('.//a:custGeom',NS))

    def test_returned_frame_can_place_a_real_image_at_identical_position(self):
        self.assertEqual(self.result['landscape']['frame'],{'x':48,'y':190,'w':720,'h':405})
        self.assertEqual(self.result['landscape']['fit'],'cover')
        self.assertEqual(self.result['portrait']['fit'],'contain')
        pictures=self.filled_page.findall('.//p:pic',NS)
        self.assertTrue(any(self.box(p)==(48,190,720,405) for p in pictures))

    def test_invalid_inputs_fail_before_creating_partial_slot(self):
        self.assertEqual(len(self.result['rejected']),10)
        self.assertTrue(all(item['threw'] and item['unchanged'] for item in self.result['rejected']),self.result['rejected'])

if __name__=='__main__':unittest.main()
