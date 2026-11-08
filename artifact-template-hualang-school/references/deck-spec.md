# 整稿页面规格与生产入口

用户只提供主题、内容或资料。执行助手负责读取、研究、策划和写入页面规格；`scripts/hualang_build.py` 负责稳定生成完整 PPTX。

## 1. 从用户输入到成品

1. 提取主题、用途、读者、场地、时长、页数、署名、日期、事实状态和交付范围。已给信息直接沿用。
2. 只有主题时，先确定最可能的场景与用途；影响学校事实、课程范围、政策适用或公开采用的信息缺失时，列出具体缺项。允许先做草稿时，用明确待补项，不虚构数据、人物、成果或日期。
3. 有附件时读取原文、表格、图片和已有页面，保留数据口径、完整题目、作品细节与素材来源。外部补充资料只用于有依据的内容，记录来源。
4. 按[教育场景系统](scenario-system-v11.md)选择一个主场景。混合材料按读者拆成多份成品；确需同稿混合时逐页指定 tier 与版式。
5. 先写页序与每页核心回答，再转换为 `deck-spec.json`。每页只保留一个主对象，必要时使用续页。
6. 运行构建器，检查构建报告、样式契约、序列和最终文件。表格规则见[表格系统](table-system-v11.md)。

V12 管理汇报完整输入见 `assets/examples/internal-report-v12.json`，覆盖八类新增主对象、逐页内容合同、整稿质量门禁与派生指标复算；示例全部使用模拟数据。

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
| `strict_quality` | 否 | 兼容字段，默认 true；当前内容与节奏均给人工复核提示，字段丢失、无效数据和计算错误始终阻断，不依赖此开关 |
| `calculations` | 有派生指标时填写 | 在独立底稿记录比较主体、基准、视角、期间、单位、公式、输入、预期与容差；页面只保留必要业务口径 |
| `source_notes` | 否 | 独立底稿的原始出处及资料说明，不进入观众页面 |

`calculations` 示例：

```json
{
  "comparison_id": "simulated_course_cost_3yr",
  "subject": "模拟课程方案每生费用变化",
  "baseline": "方案甲1.2万元、方案乙1.0万元，均为每学年",
  "perspective": "家庭三学年总费用减少",
  "period": "三学年，模拟比较",
  "unit": "万元/生/三学年",
  "formula": "(price_a - price_b) * years",
  "inputs": {"price_a": 1.2, "price_b": 1.0, "years": 3},
  "expected": 0.6,
  "tolerance": 0.000001
}
```

## 3. 页面通用字段

| 字段 | 用途 |
|---|---|
| `layout` | 版式；省略或 auto 时按字段自动选择 |
| `role` | 可选的管理页角色：opening / context / diagnosis / evidence / options / execution / decision / closing / appendix；其他场景按实际使用单元组织 |
| `reader_question` | 本页直接回答的读者问题 |
| `new_information` | 本页新增的事实、复算、解释、方案或安排 |
| `appendix` | true 时标记资料附页，不参与正文版式比例计算 |
| `title` | 页面具体议题或判断 |
| `lead` | 统领本页的概论、核心判断或学习主旨 |
| `context` | 统计期、样本、模拟属性、资料范围等辅助口径 |
| `body` | 主体说明，容量随场景和档位控制 |
| `basis` | 补充事实、解释、比较条件；字符串或 `{title, body}`，当前通用版式放在主体下方；内部不填原始出处、算法或核验过程 |
| `action` | 有需要时写本页事实推出的动作、代价或后果；常规版式放在主体下方，不要求每页都填 |
| `items` | 2–4 个相关要点，每项 title/body |
| `tier` | read / near / far，覆盖场景默认值 |
| `image` | 相对技能目录或绝对图片路径 |
| `caption` | 图片内容、时间、范围或署名 |
| `source` / `table.source` | 数据或材料出处；`internal_report` 中仅留独立构建报告，其他场景按引用需要显示 |
| `reveal` | process / lesson 支持，true 时登记点击出现 |
| `task_label` | lesson 底部任务标签；教案默认“实施提示”，学生材料按实际学习动作命名 |

管理原始出处填写 `source` 或顶层 `source_notes`，观众需要的期间、单位、分母和模拟属性填写 `context` 或对应数据标签。内部原始出处及计算记录不放 `basis`、备注或附录。

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

见[表格系统](table-system-v11.md)。长表自动续页并重复表头。`basis` 与 `action` 只在最后一页落位，表格高度预先为其留位。内部 `table.source` 留在独立底稿，可见口径使用 `context` 或列标题。

```json
{
  "layout": "table",
  "title": "阅读支持安排",
  "lead": "模拟方案优先支持需要持续反馈的学生",
  "context": "模拟材料 · 一学期 · 人数按去重学生统计",
  "basis": {"title": "实施条件", "body": "基础活动面向全体；专项支持按同一评价任务识别，参与量不能直接证明学习改善。"},
  "action": "拟在课时允许时先试行一轮，再根据独立作答调整支持范围。",
  "table": {"style": "comparison", "columns": [], "rows": []}
}
```

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

### positioning

用于价格×分数、规模×成果等双轴定位。`x_axis` / `y_axis` 含 `label / min / max / unit`；`points` 含 `label / x / y / color / display_x / display_y / note`；可选 `x_reference / y_reference`。所有点使用原生对象和直接标签，轴域必须覆盖数值。

### waterfall

用于目标、缺口、贡献与补平。`steps` 含 `label / value / display / kind / color / note`，`kind` 为 `start / delta / total`，支持正负值；推算、计划和实际状态在文字中分开。

### trend

用于连续届别、月份或季度。`categories` 为期间标签；`series` 含 `label / color / values / displays`；`y_axis` 含 `min / max / unit / label`。各系列点数与期间数一致，零基线、比例和百分点按指标含义使用。

### diagnostic

用于原因、风险与区域诊断。`items` 含 `title / evidence / implication / action / status`。事实与解释假设分别表达，没有家庭或过程记录时不写成确定因果。

### targets

用于当前值、目标与差额。`items` 含 `label / current / target / delta / note / color`。目标为建议值时写明拟议，比例同时保留人数或分母。

### conversion

用于咨询、预约、到访、测评、录取、缴费报到。`stages` 含 `label / definition / target / owner`，阶段跟踪同一去重对象；未知基线写“待补”或建基线日期，不伪造转化率。

### swimlane

用于跨部门时间与责任。`periods` 为连续阶段；`lanes` 含 `label / owner / tasks`；任务含 `start / end / label / deliverable / status`，`start / end` 为 `periods` 的 0 基索引，可跨列。只登记真实或拟议任务，状态不省略。

### decision

用于校董会、校务会审议。`items` 含 `title / decision / recommendation / reason / owner / date`，分别写审议事项、建议、依据、责任和节点；没有真实待决事项时不使用该版式。按实际文字高度以完整事项续页，不能把超量内容截断或缩为不可读字号。

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

用于学生课堂。task 为完整任务；work 或 image 为主对象；prompts 为分段提示；independent_task 保留独立作答。教案可用同一对象详解任务，底部默认标“实施提示”；`task_label` 可按用途覆盖，不把教师实施要求写成学生独立作答。

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

### annotated：原文与近邻批注

适用于已有原文、作答或记录，需要指出具体词句怎样支持判断、怎样修订。`source_blocks` 保留完整材料单元，`annotations.target` 精确关联其 `id`；没有原文时不采用。原文占宽幅连续区域，批注靠近相应段落，不能把“亮点、问题、建议”随意塞成另一列泛话。

```json
{
  "layout": "annotated", "title": "人物判断的依据", "tier": "near",
  "context": "原创模拟作答，用于局部反馈",
  "source_title": "学生作答摘录",
  "source_blocks": [{"id": "reason", "text": "他把伞给同桌，所以他很好。"}],
  "annotations": [{"target": "reason", "label": "解释选择的代价",
    "comment": "“很好”没有说明行为怎样支持判断。",
    "rewrite": "他愿意自己淋雨，把仅有的伞让给同桌，说明他关心同学。"}]
}
```

`rewrite` 可省；`source_blocks.id` 唯一且每条批注必须找到原文。按完整段落与对应批注续页；单个单元过长会报错，不截原文、不遗漏修订。若关联材料必须同屏理解，执行者应改用更合适的页面尺寸、阅读档或底层组合，不能接受自动分页后关系断裂。

### revision：同一对象的对应修订

适用于前后稿、初次与再次作答、已修改的规则或安排。`changes` 每项包含 `label / before / after / reason`，原稿、修订稿与理由在同一行对应；中间修订稿获得较大宽度。`before_label / after_label` 可按实际版本命名。没有前后材料，不补造变化；短例只能证明该项修订，不能推断长期成长。

```json
{
  "layout": "revision", "title": "表达变化与家庭支持", "tier": "read",
  "context": "模拟个体反馈 · 同一作答前后版本",
  "before_label": "初稿", "after_label": "修订稿",
  "changes": [{"label": "限定评价范围", "before": "他每次都把别人放在第一位。",
    "after": "在这次雨中送伞的选择里，他表现出对同桌的关心。",
    "reason": "单个片段只支持此次选择，不能推断“每次”都如此。"}],
  "boundary": "本次修订得到过提示，尚不能证明已掌握独立分析。"
}
```

### tradeoff：共同尺度与实施代价

适用于存在真实备选项、需要比较投入与适用条件的材料。横条只编码同一指标，文本列逐项保留适用问题、其他代价和成立条件。`metric` 含 `label / unit` 与可选 `max`；`options` 每项含 `name / value / fit / cost / condition`，可选 `display / color`。`value` 仅接受非负有限数，`max` 必须覆盖全部值；续页保持同一零基线和比例。

```json
{
  "layout": "tradeoff", "title": "新教师支持方案", "tier": "read",
  "context": "拟议方案演示 · 同一学期模拟预算",
  "metric": {"label": "新增预算", "unit": "万元", "max": 12},
  "options": [
    {"name": "集中培训", "value": 12, "fit": "共性教学方法缺口",
     "cost": "占用集中培训时间，后续仍需课堂练习", "condition": "课程内容与具体难题对应"},
    {"name": "共同备课", "value": 0, "fit": "任务设计与课堂执行困难",
     "cost": "每组每周1小时，需要导师投入", "condition": "课表可安排共同时间"}
  ],
  "recommendation": {"option": "按困难类型安排支持", "why": "方法与执行困难需要不同支持。"},
  "boundary": "问题分布与可用工时待补，暂不能决定最终预算分配。"
}
```

`recommendation` 可为文字或 `{option, why}`，按材料状态保留建议属性。新增预算为零不等于没有成本；无法量化的代价保留具体文字，不伪造评分。无同口径指标时用比较表或定制开放比较，不为调用组件制造数字。

以上组合支持 `lead / context / body / basis / action / boundary / recommendation`，字段必须实际呈现。容量按段落测量；按完整单元续页，单项过长明确报错。组件没有固定条目配额，也不能代替内容策划。可运行输入见 `assets/examples/content-components.json`；局部混排方法见 [python-pptx通道](python-production.md#材料组件的局部组合)。

## 5. 场景验收

- `internal_report`：至少保留比较、指标、数据图或取舍页，以及责任条件。
- `lesson_plan`：至少一个 activity，包含任务、预期回应和评价调整。
- `classroom`：完整学习对象、关键提示、独立任务与反馈；答案分页或分态。
- `practice`：完整题组、作答空间、答案与判据分页。
- `parent_growth`：至少一个 evidence，家庭动作与复核条件明确。
- `parent_meeting`：班级范围、统一节点、家校分工与沟通渠道明确。
- `admissions`：真实体验、课程适配、当期条件与一个主要行动入口。
- `public_address`：核心主张、具体证据、数据口径与参与方式。

构建报告记录场景、页数、每页版式、分页、错误与复核提示。`quality` 的版式关系数、表格占比和连续节奏只是人工审稿线索；管理内容提示不强加给课堂和演讲。`calculations` 记录公式复算与比较语义，错误不因 `strict_quality: false` 而放行。技术构建成功仍须按[成品验收](review.md)检查内容、场景和实际页面。

`content_review` 从最后保存的 PPTX 回读可见文字，定位数量堆砌、绝对承诺、制作术语和重复段落等候选复读项。其状态始终要求人工复读；无提示不等于内容正确、充分或视觉合格。

内部汇报正文达到 8 页时，少于 6 类内容关系、表格超过45%、连续4个独立输入页少于3类会触发复核提示。必要续表、同口径核对和连续推理可按内容保留，并检查实际阅读作用；不为数值配额虚构关系或拆薄内容。`appendix: true` 只用于真实资料附页，不能隐藏正文重复。

## 容量与完整性

当前构建器对同页可容纳的条目设明确技术边界：主张页最多3项、比较页每侧最多3项、指标最多4项、横条最多7项、证据观察最多4项、课堂追问最多4项、反馈观察最多3项。这些是当前版式实现的容量，并非内容策划配额；超过时应拆页或改用底层精修，构建器会报出源页与字段，不会截断输入。

长表按完整数据行续页；证据观察可按完整条目续页，重复同一作品及口径，行动提示留在最后一页。单项本身过长时明确报错，返回内容重排。远距出血主张页不接收观察列表；把要点另排正文。留阅、近距的图片主张页使用图文证据布局保留图片。

通用横条仅支持有限的非负数，`max_value`须为正且不小于全部数据。涉及负值、变化方向或零基线时，使用支持符号的 waterfall / trend、表格或定制图表。

新增诊断、目标和审议版式允许从一个完整事项起排；转化过程至少两个真实阶段。条目数是工具容量边界，不是内容配额。输入的 `context / body / basis / action` 若当前版式没有实际呈现，构建器会报错；按该版式字段重组或使用底层精修，不能仅删去必要内容使构建通过。管理原始 `source / table.source` 是留底稿的明确例外。

泳道任务按时间占用分配纵轨，同一责任方的不重叠任务可以共用基线；实际重叠才分轨。任务文字与责任保持可读字号，放不下时重组或拆页，不自动缩字。阶段宽度按离散列展示，不代表不同阶段的真实时长比例。

完整模拟业务输入另见 `assets/examples/library-trial.json`：原始统计、问卷口径、拟议预算、派生指标与责任安排由同一份材料形成连续报告，不以版式库存构成页序。
