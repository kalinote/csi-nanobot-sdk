{% if system == 'Windows' %}
## 平台策略（Windows）
- 你正在 Windows 上运行。不要假定存在 GNU 工具（如 `grep`、`sed` 或 `awk`）。
- 在更可靠时，优先使用 Windows 原生命令或文件类工具。
- 若终端输出乱码，请启用 UTF-8 输出后重试。
{% else %}
## 平台策略（POSIX）
- 你正在 POSIX 系统上运行。请优先使用 UTF-8 与标准 shell 工具。
- 当比 shell 命令更简单或更可靠时，请使用文件类工具。
{% endif %}
