#!/usr/bin/env python3
"""原创数学学习单元，使用同尺度原生图形；学生任务与教师反馈分别保存。"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'artifact-template-hualang-school'
sys.path.insert(0,str(SKILL/'scripts'))
from hualang_deck import Deck, _textbox, _write, text_height
from hualang_teaching_objects import fraction_strip, brace_label, anchored_note
from audit_content_claims import audit_presentation


def text(p,s,x,y,w,size=26,color='ink',bold=False,h=None):
 b=_textbox(p.slide,x,y,w,h or text_height(s,w,size,1.35))
 _write(b.text_frame,s,size,color,bold=bold,line_spacing=1.35)
 return b


def page(d,title,lead=None):
 p=d.page(title,tier='near')
 if lead:text(p,lead,48,112,1184,36,bold=True)
 p.context('原创数学学习单元 · 已学分数的意义与乘法',y=171)
 p.page_number();return p


def build(out):
 out.mkdir(parents=True,exist_ok=True)
 d=Deck(SKILL/'assets/source-original.pptx',title='分数除以整数',presenter='教学示范',date='2026年11月8日')
 d.set_closing_message('保留你的图、算式和解释')
 p=page(d,'彩带分段','3/4 米彩带，平均剪成两段，每段有多长？')
 text(p,'图中一整条表示 1 米。先标出 3/4 米，再画出平均分的位置。',48,216,1120,26)
 fraction_strip(p,80,300,720,76,3,4)
 brace_label(p,80,800,390,'1 米',size=22)
 text(p,'小周的困惑',880,282,320,26,'purple',True)
 text(p,'“3 个 1/4 分成两份，每份不是整数格，图就画不出来了。”',880,326,320,24)
 text(p,'请说明你怎样处理原来的每一格。',880,455,320,24,'blue',True)
 p.rule(48,548,1184)
 text(p,'把画图过程和算式对应起来：分的是什么？每份有几个这样的单位？',48,572,1184,27)

 p=page(d,'分数单位','把每个 1/4 再分成两格，就能继续平均分。')
 text(p,'原来按四等分看',48,228,400,23,'purple',True)
 fraction_strip(p,48,273,720,56,3,4)
 text(p,'同一长度，改按八等分看',48,370,640,23,'purple',True)
 fraction_strip(p,48,417,720,72,3,4,split=2,highlight=[0,1,2])
 brace_label(p,48,318,507,'一份：3 个 1/8 米',size=22,label_width=300)
 brace_label(p,318,588,507,'另一份：3 个 1/8 米',size=22,label_width=300)
 text(p,'完整的一米没有改变',850,236,350,27,'purple',True)
 text(p,'3/4 = 6/8',850,288,350,42,'blue',True)
 text(p,'六个小单位平均分成两份，每份三个。',850,358,350,26)
 text(p,'3/4 ÷ 2 = 3/8（米）',850,467,350,30,'ink',True)

 p=page(d,'算式联系','平均分成两份，就是取原来这段彩带的一半。')
 text(p,'3/4 米作为这次平均分的对象',48,228,850,26,'purple',True)
 fraction_strip(p,48,304,1080,84,3,4,split=2,highlight=[0,1,2])
 brace_label(p,48,453,407,'取这段彩带的一半',size=24,label_width=405)
 brace_label(p,48,858,482,'原来这段彩带：3/4 米',size=24)
 text(p,'3/4 ÷ 2',64,575,300,42,'ink',True)
 text(p,'=',382,575,50,42,'ink',True)
 text(p,'3/4 × 1/2',462,575,340,42,'purple',True)
 text(p,'这里的 1/2 表示取原量的一半。',850,555,340,25,'ink')

 p=page(d,'两种操作','取一半，与减去 1/2 米，得到的长度不同。')
 text(p,'把 3/4 米平均分成两份',48,229,530,26,'purple',True)
 fraction_strip(p,48,288,520,70,3,4,split=2,highlight=[0,1,2])
 brace_label(p,48,243,380,'一份 3/8 米',size=23,label_width=240)
 text(p,'取原来长度的 1/2，另一份同样长。',48,472,520,26)
 text(p,'从 3/4 米中剪去 1/2 米',680,229,550,26,'blue',True)
 fraction_strip(p,680,288,520,70,3,4,split=2,highlight=[4,5],accent='blue')
 brace_label(p,680,940,380,'剪去 1/2 米',size=23,label_width=260,color='secondary')
 brace_label(p,940,1070,434,'剩 1/4 米',size=23,label_width=220,color='blue')
 text(p,'减去固定的 1/2 米，剩下原来的一部分。',680,516,520,26)
 p.rule(48,593,1184)
 text(p,'解释时写清：1/2 是“原来彩带的一半”，还是“半米”。',48,614,1184,25,'ink',True)

 p=page(d,'独立作答','4/5 米彩带平均分成三份，每份有多长？')
 text(p,'画出完整单位与分法，写出算式，再解释两者怎样对应。',48,222,1184,28)
 fraction_strip(p,48,304,1050,76,0,5)
 brace_label(p,48,1098,399,'空白整条表示 1 米，请自行标出彩带与分法。',size=22)
 p.panel(48,500,1184,145,fill='pale')
 text(p,'留下你的依据',72,518,350,26,'purple',True)
 text(p,'新的分数单位是什么？每一份有几个？\n与原来的 4/5 米相比，结果应更长还是更短？',72,563,1120,27)

 p=page(d,'迁移练习','2/3 米长的纸条，平均分成四份。')
 text(p,'用图、算式和文字说明每份长度，并回答下面的问题。',48,222,1150,28)
 text(p,'①',48,304,54,28,'purple',True)
 text(p,'原来的一个 1/3 应再分成几份？新的单位是什么？',112,304,1080,28)
 text(p,'②',48,390,54,28,'purple',True)
 text(p,'如果把 2/3 ÷ 4 写成 2/7，图中哪一处不相符？',112,390,1080,28)
 text(p,'③',48,476,54,28,'purple',True)
 text(p,'把 a/b 平均分成 n 份，为什么可以写成 a/(b×n)？\n本题中 b、n 都是正整数；零份无法完成这样的平均分。',112,476,1080,28)
 text(p,'作答后再查教师反馈，保留原来的错误和修改过程。',48,620,1184,22,'secondary')
 student=out/'分数除以整数_学生学习单元.pptx';d.save(student)

 t=Deck(SKILL/'assets/source-original.pptx',title='分数除法教学反馈',presenter='教学示范',date='2026年11月8日')
 t.set_closing_message('看清分数单位，再判断是否理解')
 p=page(t,'作答核对','4/5 ÷ 3 = 4/15：先把原来的每个 1/5 再三等分。')
 fraction_strip(p,48,276,900,80,4,5,split=3,highlight=[0,1,2,3])
 brace_label(p,48,288,379,'一份：4 个 1/15',size=23,label_width=260)
 brace_label(p,48,768,452,'4/5 = 12/15，共 12 个小单位',size=24)
 text(p,'新单位',1010,265,200,24,'purple',True)
 text(p,'1/15',1010,305,200,42,'purple',True)
 text(p,'三份各有四个，合起来回到原来的 4/5。',1010,375,205,24)
 p.rule(48,551,1184)
 text(p,'判据',48,577,120,25,'purple',True)
 text(p,'能解释“为何分成十五格”，并指出每份的四格；只报出 4/15，尚不能证明理解了单位细分。',190,577,1040,26)

 p=page(t,'迁移反馈','2/3 ÷ 4 = 2/12 = 1/6：完整单位保持不变。')
 fraction_strip(p,48,267,900,72,2,3,split=4,highlight=[0,1])
 brace_label(p,48,198,362,'一份：2 个 1/12',size=23,label_width=245)
 text(p,'a/b ÷ n = a/(b×n) = a/b × 1/n',48,469,1184,38,'purple',True)
 text(p,'每个 1/b 再分成 n 份，新单位是 1/(b×n)。\n原来每个单位都贡献一小份，所以每份共 a 个新单位。',48,542,1184,27)

 p=page(t,'错误后的处理','让学生把算式里的每个数放回图中核对。')
 rows=[['观察到的作答','下一步追问或操作','判断是否修正'],
       ['只写“乘倒数”','指出 1/2 是谁的一半，圈出对应范围。','能说明原来的 3/4 米才是分的对象。'],
       ['把 4/5 ÷ 3 算成 4/8','保留完整一米，将每个 1/5 三等分，再数总格数。','图有15格；能说明分母应乘3。'],
       ['把“取一半”当成“减半米”','并排画出两种操作，标出取走和保留的范围。','能区分3/8米与1/4米的来源。']]
 p.table(48,231,[285,490,409],rows,row_h=108,head_h=44,align=['l','l','l'])
 text(p,'使用顺序：彩带任务 → 单位细分与算式联系 → 独立题 → 迁移题。按学生实际回应决定停留与补问，不预设完成速度。',48,620,1184,21,'secondary')
 teacher=out/'分数除以整数_教师反馈.pptx';t.save(teacher)
 for f in [student,teacher]:
  (out/(f.stem+'_文案复读.json')).write_text(json.dumps(audit_presentation(f),ensure_ascii=False,indent=2))
 print(student);print(teacher)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();build(args.out)
