# 整稿页面规格与生产入口 V11

用户只提供主题、内容或资料。执行助手负责读取、研究、策划和写入页面规格；`scripts/hualang_build.py` 负责稳定生成完整 PPTX。

## 1. 从用户输入到成品

1. 提取主题、用途、读者、场地、时长、页数、署名、日期、事实状态和交付范围。已给信息直接沿用。
2. 只有主题时，先确定最可能的场景与用途；影响学校事实、课程范围、政策适用或公开采用的信息缺失时，列出具体缺项。允许先做草稿时，用明确待补项，不虚构数据、人物、成果或日期。
3. 有附件时读取原文、表格、图片和已有页面，保留数据口径、完整题目、作品细节与素材来源。外部补充资料只用于有依据的内容，记录来源。
4. 按[教育场景系统](scenario-system-v11.md)选择一个主场景。混合材料按读者拆成多份成品；确需同稿混合时逐页指定 tier 与版式。
5. 先写页序与每页核心回答，再转换为 `deck-spec.json`。每页只保留一个主对象，必要时使用续页。
6. 运行构建器，检查构建报告、样式契约、序列和最终文件。表格规则见[表格系统](table-system-v11.md)。

```bash
python3 scripts/hualang_build.py \
  --spec /绝对路径/deck-spec.json \
  --out /绝对路径/华朗主题汇报.pptx \
  --report /绝对路径/构建报告.json
```

依赖 `python-pptx`、`Pillow`。完整稿自动保留原封面和封尾；`content_only: true` 仅生成正文。

## 2. 整稿字段

```json
{
  "schema_version": "1.0",
  "title": "阅读支持课程实施方案",
  "scenario": "internal_report",
  "audience": "校务会",
  "presenter": "课程中心",
  "date": "2026年11月",
  "content_only": false,
  "closing_text": "汇报完毕，敬请指导",
  "slides": []
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | 是 | 正式封面题名，沿用用户题名或具体议题 |
| `scenario` | 是 | 八类场景或中文别名 |
| `slides` | 是 | 正文页数组，按叙事顺序排列 |
| `audience` | 建议 | 实际读者，供内容策划与报告记录 |
| `presenter` / `date` | 完整稿必填 | 缺失时可先准备规格，正式构建前补齐 |
| `content_only` | 否 | true 时不生成封面封尾，也无需署名日期 |
| `closing_text` | 否 | 按场合覆盖默认结束语 |

## 3. 页面通用字段

| 字段 | 用途 |
|---|---|
| `layout` | 版式；省略或 auto 时按字段自动选择 |
| `title` | 页面具体议题或判断 |
| `lead` | 统领本页的概论、核心判断或学习主旨 |
| `context` | 统计期、样本、模拟属性、资料范围等辅助口径 |
| `body` | 主体说明，容量随场景和档位控制 |
| `items` | 2–4 个相关要点，每项 title/body |
| `tier` | read / near / far，覆盖场景默认值 |
| `image` | 相对技能目录或绝对图片路径 |
| `caption` | 图片内容、时间、范围或署名 |
| `source` | 数据或材料来源 |
| `reveal` | process / lesson 支持，true 时登记点击出现 |

图片缺失时可以省略 `image`，并填写 `image_title`、`image_brief` 生成明确留位。核心证据未补前，不把相关结论写成已证实事实。

## 4. 版式与字段

### statement / image

用于主张、章节、舞台主视觉和收束。far 档默认整页出血；near/read 保留品牌页眉。`text_side` 可选 left/right，用于按图片主体位置安排文字，也能让开场与收束形成左右呼应。

```json
{
  "layout": "statement",
  "title": "让每一次表达都有依据",
  "lead": "让孩子说出判断，\n也说出文本依据。",
  "body": "阅读微课堂 · 学生作品与课堂观察",
  "image": "assets/reading-scene.png",
  "context": "真实素材需确认授权与拍摄日期",
  "tier": "far"
}
```

### comparison

用于同口径比较、疑虑与回应、方案取舍、前后变化。`split` 默认 0.5，可按内容调整。

```json
{
  "layout": "comparison",
  "title": "两种支持路径的条件",
  "left": {"title": "课堂内支持", "body": "适用对象、具体动作、资源与限制"},
  "right": {"title": "导师跟进", "body": "适用对象、复核方式、责任与节点"}
}
```

### table

见[表格系统](table-system-v11.md)。长表自动续页并重复表头。

### metrics

用于 1–4 个同口径关键指标。每个指标含 value、label、note；note 标统计范围。

```json
{
  "layout": "metrics",
  "title": "本学期阅读参与情况",
  "metrics": [
    {"value": "86%", "label": "任务提交率", "note": "模拟数据 · 七年级两个班"},
    {"value": "2次", "label": "人均修订", "note": "同一作品前后版本"}
  ],
  "context": "正式稿须替换为已核实记录"
}
```

### bars

用于 2–7 项同尺度比较。series 含 label、value、display，value 为数值，display 为带单位显示文本。

### timeline

steps 含 date、title、body。read 每页至多 5 个节点，near/far 至多 4 个，自动续页。日期未定时使用阶段文字，不虚构具体日期。

### process

steps 含 title、body。用于家校动作、办理流程、协作步骤。`reveal: true` 时逐步出现。

### activity

教师教案专用序列。steps 含 time、task、expected、feedback；每页 3 个活动，自动续页。

```json
{
  "layout": "activity",
  "title": "阅读证据链活动安排",
  "steps": [
    {
      "time": "8分钟",
      "task": "圈出支持人物判断的两处词句",
      "expected": "学生能指出动作与语言描写",
      "feedback": "若只找形容词，追问哪一处动作能验证"
    }
  ]
}
```

### lesson

用于学生课堂。task 为完整任务；work 或 image 为主对象；prompts 为分段提示；independent_task 保留独立作答。

```json
{
  "layout": "lesson",
  "title": "文本证据与人物判断",
  "task": "阅读完整选段，用两处词句说明人物判断，并写出理由。",
  "work": "在此保留完整原文、题目、公式或实验材料。",
  "prompts": [
    {"body": "先圈出人物的动作与语言。"},
    {"body": "再写明词句与判断之间的联系。"}
  ],
  "independent_task": "换一个段落，独立写出证据链。",
  "answer": "反馈页呈现参考答案、判据与常见错误。",
  "reveal": true
}
```

`answer` 自动生成独立反馈页。无动画基础稿与 `.reveals.json` 一并保留，最终 PPTX 写入原生出现效果。

### practice

questions 为完整题组，每项可含 body、hint、bold。read 每页 3 题，near 每页 2 题。answers 或 answer 自动生成独立答案与判据页。

### evidence

用于学生作品、活动记录、实景与批注。image 为主对象，items 为就近观察，action 为家庭或教学动作，orientation 可选 left/right。

## 5. 场景验收

- `internal_report`：至少保留比较、指标、数据图或取舍页，以及责任条件。
- `lesson_plan`：至少一个 activity，包含任务、预期回应和评价调整。
- `classroom`：完整学习对象、关键提示、独立任务与反馈；答案分页或分态。
- `practice`：完整题组、作答空间、答案与判据分页。
- `parent_growth`：至少一个 evidence，家庭动作与复核条件明确。
- `parent_meeting`：班级范围、统一节点、家校分工与沟通渠道明确。
- `admissions`：真实体验、课程适配、当期条件与一个主要行动入口。
- `public_address`：核心主张、具体证据、数据口径与参与方式。

构建报告记录场景、页数、每页版式、表格分页与警告。警告需要人工回到内容或版式处理，不能忽略后宣称完成场景适配。

## 容量与完整性

当前构建器对同页可容纳的条目设明确技术边界：主张页最多3项、比较页每侧最多3项、指标最多4项、横条最多7项、证据观察最多4项、课堂追问最多4项、反馈观察最多3项。这些是当前版式实现的容量，并非内容策划配额；超过时应拆页或改用底层精修，构建器会报出源页与字段，不会截断输入。

长表按完整数据行续页；证据观察可按完整条目续页，重复同一作品及口径，行动提示留在最后一页。单项本身过长时明确报错，返回内容重排。远距出血主张页不接收观察列表；把要点另排正文。留阅、近距的图片主张页使用图文证据布局保留图片。

通用横条仅支持有限的非负数，`max_value`须为正且不小于全部数据。涉及负值、变化方向或零基线时，使用保留符号的表格或定制图表。
