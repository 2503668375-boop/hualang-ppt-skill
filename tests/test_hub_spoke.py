"""Check semantic hub export, edge connections and atomic invalid-input rejection."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}

class HubSpokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node, modules = os.environ.get('HUALANG_NODE'), os.environ.get('HUALANG_NODE_MODULES')
        if not node or not modules:
            raise unittest.SkipTest('Set discovered HUALANG_NODE and HUALANG_NODE_MODULES.')
        cls.temp = tempfile.TemporaryDirectory(prefix='hualang-hub-')
        cls.addClassCleanup(cls.temp.cleanup)
        work = Path(cls.temp.name)
        shutil.copy2(ROOT/'artifact-template-hualang-school/scripts/hualang-kit.mjs', work/'hualang-kit.mjs')
        (work/'node_modules').symlink_to(modules, target_is_directory=True)
        (work/'fixture.mjs').write_text('''
import fs from 'node:fs/promises';
import {PresentationFile} from '@oai/artifact-tool';
import {createDeck} from './hualang-kit.mjs';
const d=await createDeck({skillDir:process.argv[2],title:'关系验证',presenter:'示例',date:'2026年11月7日'});
const s=d.addPage({title:'共同对象'}), hub={x:640,y:390,r:85,title:'学生'};
const a={x:70,y:240,w:300,h:130,title:'教师',body:'根据作答提供练习',relation:'练习支持'};
const b={x:900,y:240,w:300,h:150,title:'家庭',body:'提供环境与观察',relation:'学习条件',connect:false};
const objects=d.hubSpoke(s,{center:hub,nodes:[a,b]});
const rejected=[];
for(const input of [
 {center:{...hub,x:NaN},nodes:[a]},
 {center:hub,nodes:[{...a,x:1200}]},
 {center:hub,nodes:[a,{...a,title:'重复区域'}]},
 {center:hub,nodes:[{...a,x:600,y:350}]},
 {center:hub,nodes:[{...a,relation:''}]},
 {center:hub,nodes:[{...a,label:{x:80,y:250,w:100,h:25}}]},
 {center:hub,nodes:[{...a,anchor:{x:400,y:200}}]},
 {center:hub,nodes:[{...a,x:550,y:350,anchor:{x:850,y:350}}]},
]) {const count=s.shapes.items.length;let failed=false;try{d.hubSpoke(s,input)}catch{failed=true}rejected.push({failed,unchanged:count===s.shapes.items.length});}
await (await PresentationFile.exportPptx(d.presentation)).save(process.argv[3]+'/hub.pptx');
await fs.writeFile(process.argv[3]+'/result.json',JSON.stringify({rejected,objectCount:objects.length}));
''')
        run = subprocess.run([node,str(work/'fixture.mjs'),str(ROOT/'artifact-template-hualang-school'),str(work)],capture_output=True,text=True,timeout=120)
        if run.returncode:
            raise AssertionError(run.stdout+run.stderr)
        cls.result=json.loads((work/'result.json').read_text())
        with zipfile.ZipFile(work/'hub.pptx') as z:
            cls.slide=ET.fromstring(z.read('ppt/slides/slide2.xml'))

    def test_invalid_geometry_and_missing_relationship_leave_no_partial_diagram(self):
        self.assertEqual(len(self.result['rejected']),8)
        self.assertTrue(all(r['failed'] and r['unchanged'] for r in self.result['rejected']))

    def test_center_is_a_single_native_circle_and_satellites_are_editable_text(self):
        shapes=self.slide.findall('.//p:sp',NS)
        circles=[s for s in shapes if s.find('p:spPr/a:prstGeom',NS) is not None and s.find('p:spPr/a:prstGeom',NS).get('prst')=='ellipse']
        self.assertEqual(len(circles),1)  # no invented outer orbit or equal circular containers
        texts=[''.join(n.text or '' for n in s.findall('.//a:t',NS)) for s in shapes]
        for required in ['学生','教师','家庭','练习支持','学习条件','根据作答提供练习','提供环境与观察']:
            self.assertIn(required,texts)

    def test_optional_connection_and_line_endpoints_respect_center_and_text_regions(self):
        paths=self.slide.findall('.//p:sp/p:spPr/a:custGeom/a:pathLst/a:path',NS)
        self.assertEqual(len(paths),1)  # connect:false removes the family's connector
        shape=next(s for s in self.slide.findall('.//p:sp',NS) if s.find('p:spPr/a:custGeom',NS) is not None)
        xf=shape.find('p:spPr/a:xfrm',NS)
        off,ext=xf.find('a:off',NS),xf.find('a:ext',NS)
        x,y,w,h=[int(v)/9525 for v in [off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy')]]
        p=paths[0]
        points=[(x+int(n.get('x'))/int(p.get('w'))*w,y+int(n.get('y'))/int(p.get('h'))*h) for n in p.findall('.//a:pt',NS)]
        self.assertEqual(len(points),2)
        self.assertAlmostEqual(((points[0][0]-640)**2+(points[0][1]-390)**2)**.5,91,places=2)
        self.assertGreater(points[1][0],370)  # line stops outside the left satellite's text
        self.assertLess(points[1][0],400)

if __name__=='__main__':
    unittest.main()
