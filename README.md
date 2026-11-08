# 华朗学校汇报与教学 Skill

当前版本 **v11.0.1**。在 V11.0 更新包基础上完成发布前审查和修订，按华朗独立品牌制作可编辑的校务汇报、教案、课堂、练习、家长沟通、招生与公众演讲材料。

## V11 的主要变化

- **八类教育场景**：区分校务决策、教师教案与说课、学生课堂、练习复习、个体家长反馈、班级家长会、招生开放日和公众演讲，分别组织问题、证据和行动。
- **三档观看条件**：留阅、近距、远距分别设置文字层级、内容负载和图文重心。参数是起排参考，实际材料与可读性决定最终页面。
- **统一整稿入口**：助手从主题与附件组织页面规格，由 Python 构建器输出原生可编辑 PPTX；原有 JavaScript 底层通道继续支持定制精修。
- **六类表格**：比较、矩阵、日程、评价等按列类型与内容分配空间，长表按完整数据行续页，重复表头、保留口径及合计。
- **学习任务与反馈分开**：课堂及练习保留独立作答、答案反馈页和指定步骤的点击出现；未验证的应用播放不作承诺。

[![三档视觉样张](artifact-template-hualang-school/assets/tier-strip.png)](artifact-template-hualang-school/assets/python-3tiers.pptx?raw=true)

[三档可编辑样张](artifact-template-hualang-school/assets/python-3tiers.pptx?raw=true) · [场景系统](artifact-template-hualang-school/references/scenario-system-v11.md) · [视觉语法](artifact-template-hualang-school/references/scene-visual-grammar.md) · [本次验证](tests/v11-validation.md)

常规正文保留近白底、左题右徽与金线。远距实景主视觉允许按专项规范整页出血，使用金色校徽和清楚主张；固定原始封面、封尾及培养目标“华夏俊采，朗若星辰”继续保留。历史样张按[样张索引](artifact-template-hualang-school/references/sample-index.md)的版本和适用范围使用。

## 本次审查修订

修复了超量条目静默丢失、负数横条误画为正向、部分批注越界及出血页标题检查过宽等问题；统一网格、表格行高、场景转换及结构镜像的说明。构建容量不足时给出具体错误或支持的续页处理，不靠截断内容或缩字完成。

三档样张与九组场景输入均用于功能及页面检查，示例的模拟、原创、拟议属性须保留。文件生成成功、程序检查和 AI 审查均不代表真实教学成效或用户审美认可。详细范围见[验证记录](tests/v11-validation.md)。

## 开始使用

下载或安装完整目录，保留模板、图片、参考文件与工具：

> 从 https://github.com/2503668375-boop/hualang-ppt-skill 安装或更新 artifact-template-hualang-school，保留旧版备份及完整资源。

制作时附实际资料，直接说明读者、用途、形式、署名和日期，例如：

> 用华朗学校汇报技能，把附件费用和实到记录做成校务会议PPT，保留比较、差额、判断条件和可编辑对象。

教学补充教材或课程体系、学科年级、课时与已知基础；家长与招生提供作品、真实照片和当期条件。助手只追问影响内容正确性或正式采用的缺项。无需用户编写规格或代码。

[下载完整仓库 ZIP](https://github.com/2503668375-boop/hualang-ppt-skill/archive/refs/heads/main.zip) · [技能入口](artifact-template-hualang-school/SKILL.md) · [上手说明](artifact-template-hualang-school/references/getting-started.md) · [版本记录](CHANGELOG.md)

## 制作与验证边界

Python 通道依赖 `python-pptx`、`Pillow`，原有 JavaScript 通道依赖支持的原生制作运行库。八类场景示例及一组长表位于 `artifact-template-hualang-school/assets/examples/`，入口见[页面规格](artifact-template-hualang-school/references/deck-spec.md)；特殊图形和复杂学科对象使用底层通道精修。

最终 PPTX 应由实际演示引擎打开后导出并检查。结构镜像只辅助核对内容与坐标，不能证明最终字形、换行和播放效果。本次未完成 Microsoft PowerPoint 应用内放映、现场投影或真实教学成效验证，也未穷尽所有学段学科。
