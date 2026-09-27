"""Telegram Bot interface for algo-compare."""

from __future__ import annotations

import html
import os
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from algocomp.comparator import compare
from algocomp.registry import Registry, default_registry
from algocomp.static_analysis import analyze_source, expr_label

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8732668889:AAHJT2JZKFdLGTY4BfYWGWoOn_t_qmSYDQo")

_REGISTRY: Optional[Registry] = None


def get_registry() -> Registry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = default_registry()
    return _REGISTRY


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "⚡ <b>Welcome to AlgoCompare Bot!</b>\n\n"
        "Compare algorithm theoretical complexities and perform static Big-O analysis directly on Telegram.\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/compare &lt;algo1&gt; &lt;algo2&gt;</code> - Compare two algorithms\n"
        "  <i>e.g. /compare merge_sort quick_sort</i>\n"
        "• <code>/info &lt;algo&gt;</code> - View full Big-O profile\n"
        "  <i>e.g. /info timsort</i>\n"
        "• <code>/list [category]</code> - List catalogued algorithms\n"
        "• <code>/categories</code> - View all supported categories\n"
        "• <code>/analyze &lt;code&gt;</code> - Estimate Big-O complexity of Python code\n\n"
        "💡 <i>Tip: You can also upload a .py file or paste code directly to analyze it!</i>"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)
async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reg = get_registry()
    cats = reg.categories()
    lines = ["📚 <b>Supported Categories:</b>\n"]
    for cat in cats:
        algos = reg.filter(category=cat)
        lines.append(f"• <b>{html.escape(cat)}</b>: {len(algos)} algorithms")
    lines.append("\nUse <code>/list &lt;category&gt;</code> to view algorithms in any category.")
    if update.message:
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reg = get_registry()
    args = context.args or []
    if args:
        cat = args[0].strip().lower()
        algos = reg.filter(category=cat)
        if not algos:
            matches = [c for c in reg.categories() if cat in c.lower()]
            msg = f"❌ Category <code>{html.escape(cat)}</code> not found."
            if matches:
                msg += f"\nDid you mean: {', '.join(f'<code>{m}</code>' for m in matches)}?"
            if update.message:
                await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            return

        lines = [f"📂 <b>Category: {html.escape(cat)}</b> ({len(algos)} algorithms)\n"]
        for a in algos:
            lines.append(f"• <code>{html.escape(a.key)}</code> — {html.escape(a.name)}")
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3900] + "\n... (truncated)"
        if update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        total = len(reg)
        cats = reg.categories()
        lines = [
            f"📊 <b>AlgoCompare Catalog: {total} algorithms</b> across {len(cats)} categories.\n",
            "Specify a category: <code>/list &lt;category&gt;</code>\n",
            "<b>Popular categories:</b>"
        ]
        for c in cats[:10]:
            count = len(reg.filter(category=c))
            lines.append(f"• <code>{html.escape(c)}</code> ({count})")
        lines.append("\nUse <code>/categories</code> to see all categories.")
        if update.message:
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "Usage: <code>/info &lt;algo_key&gt;</code>\nExample: <code>/info merge_sort</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    reg = get_registry()
    key = context.args[0].strip()
    algo = reg.get(key)
    if not algo:
        matches = [k for k in reg.keys() if key.lower() in k.lower()]
        hint = f"\nDid you mean: {', '.join(f'<code>{m}</code>' for m in matches[:5])}?" if matches else ""
        if update.message:
            await update.message.reply_text(
                f"❌ Algorithm <code>{html.escape(key)}</code> not found.{hint}",
                parse_mode=ParseMode.HTML,
            )
        return

    txt = [
        f"🔍 <b>{html.escape(algo.name)}</b> (<code>{html.escape(algo.key)}</code>)",
        f"📁 Category: <i>{html.escape(algo.category)}</i> | Task: <i>{html.escape(algo.task)}</i>\n",
        "<b>Time Complexity:</b>",
        f"  • Best:    <code>{html.escape(str(algo.time.best))}</code>",
        f"  • Average: <code>{html.escape(str(algo.time.average))}</code>",
        f"  • Worst:   <code>{html.escape(str(algo.time.worst))}</code>\n",
        "<b>Space Complexity:</b>",
        f"  • Worst:   <code>{html.escape(str(algo.space.worst))}</code>\n",
        "<b>Properties:</b>",
        f"  • Stable: {'✅ Yes' if algo.stable else ('❌ No' if algo.stable is False else '➖ N/A')}",
        f"  • In-place: {'✅ Yes' if algo.in_place else ('❌ No' if algo.in_place is False else '➖ N/A')}",
    ]
    if algo.description:
        txt.append(f"\n<b>Description:</b>\n{html.escape(algo.description)}")

    if update.message:
        await update.message.reply_text("\n".join(txt), parse_mode=ParseMode.HTML)


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) < 2:
        if update.message:
            await update.message.reply_text(
                "Usage: <code>/compare &lt;algo1&gt; &lt;algo2&gt;</code>\n"
                "Example: <code>/compare merge_sort quick_sort</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    reg = get_registry()
    k1 = context.args[0].strip()
    k2 = context.args[1].strip()

    a1 = reg.get(k1)
    a2 = reg.get(k2)

    if not a1:
        if update.message:
            await update.message.reply_text(f"❌ Unknown algorithm: <code>{html.escape(k1)}</code>", parse_mode=ParseMode.HTML)
        return
    if not a2:
        if update.message:
            await update.message.reply_text(f"❌ Unknown algorithm: <code>{html.escape(k2)}</code>", parse_mode=ParseMode.HTML)
        return

    verdict = compare(a1, a2)

    lines = [
        f"⚔️ <b>Comparison: {html.escape(a1.name)} vs {html.escape(a2.name)}</b>\n",
        "<b>Time Complexity:</b>",
        f"• Best:    {html.escape(str(a1.time.best))} vs {html.escape(str(a2.time.best))}",
        f"• Average: {html.escape(str(a1.time.average))} vs {html.escape(str(a2.time.average))}",
        f"• Worst:   {html.escape(str(a1.time.worst))} vs {html.escape(str(a2.time.worst))}\n",
        "<b>Space Complexity (Worst):</b>",
        f"• {html.escape(str(a1.space.worst))} vs {html.escape(str(a2.space.worst))}\n",
        "<b>Analysis & Verdict:</b>",
        f"{html.escape(verdict.conclusion())}"
    ]

    if update.message:
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


def _format_analysis_result(est, filename: str = "snippet") -> str:
    lines = [
        f"🔬 <b>Static Complexity Estimate:</b> <code>{html.escape(filename)}</code>",
        f"Target Function: <code>{html.escape(str(est.details.get('function', '<module>')))}</code>\n",
        "<b>Time Complexity:</b>",
        f"  • Best:    <code>{html.escape(expr_label(est.time_best))}</code>",
        f"  • Average: <code>{html.escape(expr_label(est.time_average))}</code>",
        f"  • Worst:   <code>{html.escape(expr_label(est.time_worst))}</code>\n",
        f"<b>Space Complexity:</b> <code>{html.escape(expr_label(est.space))}</code>",
        f"<b>Confidence:</b> {est.confidence * 100:.0f}%\n",
        "<b>Notes & Heuristics:</b>"
    ]
    for note in est.notes:
        lines.append(f"  • {html.escape(note)}")

    return "\n".join(lines)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = ""
    if context.args:
        code = " ".join(context.args)

    if not code:
        if update.message:
            await update.message.reply_text(
                "Usage: <code>/analyze &lt;python code&gt;</code> or send a Python code snippet / .py file.",
                parse_mode=ParseMode.HTML
            )
        return

    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]

    est = analyze_source(code.strip())
    result = _format_analysis_result(est, "snippet.py")
    if update.message:
        await update.message.reply_text(result, parse_mode=ParseMode.HTML)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document if update.message else None
    if not doc or not doc.file_name or not doc.file_name.endswith(".py"):
        if update.message:
            await update.message.reply_text("Please upload a Python (.py) file to analyze.")
        return

    tg_file = await context.bot.get_file(doc.file_id)
    file_bytes = await tg_file.download_as_bytearray()
    source = file_bytes.decode("utf-8", errors="replace")

    est = analyze_source(source, filename=doc.file_name)
    result = _format_analysis_result(est, doc.file_name)
    if update.message:
        await update.message.reply_text(result, parse_mode=ParseMode.HTML)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text if update.message else None
    if not text:
        return

    is_code = (
        text.startswith("```")
        or ("def " in text and ":" in text)
        or ("for " in text and "in " in text)
        or ("while " in text and ":" in text)
    )
    if is_code:
        code = text
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]

        est = analyze_source(code.strip())
        result = _format_analysis_result(est, "code_snippet.py")
        if update.message:
            await update.message.reply_text(result, parse_mode=ParseMode.HTML)


def main() -> None:
    token = BOT_TOKEN
    print(f"Starting AlgoCompare Telegram Bot with token prefix: {token[:10]}...")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("compare", compare_command))
    app.add_handler(CommandHandler("analyze", analyze_command))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is polling. Ready to receive commands...")
    app.run_polling()


if __name__ == "__main__":
    main()

