# 场景版式与实际样例

现行样例见 `assets/scene-examples.pptx` 与 `assets/scene-preview.png`。它们演示完整内容如何组织，不能把案例主题复制进所有任务。

| 观看任务 | 可用入口/组件 | 页面主体 |
|---|---|---|
| 内部查数与判断 | `addReportPage` 或普通页＋原生图表/表格 | 主证据优先，差额/原因/行动在相邻区域 |
| 两道数学短题 | `addMathPage({mode:'pair'})` | 两题分别保持题干、留白、解答；依次揭示 |
| 单道数学综合题 | `addMathPage({mode:'single'})` | 完整题干带、推导区、固定图形区 |
| 纯推导或长证明 | `addMathPage({mode:'proof'})` | 通栏推导，按逻辑单元揭示；过长续页 |
| 实验观察 | `addLessonPage` | 观察对象与问题贴近；这只是观察页入口 |
| 文本证据分析 | 普通页＋原文/批注 | 完整语段、行号、证据标注与解释 |
| 家长招生照片组 | `addPhotoEssay` | 一主两辅的图文区域，可按内容重新划分 |
| 数字或演讲重点 | `addEditorial` 或 `addStage` | 数字、主张或图像在远距可读，口径邻近 |
| 家长留阅信息 | 原生比较表/路径/信息页 | 条件、费用、日期和下一步完整 |

旧的 `addParentPage` 只适合宽幅图＋短说明，不作为所有家长任务的默认入口。旧的 `addLessonPage` 只适合观察课件，不承担所有学科的教学。

先读[构图方法](composition.md)，按任务读取[数学专项](math-teaching.md)、[学科版式](subject-layouts.md)、[家长与招生](parent-admissions.md)。具体参数见[制作API](production-api.md)。

遮住场景标签后，仍应能从实际对象、面积、阅读顺序与揭示过程理解页面用途。组件数量、图片比例和固定卡片数不能代替这个检验。
