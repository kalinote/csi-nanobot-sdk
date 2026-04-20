from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

from loguru import logger

from nanobot.agent.hook import AgentHook, AgentHookContext
from nanobot.nanobot import Nanobot


def _install_console_logger() -> None:
    """统一使用 loguru 输出，并避免控制台编码导致崩溃。"""

    def _safe_sink(message: Any) -> None:
        text = str(message)
        enc = sys.stdout.encoding or "utf-8"
        try:
            sys.stdout.write(text)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(text.encode(enc, errors="replace"))

    logger.remove()
    logger.add(_safe_sink, level="INFO")


@dataclass(slots=True)
class _RunOptions:
    config_path: Path
    workspace: str | None
    session_key: str
    message: str
    stream: bool
    verbose_hook: bool


class PrintHook(AgentHook):
    """用于验证 hook 生命周期是否生效的最小示例。"""

    def __init__(self, *, stream: bool, verbose: bool = False) -> None:
        super().__init__()
        self._stream = stream
        self._verbose = verbose

    def wants_streaming(self) -> bool:
        return self._stream

    async def before_iteration(self, context: AgentHookContext) -> None:
        logger.info("[Hook] 开始迭代：{}", context.iteration)
        if self._verbose:
            last = context.messages[-1] if context.messages else None
            if last:
                role = last.get("role")
                content = last.get("content")
                if isinstance(content, str):
                    preview = content[:120] + ("..." if len(content) > 120 else "")
                else:
                    preview = "<非文本内容>"
                logger.info("[Hook] 最后一条消息：role={} content={}", role, preview)

    async def on_stream(self, context: AgentHookContext, delta: str) -> None:
        # 这里的 delta 是“增量文本”，不会包含 <think> 之类的隐藏块（由核心 loop 清洗）
        logger.opt(raw=True).info(delta)

    async def on_stream_end(self, context: AgentHookContext, *, resuming: bool) -> None:
        if self._stream:
            logger.opt(raw=True).info("\n")
        if self._verbose:
            logger.info("[Hook] 流式结束：resuming={}", resuming)

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        # 基础对话测试一般不会触发工具；这里打印出来方便你确认是否有工具调用
        if context.tool_calls:
            logger.info("[Hook] 即将执行工具：{} 个", len(context.tool_calls))
            if self._verbose:
                for tc in context.tool_calls[:5]:
                    logger.info("[Hook] 工具：{} 参数键={}", tc.name, list(tc.arguments.keys()))

    async def after_iteration(self, context: AgentHookContext) -> None:
        usage = context.usage or {}
        if usage:
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            cached = usage.get("cached_tokens", 0)
            logger.info(
                "[Hook] 本轮用量：prompt={} completion={} cached={}",
                prompt,
                completion,
                cached,
            )

        if context.stop_reason:
            logger.info("[Hook] 停止原因：{}", context.stop_reason)
        if context.error:
            logger.error("[Hook] 错误：{}", context.error)


def _parse_args(argv: list[str] | None = None) -> _RunOptions:
    p = argparse.ArgumentParser(description="nanobot 功能测试脚本（对话 + hook）")
    p.add_argument(
        "--config",
        default="config.json",
        help="配置文件路径（默认：仓库根目录 config.json）",
    )
    p.add_argument(
        "--workspace",
        default=None,
        help="覆盖配置中的 workspace（可选）",
    )
    p.add_argument(
        "--session",
        default="sdk:test",
        help="会话 key（默认：sdk:test）",
    )
    p.add_argument(
        "--message",
        default="你好，请用一句话自我介绍，并说明你支持哪些 provider。",
        help="发送给 nanobot 的消息（默认提供一个简单测试问题）",
    )
    p.add_argument(
        "--stream",
        action="store_true",
        help="开启流式输出（会触发 hook.on_stream）",
    )
    p.add_argument(
        "--verbose-hook",
        action="store_true",
        help="hook 输出更多上下文（消息预览/工具信息等）",
    )
    ns = p.parse_args(argv)
    return _RunOptions(
        config_path=Path(ns.config),
        workspace=ns.workspace,
        session_key=str(ns.session),
        message=str(ns.message),
        stream=bool(ns.stream),
        verbose_hook=bool(ns.verbose_hook),
    )


async def _run_once(opts: _RunOptions) -> None:
    config_path = opts.config_path
    if not config_path.is_absolute():
        config_path = (Path(__file__).resolve().parent / config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"找不到配置文件：{config_path}")

    bot = Nanobot.from_config(config_path=str(config_path), workspace=opts.workspace)

    hook = PrintHook(stream=opts.stream, verbose=opts.verbose_hook)

    if opts.stream:
        # Nanobot.run() 当前只返回最终内容；流式文本在 hook.on_stream 里打印
        await bot.run(opts.message, session_key=opts.session_key, hooks=[hook])
        return

    result = await bot.run(opts.message, session_key=opts.session_key, hooks=[hook])
    logger.info(result.content)


def main(argv: list[str] | None = None) -> int:
    try:
        _install_console_logger()
        opts = _parse_args(argv)
        asyncio.run(_run_once(opts))
        return 0
    except KeyboardInterrupt:
        logger.warning("已取消。")
        return 130
    except Exception:
        logger.exception("运行失败")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

