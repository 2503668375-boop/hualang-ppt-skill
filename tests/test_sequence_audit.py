"""Synthetic OOXML behavior tests; contains no school/user source content."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as E
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/'artifact-template-hualang-school'/'scripts'
sys.path.insert(0, str(SCRIPTS))
import audit_sequence as audit

P, A, R = (audit.NS[k] for k in ('p', 'a', 'r'))
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
C = audit.CHART_NS


def el(parent, ns, tag, **attrs):
    return E.SubElement(parent, '{'+ns+'}'+tag, {k: str(v) for k, v in attrs.items()})


def transform(parent, tag, box, size=(1000, 500), **attrs):
    node = el(parent, P if tag == 'xfrm' else A, 'xfrm', **attrs)
    x, y, w, h = box
    el(node, A, 'off', x=round(x*size[0]), y=round(y*size[1]))
    el(node, A, 'ext', cx=round(w*size[0]), cy=round(h*size[1]))
    return node


def shape(tree, box, text='', fill=None, geometry='rect', size=(1000, 500)):
    node = el(tree, P, 'sp')
    prop = el(node, P, 'spPr')
    transform(prop, 'a:xfrm', box, size)
    el(prop, A, 'prstGeom', prst=geometry)
    if fill:
        el(el(prop, A, 'solidFill'), A, 'srgbClr', val=fill)
    if text:
        run = el(el(el(node, P, 'txBody'), A, 'p'), A, 'r')
        el(run, A, 't').text = text
    return node


def frame(tree, kind, box, size=(1000, 500)):
    node = el(tree, P, 'graphicFrame')
    transform(node, 'xfrm', box, size)
    data = el(el(node, A, 'graphic'), A, 'graphicData')
    if kind == 'chart':
        el(data, C, 'chart')
    elif kind == 'table':
        el(data, A, 'tbl')
    return node


def picture(tree, box, size=(1000, 500)):
    node = el(tree, P, 'pic')
    transform(el(node, P, 'spPr'), 'a:xfrm', box, size)
    return node


def slide():
    root = E.Element('{'+P+'}sld')
    tree = el(el(root, P, 'cSld'), P, 'spTree')
    return root, tree


def cards(size=(1000, 500), fill='663399', jitter=0, words='value', mirror=False):
    root, tree = slide()
    # Changing a header must not affect the body's composition finding.
    shape(tree, (.03+jitter*10, .03, .55, .06), words+' header', size=size)
    for index, x in enumerate((.05, .36, .67)):
        x += jitter
        if mirror:
            x = 1-x-.28
        shape(tree, (x, .27+jitter, .28, .50), fill=fill, size=size)
        shape(tree, (x+.025, .32+jitter, .23, .34), words+str(index), size=size)
    return root


class SequenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hualang-sequence-')
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def deck(self, content, size=(1000, 500), name='test.pptx'):
        roots = [slide()[0], *content, slide()[0]]
        pres = E.Element('{'+P+'}presentation')
        ids = el(pres, P, 'sldIdLst')
        rels = E.Element('{'+PKG+'}Relationships')
        for index in range(1, len(roots)+1):
            node = el(ids, P, 'sldId', id=255+index)
            node.set('{'+R+'}id', 'rId'+str(index))
            el(rels, PKG, 'Relationship', Id='rId'+str(index), Type=R+'/slide', Target='slides/slide'+str(index)+'.xml')
        el(pres, P, 'sldSz', cx=size[0], cy=size[1])
        path = self.directory/name
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as output:
            output.writestr('ppt/presentation.xml', E.tostring(pres))
            output.writestr('ppt/_rels/presentation.xml.rels', E.tostring(rels))
            for index, root in enumerate(roots, 1):
                output.writestr('ppt/slides/slide'+str(index)+'.xml', E.tostring(root))
        return path

    def test_manifest_optional_and_variations_do_not_hide_real_grid(self):
        path = self.deck([cards(), cards(fill='009988', words='new'), cards(jitter=.004, mirror=True)])
        result = audit.audit(path)
        self.assertTrue(result['ok'])
        self.assertEqual(result['content_pages'], 3)
        self.assertEqual(result['panel_grid_pages'], [2, 3, 4])
        self.assertEqual(result['pages'][1]['panel_groups'][0]['columns_by_row'], [3])
        self.assertTrue(any(f['code'] == 'recurring-geometry' for f in result['findings']))
        self.assertEqual(len(result['similar_pairs']), 3)
        self.assertFalse(any(f['code'].endswith('family') for f in result['findings']))

    def test_new_layout_names_and_continuation_reasons_keep_findings(self):
        path = self.deck([cards(), cards(words='different content'), cards()])
        manifest = {'slides': [{'slide': n, 'family': 'unique-'+str(n),
                               'continuationReason': '同一对象的对照'} for n in range(2, 5)]}
        result = audit.audit(path, manifest)
        self.assertTrue(result['ok'])
        finding = next(f for f in result['findings'] if f['code'] == 'adjacent-geometry')
        self.assertEqual(finding['continuation_reasons'], {'2': '同一对象的对照', '3': '同一对象的对照'})
        self.assertTrue(any('已登记连续理由' in text for text in result['warnings']))

    def test_different_slide_dimensions_have_same_normalized_geometry(self):
        small = audit.audit(self.deck([cards()], name='small.pptx'))
        large = audit.audit(self.deck([cards(size=(2000, 1000))], size=(2000, 1000), name='large.pptx'))
        self.assertEqual(small['pages'][1]['geometry_signature'], large['pages'][1]['geometry_signature'])
        self.assertEqual(large['slide_size_emu'], [2000, 1000])

    def test_asymmetric_mirror_is_still_the_same_layout(self):
        roots = []
        for mirrored in (False, True):
            root, tree = slide()
            for kind, box in [('picture', (.05, .2, .56, .6)), ('text', (.67, .25, .28, .43))]:
                if mirrored:
                    box = (1-box[0]-box[2], *box[1:])
                picture(tree, box) if kind == 'picture' else shape(tree, box, 'annotation')
            roots.append(root)
        result = audit.audit(self.deck(roots))
        self.assertTrue(result['similar_pairs'][0]['mirrored'])
        self.assertGreaterEqual(result['similar_pairs'][0]['similarity'], .99)
        self.assertFalse(result['panel_grid_pages'])

    def test_picture_chart_table_and_timeline_are_not_panel_grids(self):
        roots = []
        for kind in ('picture', 'chart', 'table', 'timeline'):
            root, tree = slide()
            if kind == 'picture':
                picture(tree, (.05, .2, .9, .65))
            elif kind in ('chart', 'table'):
                frame(tree, kind, (.05, .2, .9, .65))
            else:
                shape(tree, (.1, .5, .8, 0), geometry='line')
                for x in (.1, .36, .62, .86):
                    shape(tree, (x, .47, .04, .08), fill='663399', geometry='ellipse')
                    shape(tree, (x-.03, .60, .16, .13), 'milestone')
            roots.append(root)
        result = audit.audit(self.deck(roots))
        self.assertFalse(result['panel_grid_pages'])
        self.assertEqual(result['pages'][1]['pictures'], 1)
        self.assertEqual(result['pages'][2]['charts'], 1)
        self.assertEqual(result['pages'][3]['tables'], 1)
        self.assertFalse(result['similar_pairs'])

    def test_nested_group_scaling_and_flip_are_resolved(self):
        root, tree = slide()
        outer = el(tree, P, 'grpSp')
        outer_transform = transform(el(outer, P, 'grpSpPr'), 'a:xfrm', (.10, .2, .8, .6), flipH='1')
        el(outer_transform, A, 'chOff', x=0, y=0)
        el(outer_transform, A, 'chExt', cx=1000, cy=500)
        inner = el(outer, P, 'grpSp')
        inner_transform = transform(el(inner, P, 'grpSpPr'), 'a:xfrm', (0, 0, 1, 1))
        el(inner_transform, A, 'chOff', x=0, y=0)
        el(inner_transform, A, 'chExt', cx=1000, cy=500)
        picture(inner, (.1, .1, .5, .5))
        objects = audit.read_objects(root, (1000, 500))
        self.assertEqual(len(objects), 1)
        for actual, expected in zip(objects[0]['box'], (.42, .26, .4, .3)):
            self.assertAlmostEqual(actual, expected)

    def test_grouped_shapes_still_count_as_real_panels(self):
        root = cards()
        tree = root.find('p:cSld/p:spTree', audit.NS)
        children = list(tree)
        for child in children:
            tree.remove(child)
        group = el(tree, P, 'grpSp')
        tr = transform(el(group, P, 'grpSpPr'), 'a:xfrm', (0, 0, 1, 1))
        el(tr, A, 'chOff', x=0, y=0)
        el(tr, A, 'chExt', cx=1000, cy=500)
        for child in children:
            group.append(child)
        result = audit.audit(self.deck([root, cards()]))
        self.assertEqual(result['panel_grid_pages'], [2, 3])
        self.assertTrue(result['similar_pairs'][0]['exact'])

    def test_duplicate_and_missing_manifest_pages_fail_structural_check(self):
        path = self.deck([cards(), cards()])
        for rows in ([{'slide': 2}], [{'slide': 2}, {'slide': 3}, {'slide': 3}]):
            result = audit.audit(path, {'slides': rows})
            self.assertFalse(result['ok'])
            self.assertTrue(result['errors'])

    def test_actual_abab_and_nonadjacent_reuse_need_no_layout_labels(self):
        photo, tree = slide()
        picture(tree, (.05, .2, .9, .65))
        result = audit.audit(self.deck([cards(), photo, cards(words='later'), photo]))
        codes = {finding['code'] for finding in result['findings']}
        self.assertIn('abab-geometry', codes)
        self.assertIn('revisited-geometry', codes)


if __name__ == '__main__':
    unittest.main()
