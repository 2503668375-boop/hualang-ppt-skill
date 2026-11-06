"""Measured PDF-boundary behavior; fixtures contain no school/user content."""
from pathlib import Path
import io
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/'artifact-template-hualang-school'/'scripts'
sys.path.insert(0, str(SCRIPTS))
import audit_rendered_pdf as audit

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader
except ImportError:
    canvas = HexColor = ImageReader = None

try:
    import PIL
except ImportError:
    PIL = None


class DependencyTests(unittest.TestCase):
    def test_missing_dependency_is_explicit_and_not_a_pass(self):
        with mock.patch.object(audit, 'pdfplumber', None):
            result = audit.audit('not-opened.pdf')
        self.assertFalse(result['parsed'])
        self.assertEqual(result['status'], 'review_required')
        self.assertEqual(result['errors'][0]['code'], 'dependency_missing')
        self.assertIn('不会自动安装', result['errors'][0]['message'])


@unittest.skipUnless(audit.pdfplumber is not None and canvas is not None,
                     'PDF几何测试需要可选的pdfplumber和reportlab；未安装时明确跳过。')
class RenderedPdfAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hualang-pdf-audit-')
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def pdf(self, draw, name='fixture.pdf'):
        target = self.directory/name
        c = canvas.Canvas(str(target), pagesize=(600, 400))
        c.setFont('Helvetica', 20)
        draw(c)
        c.showPage()
        c.save()
        return target

    @staticmethod
    def panel(c, x=60, y=120, width=300, height=160):
        c.setFillColor(HexColor('#EEE8F4'))
        c.rect(x, y, width, height, fill=1, stroke=0)
        c.setFillColor(HexColor('#222222'))

    def test_text_fits_inside_panel(self):
        def draw(c):
            self.panel(c)
            c.drawString(80, 150, 'Fits inside the panel')
        result = audit.audit(self.pdf(draw))
        self.assertTrue(result['parsed'])
        self.assertEqual(result['status'], 'no_measured_issue')
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['page_summaries'][0]['content_panels'], 1)
        self.assertNotIn('layoutpass', json.dumps(result))

    def test_actual_glyph_lower_edge_crosses_panel_bottom(self):
        def draw(c):
            self.panel(c)
            c.drawString(80, 120, 'Crosses panel bottom')
        result = audit.audit(self.pdf(draw))
        self.assertTrue(result['parsed'])
        self.assertEqual(result['status'], 'review_required')
        crossing = [f for f in result['findings'] if f['code'] == 'text_crosses_panel']
        self.assertEqual(len(crossing), 1)
        finding = crossing[0]
        self.assertEqual(finding['page'], 1)
        self.assertEqual(finding['text'], 'Crosses panel bottom')
        self.assertLess(finding['line_bbox'][1], finding['panel_bbox'][3])
        self.assertGreater(finding['line_bbox'][3], finding['panel_bbox'][3]+1)
        self.assertFalse(any(f['code'] == 'text_outside_page' for f in result['findings']))

    def test_text_outside_page_is_reported(self):
        def draw(c):
            c.drawString(590, 350, 'Past the right edge')
            c.drawString(60, 0, 'Below the page')
        result = audit.audit(self.pdf(draw))
        outside = [f for f in result['findings'] if f['code'] == 'text_outside_page']
        self.assertEqual(len(outside), 2)
        self.assertTrue(any(f['line_bbox'][2] > 600 for f in outside))
        self.assertTrue(any(f['line_bbox'][3] > 400 for f in outside))
        self.assertTrue(all(f['panel_bbox'] is None for f in outside))

    def test_full_page_and_near_page_backgrounds_are_excluded(self):
        def draw(c):
            self.panel(c, 0, 0, 600, 400)
            self.panel(c, 8, 8, 584, 384)
            # The glyph bottom crosses the inset background but is on-page.
            c.drawString(80, 9, 'Not a content-panel overflow')
        result = audit.audit(self.pdf(draw))
        self.assertEqual(result['page_summaries'][0]['content_panels'], 0)
        self.assertEqual(result['status'], 'no_measured_issue')
        self.assertEqual(result['findings'], [])

    def test_public_boundary_tolerance_is_a_measurement_setting(self):
        def draw(c):
            self.panel(c)
            c.drawString(80, 120, 'Tolerance example')
        pdf = self.pdf(draw)
        self.assertEqual(audit.audit(pdf)['status'], 'review_required')
        relaxed = audit.audit(pdf, tolerance_pt=6.0)
        self.assertEqual(relaxed['status'], 'no_measured_issue')
        self.assertEqual(relaxed['tolerances']['boundary_pt'], 6.0)
        self.assertTrue(relaxed['limitations'])

    def test_thin_color_strips_are_not_content_panels(self):
        def draw(c):
            self.panel(c, 60, 120, 300, 4)
            self.panel(c, 430, 120, 4, 200)
            c.drawString(80, 150, 'Ordinary annotation')
        result = audit.audit(self.pdf(draw))
        self.assertEqual(result['page_summaries'][0]['content_panels'], 0)
        self.assertEqual(result['findings'], [])

    def test_blank_page_requires_review_even_when_other_page_is_measurable(self):
        def draw(c):
            c.drawString(80, 150, 'Measured first page')
            c.showPage()
            # The fixture helper closes this deliberately blank second page.
        result = audit.audit(self.pdf(draw))
        self.assertTrue(result['parsed'])
        self.assertEqual(result['unmeasured_pages'], [2])
        self.assertEqual(result['status'], 'review_required')
        self.assertEqual(result['findings'], [])

    @unittest.skipUnless(PIL is not None, '纯图片PDF夹具需要reportlab的可选Pillow图像依赖。')
    def test_image_only_page_is_unmeasured_not_a_geometry_defect(self):
        def chunk(kind, payload):
            return (struct.pack('>I', len(payload)) + kind + payload
                    + struct.pack('>I', zlib.crc32(kind+payload) & 0xffffffff))
        # A synthetic one-pixel RGB PNG; no user image or OCR is involved.
        png = (b'\x89PNG\r\n\x1a\n'
               + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress(b'\x00\x66\x33\x99'))
               + chunk(b'IEND', b''))
        result = audit.audit(self.pdf(
            lambda c: c.drawImage(ImageReader(io.BytesIO(png)), 60, 80,
                                  width=300, height=200)))
        self.assertTrue(result['parsed'])
        self.assertEqual(result['unmeasured_pages'], [1])
        self.assertEqual(result['status'], 'review_required')
        self.assertEqual(result['findings'], [])

    def test_cli_writes_json_and_returns_review_signal(self):
        def draw(c):
            self.panel(c)
            c.drawString(80, 120, 'CLI panel example')
        pdf = self.pdf(draw)
        output = self.directory/'result.json'
        run = subprocess.run([sys.executable, str(SCRIPTS/'audit_rendered_pdf.py'),
                              str(pdf), '--output', str(output)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 1, run.stderr)
        saved = json.loads(output.read_text())
        self.assertEqual(saved, json.loads(run.stdout))
        self.assertTrue(saved['parsed'])
        self.assertEqual(saved['status'], 'review_required')

    def test_cli_refuses_to_overwrite_input_pdf(self):
        pdf = self.pdf(lambda c: c.drawString(80, 150, 'Preserve the source PDF'))
        before = pdf.read_bytes()
        run = subprocess.run([sys.executable, str(SCRIPTS/'audit_rendered_pdf.py'),
                              str(pdf), '--output', str(pdf)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('--output不能与输入PDF相同', run.stderr)
        self.assertEqual(pdf.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
