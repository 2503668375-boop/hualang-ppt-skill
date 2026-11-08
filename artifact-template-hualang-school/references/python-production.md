# python-pptx 生产通道

`hualang-kit.mjs` 依赖 `@oai/artifact-tool`，该运行库只在特定宿主环境存在。缺少它时用本通道：同样是原生可编辑对象，坐标、字号、档位与品牌框架全部取自[样式契约](../assets/style-contract.json)和[场景视觉语法](scene-visual-grammar.md)。

依赖：`python-pptx`、`Pillow`。字体用系统已装的 PingFang SC，英文 Arial。

## V11 常规整稿入口

优先按[页面规格](deck-spec.md)编写 `deck-spec.json`，调用 `scripts/hualang_build.py`。统一构建器已经封装八类场景、分页、固定首尾、原生表格、课堂反馈和可选动画，常规任务无需逐页调用本文件中的底层方法。

```bash
python3 scripts/hualang_build.py --spec deck-spec.json --out 成品.pptx --report 构建报告.json
```

`scripts/hualang_tables.py` 负责按内容分配列宽、逐行测量、长表续页和表头重复。六类样式与字段见[表格系统](table-system-v11.md)。以下底层 API 用于特殊页面和局部精修。

## 最小骨架

```python
import sys
from pathlib import Path
SKILL = Path('/path/to/artifact-template-hualang-school')
sys.path.insert(0, str(SKILL / 'scripts'))
from hualang_deck import Deck, COLORS as C

deck = Deck(SKILL / 'assets' / 'source-original.pptx',
            title='开放日费用与到场', presenter='市场部', date='2026年11月8日')
p = deck.page('开放日费用与到场', tier='read')     # tier: read / near / far
p.lead('费用增25%、实到增31.3%，B场每位实到费用低4.8%')
p.context('模拟资料 · 非学校实绩；比较基准均为A场')
p.table(48, 200, [196, 132, 132, 220], [['费用（元）','A场','B场','B−A'], ...])
deck.save('成品.pptx')
```

`Deck` 打开原始模板，自动保留封面与封尾、删除中间的旧正文页；`page()` 新建正文页并画好校徽、金线、题名。封面题名、汇报人、汇报时间按契约坐标写入，封尾加培养目标与结束语。

只要正文、不要首尾时用 `Deck(..., content_only=True)`，产物用 `check_style_contract.py --content-only` 校验。

## 字号由档位决定

| 档位 | 题名 | 概论 | 小标题 | 正文 | 标注 | 注释 | 表内 | 表格行高 |
|---|---|---|---|---|---|---|---|---|
| `read` 留阅 | 28 | 33 | 26 | 21 | 17 | 14 | 19 | 底层默认46，V11表格按内容计算 |
| `near` 近距 | 30 | 42 | 32 | 26 | 21 | 17 | 23 | 底层默认46，V11表格按内容计算 |
| `far` 远距 | 30 | 64 | 44 | 34 | 26 | 20 | 26 | 底层默认54，V11表格按内容计算 |

传的是逻辑像素，库内部换算成 pt（×0.75）。同一主题要做成手册版和讲台版，先分别重组内容与证据，再设置相应 `tier`；切档后检查文字负载、图表、条件与办理信息是否可读，不能只改字号。

## 坐标来自 12 栏网格

正文区 x48–1232 / y112–650，步进 100。`col(n)` 返回第 n 栏左边界，`span(a, b)` 返回跨栏的 `(x, w)`。

```python
from hualang_deck import col, span
col(0), col(7)          # (48, 748)
span(0, 5)              # (48, 584)
```

主要分区优先参考 `48 + 100n` 共享对齐线，色面块内文字可另加 24 内距。表格单元格、图表节点和批注按内容定位，不要求逐个落在主网格。

## 方法

| 方法 | 用途 | 要点 |
|---|---|---|
| `title(text)` | 页眉题名 | 由 `page()` 自动调用，一般不手动调 |
| `lead(text, x=48, y=110, w=1184, runs=None)` | 概论／主判断 | 自动加粗，高度按字数估算 |
| `subhead / body / label / note / context` | 小标题、正文、标注、注释、口径 | 字号随档位，高度自动 |
| `panel(x,y,w,h, fill='pale')` | 浅紫分组底或证据底 | 面积按内容给，不做卡片墙 |
| `band(x,y,w,h, text, fill='purple')` | 深紫任务带、口径带 | 文字垂直居中，内距 26 |
| `rule / gold_rule` | 分隔线、金色短线 | 细线只分隔不同性质的材料 |
| `table(x, y, widths, rows, bold_last=False)` | 原生表格 | 表头深紫白字、行底线、首列左对齐其余右对齐 |
| `bars(x, y, w, items)` | 同尺度横向条 | `items=[(标签, 数值, 显示文本)]` |
| `image(path, x, y, w, h)` | 图片，默认按 cover 裁切 | 保留比例与关键动作 |
| `scrim(x, y, w, h, stops)` | 图上的深色渐变遮罩 | `stops=[(位置, 不透明度)]`，避免硬边色块 |
| `freeform(points, color='blue')` | 函数图像、关系折线 | 传像素坐标点序列，产物可编辑 |
| `dot(x, y)` | 关键点 | 配标注用 |
| `page_number(light=False)` | 页码 | 常规页右下角 1190/677；`light=True` 移到文字列左下 148/677 白色 |
| `bleed_page(tier='far')` | 整页出血页 | 图铺满 1280×720，无页眉无金线；题名由主张承担 |
| `brand_mark(x=148, y=44, w=132, light=True)` | 出血页校徽 | 默认金色版，压在深色画面上；`light=False` 用深色版 |
| `image(..., focus=(fx, fy))` | 裁切焦点 | `fy=0` 保留上部、裁掉底部（去水印）；`fx=0` 贴左 |

富文本用 runs：`[(文本, {选项}), ...]`，选项支持 `color`、`bold`、`size`、`italic`。单元格同样接受 `(文本, {选项})`。

```python
p.body([('到场率降 10 个百分点', {'color': C['red'], 'bold': True}),
        ('，是本次唯一反向指标。', {})], 48, 482, 680)
```

## 整页出血

对外实景页铺满画布，代码上就是 `bleed_page()` 而不是 `page()`：

```python
r = deck.bleed_page(tier='far')
r.image(photo, 0, 0, 1280, 720, focus=(0.5, 0.0))     # 贴底裁，避开原图水印
r.scrim(0, 0, 1280, 720, [(0.0, 0.90), (0.30, 0.84), (0.48, 0.40), (0.64, 0.0)])
r.brand_mark(148, 44, 132)                            # 金色校徽
r.lead('先独立判断，\n再解释依据。', x=148, y=190, w=560, color='white')
r.body('30 分钟二次函数微课堂\n孩子写下理由，家长看见思考过程', 148, 368, 560, color='F0ECF5')
r.rule(148, 494, 64, color='gold', width=2)
r.note('面向…\n2026.5.10 现场　拟议体验方案', 148, 514, 560, color='C9C2D0')
r.page_number(light=True)
```

`bleed_page` 只接受 `tier='far'`，传其他档位直接报错。出血页不出常规页眉题名，按样式契约核对品牌对象与主张文字；满版图片本身不代表出血页合格。品牌处理、遮罩取值与节奏安排见[场景视觉语法](scene-visual-grammar.md#整页出血对外专用)。

## 保存前自检

`save()` 会检查 `spPr` 与 `tcPr` 的子元素顺序。PowerPoint 对顺序敏感，填充排在描边之后会触发修复提示；顺序错了直接抛错并指出页与形状名，不写出坏文件。

这不是质量检查，只防结构性损坏。

## 校验顺序

```bash
python3 scripts/check_style_contract.py 成品.pptx --title "题名" --presenter "汇报人" --date "2026年11月8日"
python3 scripts/mirror_render.py 成品.pptx --out 预览/镜像.html
```

`check_style_contract.py` 核首尾字段、位置与题名规范。`mirror_render.py` 按最终文件里的真实坐标、字号、颜色重绘一份 HTML，用于辅助检查结构：它可核对文字内容、坐标与预期对象顺序，**不能**证明最终PPTX的字体替换、实际换行、母版继承和放映效果。

镜像不是 PowerPoint 渲染。正式交付前仍要在装了演示软件的机器上打开最终文件，核一次实际呈现；未做的放映与投影如实说明。

## 已知边界

- 不生成 SmartArt；原生文字、表格、图表元素、自由曲线以外的组合请用基础形状拼。
- `scrim` 只支持线性渐变；复杂蒙版请用多块半透明面叠。
- 渐变、描边、阴影以外的效果（三维、发光）不提供入口。
- 中文字体缺失时统一替换，再通过最终文件的实际渲染核对字形与换行；镜像仅作辅助，不改库源码。
- 表格数字未强制等宽字形，需要严格对齐时把数字列字体设为等宽西文字族。
