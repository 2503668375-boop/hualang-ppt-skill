"""Native scene/preview behavior without creating a new PPTX.

Use HUALANG_NODE and HUALANG_NODE_MODULES from runtime discovery. Missing runtime
dependencies skip this group explicitly; generated evidence stays in a temp dir.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'artifact-template-hualang-school'


class PreviewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node=os.environ.get('HUALANG_NODE')
        modules=os.environ.get('HUALANG_NODE_MODULES')
        if not node or not modules:
            raise unittest.SkipTest('Set HUALANG_NODE and HUALANG_NODE_MODULES for native preview checks.')
        executable=shutil.which(node)
        module_dir=Path(modules)
        if not executable or not module_dir.is_dir() or not (module_dir/'@oai'/'artifact-tool').exists():
            raise unittest.SkipTest('HUALANG_NODE or @oai/artifact-tool is unavailable at the supplied runtime paths.')
        cls.temp=tempfile.TemporaryDirectory(prefix='hualang-preview-contract-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work=Path(cls.temp.name)
        shutil.copy2(SKILL/'scripts'/'hualang-kit.mjs',cls.work/'hualang-kit.mjs')
        shutil.copy2(Path(__file__).with_name('preview-contract-fixture.mjs'),cls.work/'fixture.mjs')
        (cls.work/'node_modules').symlink_to(module_dir,target_is_directory=True)
        source=SKILL/'assets'/'source-original.pptx'
        cls.source_before=hashlib.sha256(source.read_bytes()).hexdigest()
        run=subprocess.run([executable,str(cls.work/'fixture.mjs'),str(SKILL),str(cls.work)],
                           capture_output=True,text=True,timeout=180)
        if run.returncode:
            raise AssertionError(run.stdout+'\n'+run.stderr)
        cls.result=json.loads((cls.work/'fixture.json').read_text())
        cls.manifests=[json.loads(Path(cls.result[key]['renderManifestPath']).read_text())
                       for key in ('first','second')]
        retain=os.environ.get('HUALANG_TEST_OUTPUT')
        if retain:
            destination=Path(retain)/'preview-contract'
            shutil.copytree(cls.work/'previews',destination/'previews',dirs_exist_ok=True)
            destination.mkdir(parents=True,exist_ok=True)
            def relocated(value):
                if isinstance(value,dict):
                    return {key:relocated(item) for key,item in value.items()}
                if isinstance(value,list):
                    return [relocated(item) for item in value]
                if isinstance(value,str) and value.startswith(str(cls.work)+os.sep):
                    return str(destination/value[len(str(cls.work))+1:])
                return value
            for manifest in destination.rglob('render-manifest.json'):
                manifest.write_text(json.dumps(relocated(json.loads(manifest.read_text())),ensure_ascii=False,indent=2)+'\n')
            (destination/'fixture.json').write_text(json.dumps(relocated(cls.result),ensure_ascii=False,indent=2)+'\n')

    def test_mixed_requires_explicit_purpose_but_single_default_and_override_work(self):
        checks=self.result['inMemoryChecks']
        self.assertEqual(checks['mixedOmissionRejected'],['addPage','addSchoolScene'])
        self.assertEqual(checks['explicitPurposes'],['classroom','parent'])
        self.assertEqual(checks['singleDefault'],'parent')
        self.assertEqual(checks['singleOverride'],'lessonPlan')
        self.assertEqual(self.result['observedFonts'],{'classroom':26,'parent':26,
                         'singlePage':26,'singleScene':26,'singleOverride':21})

    def test_preview_uses_existing_saved_file_and_does_not_export_a_new_deck(self):
        source=SKILL/'assets'/'source-original.pptx'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),self.source_before)
        self.assertEqual(self.result['sourceSha256'],self.source_before)
        self.assertEqual(list(self.work.rglob('*.pptx')),[])
        for manifest in self.manifests:
            self.assertEqual(Path(manifest['artifact']['path']),source.resolve())
            self.assertEqual(manifest['artifact']['sha256'],self.source_before)
            self.assertEqual(manifest['renderSourceSha256'],self.source_before)
            self.assertEqual(manifest['renderEvidence']['kind'],'saved_file_render')
            self.assertIn('importPptx',manifest['renderEvidence']['entryPoint'])
            self.assertEqual(manifest['renderEvidence']['engine'],'@oai/artifact-tool')

    def test_manifest_is_unreviewed_and_covers_only_the_requested_real_page(self):
        with zipfile.ZipFile(SKILL/'assets'/'source-original.pptx') as source:
            root=ET.fromstring(source.read('ppt/presentation.xml'))
            namespace={'p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
            count=len(root.find('p:sldIdLst',namespace))
        for key,manifest in zip(('first','second'),self.manifests):
            self.assertEqual(self.result[key]['reviewStatus'],'unreviewed')
            self.assertEqual(manifest['status'],'unreviewed')
            self.assertEqual(manifest['slideCount'],count)
            self.assertEqual(manifest['scope'],[2])
            self.assertEqual(len(manifest['pages']),1)
            page=manifest['pages'][0]
            self.assertEqual(page['slide'],2)
            self.assertEqual(page['verdict'],'unverified')
            self.assertEqual(page['subject'],'')
            self.assertEqual(page['scene'],'existing-template')
            self.assertEqual(Path(page['render']).stem,'slide-02')
            layout=json.loads(Path(page['layout']).read_text())
            self.assertEqual(layout['slide']['index'],1)

    def test_png_hash_dimensions_and_run_paths_match_the_evidence(self):
        self.assertNotEqual(self.result['first']['renderDir'],self.result['second']['renderDir'])
        for key,manifest in zip(('first','second'),self.manifests):
            page=manifest['pages'][0]
            render=Path(page['render'])
            data=render.read_bytes()
            self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II',data[16:24]),(640,360))
            self.assertEqual(hashlib.sha256(data).hexdigest(),page['renderSha256'])
            self.assertEqual(self.result[key]['renderPaths'],[str(render)])
            self.assertEqual(render.parent,Path(self.result[key]['renderDir']))
            self.assertEqual(Path(page['layout']).parent,render.parent)
            self.assertEqual(len(list(render.parent.glob('*.png'))),1)

    def test_invalid_scale_and_slide_selections_are_rejected(self):
        self.assertEqual(self.result['invalidInputsRejected'],{'scales':5,'slideSelections':6})


if __name__=='__main__':
    unittest.main()
