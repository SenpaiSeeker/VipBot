import ast
import asyncio
import base64
import contextlib
import html
import importlib
import inspect
import io
import json
import logging
import os
import platform
import pprint
import random
import re
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from time import time
from typing import Any, Dict, Optional, Tuple

import pyrogram
from pyrogram import filters
from pyrogram.types import LinkPreviewOptions, Message, ReplyParameters

from . import command, ctx, is_bot_owner, listen

if not hasattr(ctx, "eval_history"):
    ctx.eval_history = {
        "last_code": None,
        "last_result": None,
        "last_stdout": None,
        "last_error": None,
        "last_time": None,
    }

def shell(code: str) -> str:
    try:
        return subprocess.check_output(code, shell=True, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        return e.output

def get_eval_payload(message: Message) -> str:
    cmd_len = len(message.command) if hasattr(message, "command") and message.command else 0
    text = message.text or message.caption or ""
    if cmd_len > 0:
        prefix_len = len(text.split()[0])
        args = text[prefix_len:].strip()
    else:
        args = ""
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            args = parts[1]
    if args:
        return args
    if message.reply_to_message:
        target_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        return target_text
    return ""

async def resolve_awaitables(obj: Any) -> Any:
    if inspect.iscoroutine(obj) or inspect.isawaitable(obj):
        return await obj
    return obj

def create_exec_scope(client: pyrogram.Client, message: Message, **kwargs) -> Dict[str, Any]:
    if not hasattr(ctx, "kwargs"):
        ctx.kwargs = {}
    scope = {
        "client": client,
        "c": client,
        "app": client,
        "message": message,
        "m": message,
        "msg": message,
        "r": message.reply_to_message,
        "rep": message.reply_to_message,
        "ctx": ctx,
        "db": ctx.db,
        "manager": getattr(ctx, "manager", None),
        "bots": ctx.manager.running_bots if hasattr(ctx, "manager") else None,
        "asyncio": asyncio,
        "os": os,
        "sys": sys,
        "re": re,
        "json": json,
        "random": random,
        "datetime": datetime,
        "timedelta": timedelta,
        "traceback": traceback,
        "io": io,
        "base64": base64,
        "logging": logging,
        "platform": platform,
        "shutil": shutil,
        "inspect": inspect,
        "importlib": importlib,
        "pyrogram": pyrogram,
        "shell": shell,
        "sh": shell,
        "print": pprint.pformat,
        "chat": message.chat,
        "user": message.from_user if message.from_user else client.me,
    }
    scope.update(kwargs)
    return scope

async def aexec(code: str, client: pyrogram.Client, message: Message, **kwargs) -> Any:
    exec_scope = create_exec_scope(client, message, **kwargs)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        tree.body[-1] = ast.Return(value=tree.body[-1].value)
    func_def = ast.AsyncFunctionDef(
        name="__aexec",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=k) for k in exec_scope.keys()],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
            vararg=None,
            kwarg=ast.arg(arg="kwargs"),
        ),
        body=tree.body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    ast.fix_missing_locations(func_def)
    module = ast.Module(body=[func_def], type_ignores=[])
    compiled_src = compile(module, filename="<ast>", mode="exec")
    exec(compiled_src, exec_scope)
    runner = exec_scope["__aexec"]
    result = await runner(**exec_scope)
    return await resolve_awaitables(result)

def format_output(
    client: pyrogram.Client,
    code: str,
    result: Any,
    stdout_val: str,
    stderr_val: str,
    exc_str: Optional[str],
    exec_time: float,
) -> Tuple[str, str]:
    final_output = ""
    status_header = "Success"
    if exc_str:
        final_output = exc_str.strip()
        status_header = "Error"
    elif stderr_val:
        final_output = stderr_val.strip()
        status_header = "Stderr"
    elif stdout_val:
        final_output = stdout_val.strip()
        if result is not None:
            final_output += f"\n---\nReturn: {str(result)}"
    elif result is not None:
        final_output = str(result).strip()
    else:
        final_output = "None"
    
    escaped_code = html.escape(code)
    escaped_output = html.escape(final_output)

    out_len_limit = 777
    short_output = escaped_output[:out_len_limit] + "..." if len(escaped_output) > out_len_limit else escaped_output

    display_text = f"<b>{client.ns.emoji.zap} Input:</b>\n"
    display_text += f"<pre><code class='language-python'>{escaped_code}</code></pre>\n\n"
    display_text += f"<b>{client.ns.emoji.laptop} Output ({status_header}):</b>\n"
    display_text += f"<pre><code>{short_output}</code></pre>\n\n"
    display_text += f"<b>{client.ns.emoji.hourglass} Time: </b><code>{exec_time:.4f}s</code>"

    return display_text, final_output

async def execute_and_format(
    client: pyrogram.Client, message: Message, code: str, **kwargs
) -> Tuple[str, Any, Optional[io.BytesIO]]:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = None
    exc_traceback = None
    start_time = time()
    
    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            result = await asyncio.wait_for(aexec(code, client, message, **kwargs), timeout=60.0)
    except asyncio.TimeoutError:
        exc_traceback = f"{client.ns.emoji.cross_mark} TimeoutError: Execution exceeded 60 seconds."
    except asyncio.CancelledError:
        exc_traceback = "CancelledError: Execution was cancelled."
    except Exception:
        exc_traceback = traceback.format_exc()
    
    end_time = time()
    execution_time = end_time - start_time
    stdout_val = stdout_capture.getvalue()
    stderr_val = stderr_capture.getvalue()
    
    ctx.eval_history.update(
        {
            "last_code": code,
            "last_result": str(result) if result is not None else None,
            "last_stdout": stdout_val,
            "last_error": exc_traceback or stderr_val,
            "last_time": execution_time,
        }
    )
    
    display_text, raw_output = format_output(
        client,
        code,
        result,
        stdout_val,
        stderr_val,
        exc_traceback,
        execution_time,
    )
    
    document = None
    if len(raw_output) > 777:
        document = io.BytesIO(str.encode(raw_output))
        document.name = "output.txt"
    
    layout = [
        [
            {
                "text": "Run Again",
                "callback_data": f"eval_run_{message.chat.id}_{message.id}",
                "style": "green"
            },
            {
                "text": "Delete",
                "callback_data": f"eval_del_{message.chat.id}_{message.id}",
                "style": "red"
            },
        ]
    ]
    keyboard = client.ns.telegram.button.build_button_grid(layout)
    
    return display_text, keyboard, document

@command(lambda ctx: filters.command("eval") & filters.user(ctx.owner_id))
async def eval_bot_handler(client: pyrogram.Client, message: Message):
    code = get_eval_payload(message)
    if not code:
        return await message.reply(f"{client.ns.emoji.cross_mark} Berikan kode untuk dievaluasi atau balas ke sebuah pesan.")
    
    status_msg = await message.reply(f"{client.ns.emoji.repeat} <code>Memproses kode...</code>")
    try:
        text, keyboard, document = await execute_and_format(client, message, code, update=message)
        if document:
            await status_msg.delete()
            await message.reply_document(
                document=document,
                caption=text,
                reply_markup=keyboard,
                reply_parameters=ReplyParameters(message_id=message.id),
            )
        else:
            await status_msg.edit_text(text, reply_markup=keyboard, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as e:
        error_text = f"<b>Kesalahan Handler:</b>\n<code>{html.escape(str(traceback.format_exc()))}</code>"
        if status_msg:
            try:
                await status_msg.edit_text(error_text)
            except Exception:
                await message.reply(error_text)
        else:
            await message.reply(error_text)

@command(
    lambda ctx: filters.regex(r"^eval_") & filters.user(ctx.owner_id),
    handler_type="callback"
)
async def eval_callback_handler(client: pyrogram.Client, query: pyrogram.types.CallbackQuery):
    data = query.data.split("_")
    if len(data) < 4:
        return
    
    action = data[1]
    chat_id = int(data[2])
    message_id = int(data[3])
    
    if action == "del":
        try:
            await client.delete_messages(chat_id, [message_id, query.message.id])
        except Exception:
            await query.answer("Tidak bisa menghapus pesan.")
    
    elif action == "run":
        try:
            trigger_message = await client.get_messages(chat_id, message_id)
            code = get_eval_payload(trigger_message)
            if not code:
                return await query.answer("Kode tidak ditemukan untuk dijalankan kembali.", show_alert=True)
            
            await query.answer("Menjalankan kembali kode...")
            
            text, keyboard, document = await execute_and_format(
                client,
                trigger_message,
                code,
                update=query,
            )

            if code.endswith("return"):
                return            
            
            is_current_msg_media = bool(query.message.document or query.message.photo)
            
            if document:
                if is_current_msg_media:
                    await query.edit_message_media(
                        media=pyrogram.types.InputMediaDocument(media=document, caption=text),
                        reply_markup=keyboard
                    )
                else:
                    await query.message.delete()
                    await client.send_document(
                        chat_id=chat_id,
                        document=document,
                        caption=text,
                        reply_markup=keyboard,
                        reply_parameters=ReplyParameters(message_id=message_id),
                    )
            else:
                if is_current_msg_media:
                    await query.message.delete()
                    await client.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=keyboard,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                        reply_parameters=ReplyParameters(message_id=message_id),
                    )
                else:
                    await query.edit_message_text(
                        text=text,
                        reply_markup=keyboard,
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    )
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)