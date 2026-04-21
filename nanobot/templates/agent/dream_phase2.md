根据下方分析更新记忆文件。
- [FILE] 条目：将所述内容添加到对应文件
- [FILE-REMOVE] 条目：从记忆文件中删除对应内容
- [SKILL] 条目：使用 write_file 在 skills/<name>/SKILL.md 下创建新技能

## File paths (relative to workspace root)
- SOUL.md
- USER.md
- memory/MEMORY.md
- skills/<name>/SKILL.md（仅用于 [SKILL] 条目）

不要臆测路径。

## Editing rules
- 直接编辑 — 下方已提供文件内容，无需 read_file
- 将 old_text 设为与原文完全一致，并包含前后空行以保证唯一匹配
- 对同一文件的修改合并为一次 edit_file 调用
- 删除时：将小节标题及所有列表项作为 old_text，new_text 留空
- 仅做精准编辑 — 切勿重写整个文件
- 若无需更新，则停止且不调用工具

## Skill creation rules (for [SKILL] entries)
- 使用 write_file 创建 skills/<name>/SKILL.md
- 写入前，read_file `{{ skill_creator_path }}` 以参考格式（frontmatter 结构、命名约定、质量标准）
- **去重检查**：读下方列出的已有技能，确认新技能在功能上不与现有技能重复。若已有技能覆盖同一工作流，则跳过创建。
- 包含带 name 与 description 字段的 YAML frontmatter
- SKILL.md 控制在 2000 词以内 — 简明、可执行
- 须包含：何时使用、步骤、输出格式、至少一个示例
- 勿覆盖已有技能 — 若技能目录已存在则跳过
- 引用智能体可用的具体工具（read_file、write_file、exec、web_search 等）
- 技能是指令集而非代码 — 不要包含实现代码

## Quality
- 每行须有独立价值
- 在清晰小标题下使用简明列表项
- 压缩（非删除）时：保留关键事实，删去冗长细节
- 若不确定是否删除，则保留并加上「（请核实时效性）」
