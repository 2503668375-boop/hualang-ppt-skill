# 教育场景系统 V11

先确定读者、使用动作和观看距离，再确定证据、页序和主对象。华朗品牌保持一致，八类场景分别组织内容。

## 1. 场景路由

| scenario | 典型请求 | 读者要完成的事 | 默认档位 | 首选版式 |
|---|---|---|---|---|
| `internal_report` | 校务会、经营复盘、教学质量、招生复盘、费用审议 | 比较、判断、取舍、落实 | read | comparison / table / metrics / bars / timeline |
| `lesson_plan` | 教案、备课、说课、教研审议 | 理解设计依据并直接实施 | read | activity / lesson / process / rubric table |
| `classroom` | 初高中及国际课程课堂课件 | 观察、推理、作答、获得反馈 | near | lesson / evidence / comparison / process |
| `practice` | 练习、复习、检测、讲评 | 独立作答、核对判据、订正迁移 | read；投影可 near | practice / comparison / table |
| `parent_growth` | 个体成长反馈、学生面谈、作品反馈 | 看见孩子的具体变化并配合支持 | near | evidence / comparison / process |
| `parent_meeting` | 班级家长会、政策说明、家校协同 | 理解班级安排、明确家庭动作与节点 | near | statement / metrics / timeline / table |
| `admissions` | 招生宣讲、开放日、课程咨询 | 形成体验认知、比较课程、完成报名 | far；办理页 near/read | statement / image / comparison / table |
| `public_address` | 成果发布、公众演讲、合作交流、品牌介绍 | 记住主张、理解证据、建立信任 | far | statement / image / metrics / evidence |

中文别名可直接写入规格：内部汇报、校务、教案、说课、课堂、练习、复习、家长反馈、家长会、招生、开放日、公众、成果发布。完整别名见 `scripts/hualang_build.py`。

### 同材料跨场景处理

共用已经核实的事实，重新组织读者问题与证据。以“阅读支持”为例：

- 校务会呈现参与分布、同口径变化、匿名样本、资源条件与待决事项。
- 教师教案呈现完整文本、设问、预期回应、评价判据与再教动作。
- 学生课堂呈现原文、关键词句、推理提示、独立任务与反馈。
- 个体家长反馈呈现孩子作品前后、具体词句变化、家庭动作与复核日期。
- 班级家长会呈现班级范围、共同目标、家校分工与统一节点。
- 招生开放日呈现真实课堂体验、课程适配、当期办理条件与预约动作。
- 公众成果发布呈现一个核心主张、代表性学生作品或项目，以及可核实成果。

总体均值不能写成个体进步，一次作品修订不能写成稳定掌握，建筑照片不能写成教学成效。

## 2. 八类内容与版式骨架

### 2.1 校务决策与内部汇报

**推荐页序**：结论与口径 → 同口径比较 → 差距或构成 → 原因及边界 → 方案取舍 → 责任与节点。

- 标题写出具体议题或判断，页面保留统计期、样本量、单位与事实状态；原始出处及计算留底稿。
- 主图或主表按信息负载与观看条件安排，解释贴近对应数据；完整明细可占较大面积，少量数据不机械放大。
- 比较页使用共同基准；差额、比例与绝对人数分别标明。
- 表格优先 `comparison`、`editorial`、`schedule`；责任清单用 `checklist`。
- 待决事项写出选项、代价、约束与责任；已定事项保留原安排。

### 2.2 教师教案与说课

**推荐页序**：学情与障碍 → 目标与判据 → 任务序列 → 预期回应 → 评价与调整 → 作业及再教。

- `activity` 每行对应一个活动，字段为时间、任务、预期回应、评价与调整。
- 关键题例或文本另给完整页，避免把学习材料压成教案中的一个短句。
- 说课增加设计取舍依据；教案保留教师可直接执行的语言与资源。
- 评价量规用 `rubric`，课时安排用 `schedule`；活动序列优先原生区域排版。

### 2.3 学生课堂

**推荐页序**：完整学习对象 → 关键关系 → 分段提示 → 条件变化或反例 → 独立任务 → 反馈。

- 题目、原文、图形或实验对象占主区域；提示与对应对象相邻。
- 复杂推理拆成学习单元，点击出现只承担分段提示或反馈。
- 每页突出一个学习动作，减少与目标无关的装饰、照片和重复文字。
- 独立任务与答案分态或分页；`answer` 默认生成独立反馈页。
- 表格只用于真实对比、记录或评价，避免把推导过程塞进窄单元格。

### 2.4 练习复习与检测

**推荐页序**：目标或方法 → 示范 → 独立题组 → 诊断 → 变式迁移 → 答案与判据。

- 短题可按每页 2–3 个完整任务起排，大题与复杂材料按完整对象安排；保留作答空间、条件和题源，不为凑题数压缩内容。
- 题组改变条件、表示或情境，避免只替换数字。
- 答案与判据默认独立成页；课堂投影可改 near，打印练习用 read。
- 错因对照用 comparison；掌握记录用简单 `matrix` 或 `checklist`。

### 2.5 个体家长成长反馈

**推荐页序**：作品或记录 → 可观察变化 → 仍有困难 → 学校支持 → 家庭动作 → 复核。

- 作品、作答或活动照片给足可辨认空间，可从正文 50%–65% 起排；批注指到具体词句、步骤或动作，不为面积比例裁掉关键证据。
- 前后对照保持相同任务或相同评价口径，标注时间与样本范围。
- 家庭建议写成 1–3 个可执行动作，给出频率、时长或复核条件。
- 个体信息注意匿名与授权；班级均值只用于背景参考。

### 2.6 班级家长会与家校协同

**推荐页序**：共同目标 → 班级现状 → 课程与活动安排 → 家校分工 → 时间节点 → 沟通渠道。

- 班级范围与学期口径置于相应页面，避免个体化推断。
- 政策内容精确到年份、批次与适用对象，未公布事项写待确认。
- 日程用 timeline 或 `schedule`；家校动作用 process 或 `checklist`。
- 现场讲解用 near，带走手册另做 read 版本。

### 2.7 招生开放日与课程选择

**推荐页序**：教育命题 → 真实学习体验 → 学生作品与成长 → 课程适配 → 安全与关怀 → 当期条件 → 报名动作。

- 舞台页使用全幅真实场景、短主张或关键证据；30–80 字是远距起排参考，关键条件和完整对象按实际负载保留。
- 课程比较使用共同维度，写清适合对象、学习体验和选择条件。
- 费用、时间、材料和办理条件转为 near/read 查询页，保留有效日期。
- 结尾只保留一个主要动作：预约、咨询或报名，并配真实渠道。
- 不使用无法核实的排名、升学承诺、绝对化表述或未经授权的未成年人肖像。

### 2.8 公众成果发布与主题演讲

**推荐页序**：核心主张 → 人物/事件/作品 → 关键数据 → 方法或机制 → 代表成果 → 合作或参与方式。

- 每页一个记忆点，大图、大数字、原文或单一关系承担主视觉。
- 复杂比较单独留页，连续大图页之间要有事件或论据承接。
- 数据标年份、范围和来源；合作成果区分已发生、拟议和预测。
- 公众版减少内部过程术语，把学校工作翻译成学生成长与社会价值。

## 3. 研究转化为排版规则

1. **单一内容与层级**：国家开放大学建议每页呈现单一内容、层级不超过三级、每行一项；教案可以保留完整活动，舞台页进一步减少文字。
2. **安全区与字级**：高校公开课程规范要求 16:9、四周留白、统一字体和清晰对比；华朗沿用 12 栏网格与 read/near/far 三档，不机械套用单一字号。
3. **认知负载**：Mayer 的 coherence、signaling、segmenting、spatial contiguity 原则对应删减无关元素、突出关键条件、分段呈现、图文相邻。
4. **表格可读性**：Microsoft 建议使用简单数据表、明确表头，避免合并、拆分和嵌套单元格；颜色之外保留文字或符号。
5. **对外叙事**：学校招生材料围绕安全、学习、被如何对待、成长与办理条件展开；真实日常、学生作品和具体场景优先于抽象口号。

## 4. 调研来源

- 国家开放大学：《演示文稿（PPT）的制作标准》  
  https://www.ouchn.edu.cn/jgjzn/jxkyglyfwbm/xxzybsztsg/zybzxxzy/967cf61888b143ac8be14c7c256876d9.htm
- 河南城建学院：《课程建设标准及要求》  
  https://jwc.huuc.edu.cn/info/1046/2927.htm
- 东北石油大学：《学校对外宣讲幻灯片模板及说明》  
  https://dzbgs.nepu.edu.cn/info/1421/4711.htm
- UC San Diego：Instructional Multimedia  
  https://digitallearning.ucsd.edu/instructors/online-teaching-essentials/multimedia.html
- TU Delft：Create impactful multimedia  
  https://www.delft.university/en/teaching-support/educational-advice/develop/create-impactful-multimedia
- Issa 等：Effects of applying multimedia design principles in PowerPoint lecture redesign  
  https://www.sciencedirect.com/science/article/pii/S187712971530006X
- Microsoft：Make your PowerPoint presentations accessible  
  https://support.microsoft.com/en-us/accessibility/powerpoint/make-your-powerpoint-presentations-accessible-to-people-with-disabilities
- Microsoft：PowerPoint—Use table headers  
  https://support.microsoft.com/en-us/accessibility/powerpoint/powerpoint-use-table-headers

量化参数以华朗样式契约为准。外部资料用于确定场景结构与可读性原则，未采用无法追溯原始研究的传播效果百分比。
