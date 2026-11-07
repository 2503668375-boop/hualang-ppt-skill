"""Saved native geometry for configurable bands and deliberate leader routing."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as E
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}

class ComponentDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node,modules=os.environ.get('HUALANG_NODE'),os.environ.get('HUALANG_NODE_MODULES')
        if not node or not modules:raise unittest.SkipTest('Set discovered HUALANG_NODE and HUALANG_NODE_MODULES.')
        cls.temp=tempfile.TemporaryDirectory(prefix='hualang-component-detail-');cls.addClassCleanup(cls.temp.cleanup)
        cls.work=Path(cls.temp.name)
        shutil.copy2(ROOT/'artifact-template-hualang-school/scripts/hualang-kit.mjs',cls.work/'hualang-kit.mjs')
        shutil.copy2(Path(__file__).with_name('component-detail-fixture.mjs'),cls.work/'fixture.mjs')
        (cls.work/'node_modules').symlink_to(modules,target_is_directory=True)
        result=subprocess.run([node,str(cls.work/'fixture.mjs'),str(ROOT/'artifact-template-hualang-school'),str(cls.work)],capture_output=True,text=True,timeout=180)
        if result.returncode:raise AssertionError(result.stdout+result.stderr)
        cls.result=json.loads((cls.work/'result.json').read_text())
        with zipfile.ZipFile(cls.work/'component-detail.pptx') as z:
            cls.pages=[E.fromstring(z.read(f'ppt/slides/slide{i}.xml')) for i in (2,3,4,5,6)]
        retain=os.environ.get('HUALANG_TEST_OUTPUT')
        if retain:
            dst=Path(retain)/'component-details';dst.mkdir(parents=True,exist_ok=True)
            for name in ['component-detail.pptx','result.json']:shutil.copy2(cls.work/name,dst/name)
            shutil.copytree(cls.work/'render',dst/'render',dirs_exist_ok=True)
            def relocated(value):
                if isinstance(value,dict):return {k:relocated(v) for k,v in value.items()}
                if isinstance(value,list):return [relocated(v) for v in value]
                if isinstance(value,str) and value.startswith(str(cls.work)+os.sep):return str(dst/value[len(str(cls.work))+1:])
                return value
            for file in [dst/'result.json',*dst.rglob('render-manifest.json')]:
                file.write_text(json.dumps(relocated(json.loads(file.read_text())),ensure_ascii=False,indent=2))

    def box(self,s):
        t=s.find('p:spPr/a:xfrm',NS);o,e=t.find('a:off',NS),t.find('a:ext',NS)
        return tuple(int(v)/9525 for v in [o.get('x'),o.get('y'),e.get('cx'),e.get('cy')])

    def named(self,page,name):
        return next(s for s in self.pages[page].findall('.//p:sp',NS) if s.find('p:nvSpPr/p:cNvPr',NS).get('name')==name)

    def paths(self,page):
        result=[]
        for s in self.pages[page].findall('.//p:sp',NS):
            p=s.find('p:spPr/a:custGeom/a:pathLst/a:path',NS)
            if p is None:continue
            x,y,w,h=self.box(s)
            result.append([(x+int(n.get('x'))/int(p.get('w'))*w,y+int(n.get('y'))/int(p.get('h'))*h) for n in p.findall('.//a:pt',NS)])
        return result

    def test_long_labels_have_explicit_space_and_multiline_height(self):
        label=self.box(self.named(0,'method-strip-label'));body=self.box(self.named(0,'method-strip-body'));bg=self.box(self.named(0,'method-strip-background'))
        self.assertEqual(label[2],210)
        self.assertAlmostEqual(body[0]-(label[0]+label[2]),28)
        self.assertEqual(label[1],body[1])
        self.assertGreaterEqual(body[3],2*24*1.2)
        self.assertAlmostEqual(bg[1]+bg[3]-(body[1]+body[3]),16)
        lesson=self.box(self.named(0,'lesson-band-label'));task=self.box(self.named(0,'lesson-band-body'))
        self.assertEqual(lesson[2],108)
        self.assertGreaterEqual(task[3],2*25*1.2)
        self.assertGreater(task[0],lesson[0]+lesson[2])

    def test_default_callout_lands_at_title_line_and_explicit_route_is_orthogonal(self):
        paths=self.paths(1)
        self.assertEqual(len(paths),6)
        for line in paths:
            self.assertTrue(abs(line[0][0]-line[1][0])<.001 or abs(line[0][1]-line[1][1])<.001)
        self.assertAlmostEqual(paths[2][-1][0],820)
        self.assertAlmostEqual(paths[2][-1][1],220)
        self.assertAlmostEqual(paths[5][-1][0],818)
        self.assertAlmostEqual(paths[5][-1][1],437)
        markers=[s for s in self.pages[1].findall('.//p:sp',NS) if s.find('p:spPr/a:prstGeom',NS) is not None and s.find('p:spPr/a:prstGeom',NS).get('prst')=='ellipse']
        self.assertEqual(len(markers),1)

    def test_tall_single_line_band_uses_the_same_vertical_alignment(self):
        shapes=self.pages[0].findall('.//p:sp',NS)
        def with_text(value):
            return next(s for s in shapes if ''.join(n.text or '' for n in s.findall('.//a:t',NS))==value)
        label,body=with_text('观察'),with_text('单行任务与标签共用垂直中心。')
        lb,bb=self.box(label),self.box(body)
        self.assertEqual((lb[1],lb[3]),(bb[1],bb[3]))
        self.assertEqual(label.find('p:txBody/a:bodyPr',NS).get('anchor'),'ctr')
        self.assertEqual(body.find('p:txBody/a:bodyPr',NS).get('anchor'),'ctr')

    def test_narrow_default_and_multiline_label_share_readable_regions(self):
        bg=self.box(self.named(3,'method-strip-background'))
        label=self.box(self.named(3,'method-strip-label'));body=self.box(self.named(3,'method-strip-body'))
        self.assertEqual(bg[2],720)
        self.assertGreaterEqual(label[3],2*23*1.2)
        self.assertGreaterEqual(body[3],2*24*1.2)
        self.assertLess(label[0]+label[2],body[0])

    def test_left_callout_auto_aligns_text_toward_its_connection(self):
        title=self.named(4,'evidence-note-title');body=self.named(4,'evidence-note-body')
        for shape in [title,body]:
            self.assertEqual(shape.find('.//a:pPr',NS).get('algn'),'r')
        self.assertAlmostEqual(self.paths(4)[-1][-1][0],448)
        self.assertAlmostEqual(self.paths(4)[-1][-1][1],215)

    def test_hub_default_connections_reach_both_actual_boundaries(self):
        paths=self.paths(2);self.assertEqual(len(paths),2)
        for line,end in zip(paths,[(395,300),(890,480)]):
            self.assertAlmostEqual(math.dist(line[0],(640,385)),92,places=2)
            self.assertAlmostEqual(line[-1][0],end[0],places=2)
            self.assertAlmostEqual(line[-1][1],end[1],places=2)

    def test_invalid_geometry_fails_before_drawing(self):
        self.assertEqual(len(self.result['rejected']),6)
        self.assertTrue(all(r['threw'] and r['unchanged'] for r in self.result['rejected']),self.result['rejected'])

if __name__=='__main__':unittest.main()
