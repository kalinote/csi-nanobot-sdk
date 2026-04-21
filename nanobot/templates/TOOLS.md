# Tool Usage Notes

工具签名通过函数调用自动提供。
本文件说明非显而易见的约束与用法。

## exec — Safety Limits

- 命令有可调超时时间（默认 60 秒）
- 危险命令会被拦截（如 rm -rf、format、dd、shutdown 等）
- 输出在 10,000 个字符处截断
- `restrictToWorkspace` 配置可将文件访问限制在工作区内

## glob — File Discovery

- 在退回到 shell 命令之前，先用 `glob` 按模式查找文件
- 诸如 `*.py` 的简单模式会按文件名递归匹配
- 需要匹配目录而非文件时使用 `entry_type="dirs"`
- 使用 `head_limit` 与 `offset` 对大型结果集分页
- 若只需文件路径，优先使用本工具而非 `exec`

## grep — Content Search

- 使用 `grep` 在工作区内搜索文件内容
- 默认行为只返回匹配的文件路径（`output_mode="files_with_matches"`）
- 支持可选的 `glob` 过滤，以及 `context_before` / `context_after`
- 支持 `type="py"`、`type="ts"`、`type="md"` 等简写过滤器
- 对于包含正则特殊字符的纯字面关键词，使用 `fixed_strings=true`
- 使用 `output_mode="files_with_matches"` 仅获取匹配的文件路径
- 使用 `output_mode="count"` 在读取完整匹配前先估量搜索规模
- 使用 `head_limit` 与 `offset` 对结果分页
- 搜索代码与历史记录时优先使用本工具而非 `exec`
- 二进制或过大的文件可能被跳过，以保持结果可读
