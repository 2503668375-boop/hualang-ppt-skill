import sys
from pathlib import Path
import tempfile
import unittest
from pptx import Presentation
SKILL=Path(__file__).resolve().parents[1]/'artifact-template-hualang-school'
sys.path.insert(0,str(SKILL/'scripts'))
from hualang_deck import Deck
from hualang_teaching_objects import fraction_strip
from audit_content_claims import audit_presentation

class ContentTools(unittest.TestCase):
 def deck(self):
  return Deck(SKILL/'assets/source-original.pptx',content_only=True)
 def test_fraction_partition_survives_save(self):
  d=self.deck();p=d.page('分数单位',tier='near')
  result=fraction_strip(p,48,250,720,80,3,4,split=2,highlight=[0,1,2])
  self.assertEqual(result['denominator'],8);self.assertEqual(result['shaded_end'],588)
  with tempfile.TemporaryDirectory() as tmp:
   f=Path(tmp)/'x.pptx';d.save(f);s=Presentation(f).slides[0]
   cells=[x for x in s.shapes if x.name.startswith('fraction-strip-cell')]
   self.assertEqual(len(cells),8)
   self.assertEqual(len({x.width for x in cells}),1)
   self.assertEqual(sum(str(x.fill.fore_color.rgb)=='403653' for x in cells),3)
 def test_invalid_fraction_not_silently_drawn(self):
  p=self.deck().page('分数单位')
  for args in [(4,3),(True,4),(3,0)]:
   with self.assertRaises(ValueError):fraction_strip(p,0,0,600,80,*args)
  with self.assertRaises(ValueError):fraction_strip(p,0,0,600,80,3,4,highlight=[7])
 def test_swimlane_nonoverlapping_tasks_share_track(self):
  from hualang_build import build_deck
  slide={'layout':'swimlane','title':'责任安排','periods':['准备','执行','复核'],
         'lanes':[{'label':'使用记录','owner':'图书馆','tasks':[
          {'start':0,'end':0,'label':'记录定义','deliverable':'口径表','status':'拟议'},
          {'start':1,'end':1,'label':'逐日登记','deliverable':'入馆记录','status':'拟议'},
          {'start':0,'end':2,'label':'材料复核','deliverable':'复核记录','status':'拟议'}]}]}
  with tempfile.TemporaryDirectory() as tmp:
   f=Path(tmp)/'x.pptx';build_deck({'title':'责任安排','scenario':'internal_report','content_only':True,'slides':[slide]},f)
   tasks={s.name:s for s in Presentation(f).slides[0].shapes if s.name.startswith('swimlane-')}
   self.assertEqual(tasks['swimlane-1-1'].top,tasks['swimlane-1-2'].top)
   self.assertGreater(tasks['swimlane-1-3'].top,tasks['swimlane-1-1'].top)
   self.assertIn('逐日登记',tasks['swimlane-1-2'].text)
   self.assertGreaterEqual(tasks['swimlane-1-2'].text_frame.paragraphs[0].runs[0].font.size.pt,14)
 def test_actual_ppt_audit_keeps_context_and_never_certifies(self):
  d=self.deck();p=d.page('材料安排');p.body('8类版式与4套框架，改一个数字整页跟着重排。',48,220,1184)
  p.body('活动预算4万元，计划参加80人，日期和人数均为原创模拟。',48,350,1184)
  with tempfile.TemporaryDirectory() as tmp:
   f=Path(tmp)/'x.pptx';d.save(f);a=audit_presentation(f)
   self.assertTrue(any(x['category']=='absolute_claim' for x in a['findings']))
   self.assertTrue(any(x['category']=='inventory_rhetoric' for x in a['findings']))
   self.assertEqual(a['status'],'human_review_required')
   self.assertTrue(any('预算4万元' in x for x in a['slides'][0]['text_blocks']))

if __name__=='__main__':unittest.main()
