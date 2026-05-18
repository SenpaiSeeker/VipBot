import ast
import asyncio
import contextlib
import html
import io
import os
import sys
import time
import traceback
import json
import re
import base64
import platform
import shutil
import importlib
import inspect
from datetime import datetime, timedelta
from typing import Any

import pyrogram
from pyrogram import Client
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw.types import (
    UpdateBotGuestChatQuery,
    PeerUser,
    InputBotInlineResult,
    InputBotInlineMessageText,
    InputBotInlineResultDocument,
    InputBotInlineMessageMediaAuto,
    InputDocument,
    InputMediaUploadedDocument,
    DocumentAttributeFilename
)
from pyrogram.raw.functions.messages import SetBotGuestChatResult, UploadMedia

from VvipBot import ctx

def create_exec_scope(client: Client, update) -> dict:
    return {
        "client": client,
        "c": client,
        "app": client,
        "update": update,
        "ctx": ctx,
        "db": getattr(ctx, "db", None),
        "asyncio": asyncio,
        "os": os,
        "sys": sys,
        "re": re,
        "json": json,
        "time": time,
        "datetime": datetime,
        "timedelta": timedelta,
        "traceback": traceback,
        "io": io,
        "base64": base64,
        "platform": platform,
        "shutil": shutil,
        "inspect": inspect,
        "importlib": importlib,
        "pyrogram": pyrogram,
    }

async def aexec(code: str, client: Client, update) -> Any:
    exec_scope = create_exec_scope(client, update)
    tree = ast.parse(code)
    
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
    
    if inspect.iscoroutine(result) or inspect.isawaitable(result):
        return await result
    return result

async def process_eval(client, code, update):
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = None
    exc_str = None
    start_time = time.perf_counter()

    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            result = await asyncio.wait_for(aexec(code, client, update), timeout=60.0)
    except asyncio.TimeoutError:
        exc_str = "TimeoutError: Execution exceeded 60 seconds."
    except Exception:
        exc_str = traceback.format_exc()

    end_time = time.perf_counter()
    execution_time = end_time - start_time

    stdout_val = stdout_capture.getvalue()
    stderr_val = stderr_capture.getvalue()

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

    display_text = f"<b>Input:</b>\n<pre>{escaped_code}</pre>\n\n<b>Output ({status_header}):</b>\n<pre>{escaped_output}</pre>\n\n<b>Time:</b> <code>{execution_time:.4f}s</code>"

    if len(display_text) > 4000:
        doc = io.BytesIO(final_output.encode("utf-8"))
        doc.name = "eval_result.txt"
        caption = f"<b>Input:</b>\n<pre>{escaped_code}</pre>\n\n<b>Output ({status_header}):</b>\n<i>Output dikirim sebagai dokumen.</i>\n\n<b>Time:</b> <code>{execution_time:.4f}s</code>"
        if len(caption) > 1024:
            caption = caption[:1000] + "..."
        return True, caption, doc
    else:
        return False, display_text, None

async def guest_chat_query_handler(client: Client, update, users, chats):
    if isinstance(update, UpdateBotGuestChatQuery):
        msg = update.message
        user_id = None
        
        if hasattr(msg, "from_id") and isinstance(msg.from_id, PeerUser):
            user_id = msg.from_id.user_id
        elif hasattr(msg, "peer_id") and isinstance(msg.peer_id, PeerUser):
            user_id = msg.peer_id.user_id
            
        if user_id == getattr(client, "owner_id", None):
            code = msg.message
            if not code:
                return

            code = re.sub(r'^@[a-zA-Z0-9_]+\s+', '', code)

            is_doc, text_or_caption, doc = await process_eval(client, code, update)
            
            if is_doc:
                uploaded_file = await client.save_file(doc)
                media_res = await client.invoke(
                    UploadMedia(
                        peer=await client.resolve_peer("me"),
                        media=InputMediaUploadedDocument(
                            file=uploaded_file,
                            mime_type="text/plain",
                            attributes=[DocumentAttributeFilename(file_name="eval_result.txt")]
                        )
                    )
                )
                input_doc = InputDocument(
                    id=media_res.document.id,
                    access_hash=media_res.document.access_hash,
                    file_reference=media_res.document.file_reference
                )
                
                inline_result = InputBotInlineResultDocument(
                    id="0",
                    type="file",
                    title="Eval Output",
                    document=input_doc,
                    send_message=InputBotInlineMessageMediaAuto(
                        message=text_or_caption
                    )
                )
            else:
                inline_result = InputBotInlineResult(
                    id="0",
                    type="article",
                    title="Eval Output",
                    send_message=InputBotInlineMessageText(
                        message=text_or_caption
                    )
                )
            
            await client.invoke(SetBotGuestChatResult(
                query_id=update.query_id,
                result=inline_result
            ))

def setup_guest_chat_query(client: Client, owner_id: int):
    client.owner_id = owner_id
    client.add_handler(RawUpdateHandler(guest_chat_query_handler), group=1)
