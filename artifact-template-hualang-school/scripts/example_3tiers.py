#!/usr/bin/env python3
"""三档样张示例：留阅、近距、远距各一页。

运行：python3 example_3tiers.py --out ./成品
输出：带原封面与原封尾的完整稿，可用 check_style_contract.py 校验。
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
from hualang_deck import Deck, COLORS as C  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--out', type=Path, default=Path('./成品'))
ap.add_argument('--presenter', default='示例工作组')
ap.add_argument('--date', default='2026年11月8日')
a = ap.parse_args()
OUT = a.out
OUT.mkdir(parents=True, exist_ok=True)

deck = Deck(SKILL / 'assets' / 'source-original.pptx',
            title='华朗学校分场景应用样页',
            presenter=a.presenter, date=a.date)
deck.set_closing_message('感谢聆听　欢迎指正')

# ============ P1 留阅档 ============
p = deck.page('开放日费用与到场', tier='read')
p.lead('费用增25%、实到增31.3%，B场每位实到费用低4.8%')
p.context('模拟资料 · 非学校实绩；两场费用口径相同，比较基准均为A场')

p.table(48, 200, [196, 132, 132, 220], [
    ['费用（元）', 'A场', 'B场', 'B−A'],
    ['场地', '6,000', '6,000', '0'],
    ['物料', '2,000', '4,000', '+2,000'],
    ['师资', '4,000', '5,000', '+1,000'],
    ['合计', '12,000', '15,000', '+3,000'],
], bold_last=True)

p.table(748, 200, [160, 108, 108, 108], [
    ['活动', '预约', '实到', '到场率'],
    ['A场', '120', '96', '80%'],
    ['B场', '180', '126', ('70%', {'color': C['red'], 'bold': True})],
])

p.panel(748, 338, 484, 180)
p.label('两项增幅在同一尺度比较', 772, 350, 432, color='purple', bold=True)
p.bars(772, 386, 432, [('费用', 25.0, '费用 +25.0%'), ('实到', 31.3, '实到 +31.3%')])
p.note('实到增长快于费用增长，单位投入略降；\n两场基数不同，增幅不可直接相减为人数差。',
       772, 474, 432)

p.body([('每位实到费用由 ', {}), ('125', {'bold': True}), (' 元降至 ', {}),
        ('119.05', {'bold': True}), (' 元。', {})], 48, 440, 680)
p.body([('到场率降 10 个百分点', {'color': C['red'], 'bold': True}),
        ('，是本次唯一反向指标。', {})], 48, 482, 680)

p.rule(48, 530, 1184)
p.label([('场地 6,000 两场相同', {'color': C['purple'], 'bold': True}),
         ('\nB场预约增60组，场地费未增，扩场未增支。', {'color': C['secondary']})],
        48, 552, 384)
p.label([('物料 +2,000', {'color': C['purple'], 'bold': True}),
         ('\n折每场+1,000，对应新增60组家庭的资料与物料。', {'color': C['secondary']})],
        448, 552, 384)
p.label([('到场率 −10 个百分点', {'color': C['purple'], 'bold': True}),
         ('\n缺后续报名记录，不能判断招生转化。', {'color': C['secondary']})],
        848, 552, 384)
p.page_number()

# ============ P2 近距档 ============
q = deck.page('区间、顶点与最值', tier='near')
q.band(48, 112, 1184, 96,
       '已知 f(x)=x²−4x+1，x∈[−1,4]。求值域，并说明最值为何在相应位置取得。')

# 坐标系：x∈[-1.6,4.6] → [88,588]，y∈[-4.6,7.0] → [244,544]
X0, X1, Y0, Y1 = -1.6, 4.6, -4.6, 7.0
L, R, T, B = 88, 588, 244, 544
sx, sy = (R - L) / (X1 - X0), (B - T) / (Y1 - Y0)
px = lambda x: L + (x - X0) * sx
py = lambda y: B - (y - Y0) * sy

PH = py(Y0) - py(Y1)   # 绘图区高度，正值
for gx in range(-1, 5):
    q.rule(px(gx), py(Y1), 1, color='EDEDED', width=PH)
for gy in range(-4, 7):
    q.rule(L, py(gy), R - L, color='EDEDED', width=1)
q.rule(px(2), py(Y1), 1, color='C9C2D0', width=PH)               # 对称轴
q.rule(L - 24, py(0), R - L + 48, color='blue', width=1.5)       # x 轴
q.rule(px(0), py(Y1), 1, color='blue', width=PH)                 # y 轴
curve = [(px(-1 + 5 * i / 160), py((-1 + 5 * i / 160) ** 2 - 4 * (-1 + 5 * i / 160) + 1))
         for i in range(161)]
q.freeform(curve, color='blue', width=2.8)
for gx, gy in ((-1, 6), (2, -3), (4, 1)):
    q.dot(px(gx), py(gy), 5, 'blue')
q.note('(−1, 6)', px(-1) + 9, py(6) - 30, 90, color=C['red'])
q.note('(2, −3)', px(2) - 30, py(-3) + 10, 90, color=C['red'])
q.note('(4, 1)', px(4) - 62, py(1) - 34, 80, color=C['red'])
q.note('对称轴 x=2', px(2) + 10, py(Y1) + 2, 120)

q.subhead('f(x)=(x−2)²−3', 648, 224, 584)
q.body([('1　顶点落在区间内', {'bold': True}),
        ('\n2∈[−1,4]，平方项最小为 0，\n最小值 −3 在 x=2 处取得。', {})], 648, 272, 584)
q.body([('2　最大值看距离', {'bold': True}),
        ('\n左端距 3，右端距 2，距离越大值越大。', {})], 648, 393, 584)
q.body([('3　端点代入核对', {'bold': True}),
        ('\nf(−1)=6，f(4)=1，最大值 6。\n', {}),
        ('值域 [−3, 6]', {'color': C['red'], 'bold': True})], 648, 477, 584)

q.panel(48, 596, 1184, 54)
q.label([('独立变式', {'color': C['purple'], 'bold': True}),
         ('　x∈[0,3] 时的值域？说明依据。', {}),
         ('　先独立作答，再核对。', {'color': C['secondary']})], 72, 610, 1136)
q.page_number()

# ============ P3 远距档（整页出血） ============
r = deck.bleed_page(tier='far')
r.image(SKILL / 'assets' / 'hualang-university-fair-20260510.png', 0, 0, 1280, 720,
        focus=(0.5, 0.0))   # 全部从底部裁掉，避开原图右下角新闻水印；该图为新闻稿配图，正式使用须换授权原图
r.scrim(0, 0, 1280, 720,
        [(0.0, 0.90), (0.30, 0.84), (0.48, 0.40), (0.64, 0.0)], angle=0)
r.brand_mark(148, 44, 132)
r.lead('先独立判断，\n再解释依据。', x=148, y=190, w=560, color='white')
r.body('30 分钟二次函数微课堂\n孩子写下理由，家长看见思考过程', 148, 368, 560,
       color='F0ECF5', spacing=1.5)
r.rule(148, 494, 64, color='gold', width=2)
r.note('面向已认识抛物线顶点的高一学生及家长\n2026.5.10 校园开放日现场　拟议体验方案，非已公布活动',
       148, 514, 560, color='C9C2D0')
r.page_number(light=True)

out = deck.save(OUT / '华朗三档样张.pptx')
print('saved', out, out.stat().st_size // 1024, 'KB')
