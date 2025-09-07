"""基于 NoneBot2 的 QQ 接收器实现"""
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
import re

from loguru import logger
from uvicorn import Server, Config

import nonebot
from nonebot import on_message, on_request
from nonebot.adapters.onebot.v11 import (
    Adapter as OneBotV11Adapter,
    Bot,
    MessageEvent,
    PrivateMessageEvent,
    GroupMessageEvent,
    FriendRequestEvent,
)

from receivers.base import BaseReceiver
from core.database import get_db
from core.models import MessageCache, BlackList
from sqlalchemy import select, and_  # type: ignore


class QQReceiver(BaseReceiver):
    """QQ 接收器（NoneBot2 + OneBot v11）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("qq_receiver", config)
        self.app = None
        self.server: Optional[Server] = None
        self.friend_request_cache: Dict[str, float] = {}
        self.suppression_cache: Dict[str, list] = {}
        # 注入的服务
        self.audit_service = None
        self.submission_service = None
        self.notification_service = None
        # 撤回事件处理：是否开启
        self.enable_recall_delete: bool = True

    def set_services(self, audit_service, submission_service, notification_service):
        """注入服务实例供指令处理使用"""
        self.audit_service = audit_service
        self.submission_service = submission_service
        self.notification_service = notification_service

    async def initialize(self):
        await super().initialize()

        # 初始化 NoneBot（注入 OneBot 鉴权配置）
        access_token = self.config.get("access_token")
        if access_token:
            try:
                import os
                # 常见环境变量名，尽量兼容
                os.environ.setdefault("ONEBOT_ACCESS_TOKEN", str(access_token))
                os.environ.setdefault("ONEBOT_V11_ACCESS_TOKEN", str(access_token))
            except Exception:
                pass

        # 确保使用 FastAPI 驱动
        try:
            import os
            os.environ.setdefault("DRIVER", "~fastapi")
        except Exception:
            pass

        nonebot.init()
        driver = nonebot.get_driver()
        # 通过运行时配置再次注入（适配不同版本）
        try:
            if access_token:
                setattr(driver.config, "onebot_access_token", access_token)
        except Exception:
            pass
        driver.register_adapter(OneBotV11Adapter)

        # 注册事件处理
        self._setup_handlers()

        # 获取 ASGI 应用
        self.app = nonebot.get_asgi()
        # 尝试添加健康检查路由
        try:
            from fastapi import FastAPI

            if isinstance(self.app, FastAPI):
                @self.app.get("/health")  # type: ignore
                async def _health():
                    return {"status": "healthy", "receiver": "qq"}
        except Exception:
            pass
        self.logger.info("NoneBot2 初始化完成，已注册 OneBot v11 适配器")

    def _setup_handlers(self):
        """注册 NoneBot 事件处理器"""

        msg_matcher = on_message(priority=50, block=False)

        @msg_matcher.handle()
        async def _(bot: Bot, event: MessageEvent):
            try:
                if isinstance(event, PrivateMessageEvent):
                    message_type = "private"
                elif isinstance(event, GroupMessageEvent):
                    message_type = "group"
                else:
                    return

                user_id = str(getattr(event, "user_id", ""))
                self_id = str(getattr(bot, "self_id", ""))

                # 检查黑名单
                if await self._is_blacklisted(user_id, self_id):
                    self.logger.info(f"用户 {user_id} 在黑名单中，忽略消息")
                    return

                # 抑制重复消息
                raw_plain = event.get_plaintext() if hasattr(event, "get_plaintext") else str(event.get_message())
                if self._should_suppress_message(user_id, raw_plain):
                    self.logger.debug(f"消息被抑制: {user_id}")
                    return

                # 群内优先尝试解析指令；私聊才进行投稿处理
                if isinstance(event, GroupMessageEvent):
                    handled = await self._try_handle_group_command(bot, event)
                    if handled:
                        return
                    # 非指令的群消息不创建投稿
                    return

                # 私聊 -> 进入投稿缓存/建稿流程
                # 在进入建稿流程前，优先解析私聊指令（如：#评论 <投稿ID> <内容>）
                if isinstance(event, PrivateMessageEvent):
                    handled_cmd = await self._try_handle_private_command(user_id, self_id, raw_plain)
                    if handled_cmd:
                        return

                # 提取消息段（用于渲染）
                segments: List[Dict[str, Any]] = []
                try:
                    for seg in event.get_message():
                        try:
                            seg_data = dict(getattr(seg, "data", {}))
                        except Exception:
                            seg_data = {}
                        segments.append({
                            "type": getattr(seg, "type", None),
                            "data": seg_data,
                        })
                except Exception:
                    segments = []

                data: Dict[str, Any] = {
                    "post_type": "message",
                    "message_type": message_type,
                    "user_id": user_id,
                    "self_id": self_id,
                    "message_id": str(getattr(event, "message_id", "")),
                    "raw_message": raw_plain,
                    "message": segments,
                    "time": int(getattr(event, "time", int(time.time()))),
                    "sender": {
                        "nickname": getattr(getattr(event, "sender", None), "nickname", None),
                    },
                }

                await self.process_message(data)
            except Exception as e:
                self.logger.error(f"处理消息事件失败: {e}", exc_info=True)

        req_matcher = on_request(priority=50, block=False)

        @req_matcher.handle()
        async def _(bot: Bot, event: FriendRequestEvent):
            try:
                if not isinstance(event, FriendRequestEvent):
                    return

                user_id = str(getattr(event, "user_id", ""))
                flag = getattr(event, "flag", None)
                comment = getattr(event, "comment", "")
                self_id = str(getattr(bot, "self_id", ""))

                # 去重窗口
                if not self._should_process_friend_request(user_id):
                    self.logger.info(f"忽略重复的好友请求: {user_id}")
                    return

                # 添加抑制项，避免同样文本立即触发投稿
                self._add_suppression(user_id, comment)

                # 自动同意
                if self.config.get("auto_accept_friend", True) and flag:
                    try:
                        await bot.call_api("set_friend_add_request", flag=flag, approve=True)
                        self.logger.info(f"已同意好友请求: {flag}")
                    except Exception as e:
                        self.logger.error(f"同意好友请求失败: {e}")

                if self.friend_request_handler:
                    await self.friend_request_handler(
                        {
                            "post_type": "request",
                            "request_type": "friend",
                            "user_id": user_id,
                            "self_id": self_id,
                            "flag": flag,
                            "comment": comment,
                            "time": int(time.time()),
                        }
                    )
            except Exception as e:
                self.logger.error(f"处理好友请求失败: {e}", exc_info=True)

        # 撤回事件（好友撤回）
        try:
            from nonebot.adapters.onebot.v11 import NoticeEvent
            recall_matcher = nonebot.on_notice(priority=50, block=False)  # type: ignore

            @recall_matcher.handle()  # type: ignore
            async def _(bot: Bot, event: NoticeEvent):
                try:
                    # 只处理好友撤回
                    if getattr(event, "notice_type", None) != "friend_recall":
                        return
                    if not self.enable_recall_delete:
                        return
                    user_id = str(getattr(event, "user_id", ""))
                    self_id = str(getattr(bot, "self_id", ""))
                    message_id = str(getattr(event, "message_id", ""))
                    if not (user_id and self_id and message_id):
                        return
                    ok = await self.remove_cached_message(user_id, self_id, message_id)
                    if ok:
                        self.logger.info(f"已根据撤回事件删除缓存消息: uid={user_id}, sid={self_id}, mid={message_id}")
                except Exception as e:
                    self.logger.error(f"处理撤回事件失败: {e}")
        except Exception:
            pass

    def _should_process_friend_request(self, user_id: str) -> bool:
        now = time.time()
        window = self.config.get("friend_request_window", 300)
        expire = self.friend_request_cache.get(user_id)
        if expire and expire > now:
            return False
        self.friend_request_cache[user_id] = now + window
        return True

    def _add_suppression(self, user_id: str, text: str, duration: int = 120):
        expire_time = time.time() + duration
        norm_text = self._normalize_text(text)
        self.suppression_cache.setdefault(user_id, []).append({"text": norm_text, "expire": expire_time})

    def _should_suppress_message(self, user_id: str, raw_message: str) -> bool:
        rules = self.suppression_cache.get(user_id)
        if not rules:
            return False
        norm_text = self._normalize_text(raw_message)
        now = time.time()
        self.suppression_cache[user_id] = [r for r in rules if r["expire"] > now]
        for rule in self.suppression_cache[user_id]:
            if rule["text"] == norm_text:
                return True
        return False

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        import re
        text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
        return text.lower()

    async def _is_blacklisted(self, user_id: str, receiver_id: str) -> bool:
        db = await get_db()
        async with db.get_session() as session:
            # 解析账号组
            from config import get_settings

            settings = get_settings()
            group_name = None
            for gname, group in settings.account_groups.items():
                if group.main_account.qq_id == receiver_id:
                    group_name = gname
                    break
                for minor in group.minor_accounts:
                    if minor.qq_id == receiver_id:
                        group_name = gname
                        break

            if not group_name:
                return False

            stmt = select(BlackList).where(
                and_(BlackList.user_id == user_id, BlackList.group_name == group_name)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return bool(row and row.is_active())

    async def start(self):
        if self.is_running:
            return
        self.is_running = True

        if not self.app:
            # 容错：若未初始化则初始化
            await self.initialize()

        # 端口与host采用全局 server 配置
        from config import get_settings
        app_settings = get_settings()
        server_host = app_settings.server.host
        server_port = app_settings.server.port

        config = Config(
            app=self.app,  # type: ignore
            host=server_host,
            port=server_port,
            log_level="info" if not self.config.get("debug") else "debug",
        )
        self.server = Server(config)
        asyncio.create_task(self.server.serve())
        self.logger.info(f"QQ NoneBot 接收器已启动: {config.host}:{config.port}")

    async def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        if self.server:
            self.server.should_exit = True
            await asyncio.sleep(1)
        self.logger.info("QQ NoneBot 接收器已停止")

    async def handle_message(self, message: Dict[str, Any]):
        # 由 NoneBot 事件处理直接调用 process_message
        pass

    async def handle_friend_request(self, request: Dict[str, Any]):
        # 由 NoneBot 事件处理直接回调
        pass

    def _get_preferred_bot(self, receiver_id: Optional[str] = None) -> Optional[Bot]:
        try:
            bots = nonebot.get_bots()
            if not bots:
                return None
            # 优先选择与 receiver_id 匹配的 Bot
            if receiver_id:
                for bot in bots.values():
                    if str(getattr(bot, "self_id", "")) == str(receiver_id):
                        return bot
            # 回退到任意可用 Bot
            return next(iter(bots.values()))
        except Exception:
            return None

    async def send_private_message(self, user_id: str, message: str, port: Optional[int] = None) -> bool:  # type: ignore[override]
        try:
            bot = self._get_preferred_bot()
            if not bot:
                self.logger.error("没有可用的 OneBot Bot 实例")
                return False
            try:
                uid = int(user_id)
            except Exception:
                uid = user_id  # 适配少数实现允许字符串
            # 重试发送，缓解偶发超时
            for attempt in range(3):
                try:
                    await bot.call_api("send_private_msg", user_id=uid, message=message)
                    return True
                except Exception as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.8 + attempt * 0.8)
        except Exception as e:
            self.logger.error(f"发送私聊消息失败: {e}")
            return False

    async def send_group_message(self, group_id: str, message: str, port: Optional[int] = None) -> bool:  # type: ignore[override]
        try:
            bot = self._get_preferred_bot()
            if not bot:
                self.logger.error("没有可用的 OneBot Bot 实例")
                return False
            try:
                gid = int(group_id)
            except Exception:
                gid = group_id
            # 重试发送，缓解 Napcat/OneBot 偶发 retcode 1200 超时
            for attempt in range(3):
                try:
                    await bot.call_api("send_group_msg", group_id=gid, message=message)
                    return True
                except Exception as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(1.0 + attempt * 1.0)
        except Exception as e:
            self.logger.error(f"发送群消息失败: {e}")
            return False

    # ===== 指令解析与执行 =====
    async def _try_handle_group_command(self, bot: Bot, event: GroupMessageEvent) -> bool:
        try:
            self_id = str(getattr(bot, "self_id", ""))
            group_id = str(getattr(event, "group_id", ""))

            # 是否 @了本机器人
            if not self._is_at_self(event, self_id):
                return False

            # 取得 @ 后的纯文本
            after_text = event.get_plaintext().strip()

            # 帮助命令：任何成员、任意群均可触发
            if after_text in ("帮助", "help", "指令"):
                await self.send_group_message(group_id, self._build_help_text())
                return True

            # 其余命令：仅管理员/群主允许在管理群执行
            if not self._is_admin_sender(event):
                return False

            group_name = self._resolve_group_name_by_group_id(group_id) or self._resolve_group_name_by_self_id(self_id)
            if not group_name:
                return False

            # 如果是回复消息，尝试从被回复的消息里解析内部编号
            reply_sub_id = await self._try_extract_submission_id_from_reply(bot, event)
            if reply_sub_id is not None and after_text:
                full_text = f"{reply_sub_id} {after_text}"
            else:
                full_text = after_text

            if not full_text:
                return False

            # 判断是审核指令还是全局指令
            tokens = full_text.split()
            if not tokens:
                return False

            # 以数字开头 -> 审核指令
            if tokens[0].isdigit():
                submission_id = int(tokens[0])
                cmd = tokens[1] if len(tokens) > 1 else ""
                extra = " ".join(tokens[2:]) if len(tokens) > 2 else None
                return await self._handle_audit_command(group_id, submission_id, cmd, str(event.user_id), extra)

            # 非数字开头 -> 全局指令
            return await self._handle_global_command(group_id, group_name, full_text)
        except Exception as e:
            self.logger.error(f"解析群指令失败: {e}", exc_info=True)
            return False

    def _is_admin_sender(self, event: GroupMessageEvent) -> bool:
        try:
            role = getattr(getattr(event, "sender", None), "role", None)
            return role in ("admin", "owner")
        except Exception:
            return False

    def _is_at_self(self, event: GroupMessageEvent, self_id: str) -> bool:
        try:
            return event.to_me
        except Exception:
            return False

    async def _try_extract_submission_id_from_reply(self, bot: Bot, event: GroupMessageEvent) -> Optional[int]:
        try:
            reply_id = None
            for seg in event.get_message():
                if seg.type == "reply":
                    rid = seg.data.get("id") or seg.data.get("message_id")
                    if rid is not None:
                        reply_id = int(rid)
                        break
            if reply_id is None:
                return None

            # 获取被回复消息
            try:
                resp = await bot.call_api("get_msg", message_id=reply_id)
                # 解析纯文本
                plain = ""
                try:
                    parts = []
                    for seg in resp.get("message", []):
                        if seg.get("type") == "text":
                            parts.append(seg.get("data", {}).get("text", ""))
                    plain = "".join(parts)
                except Exception:
                    plain = str(resp)
                import re
                m = re.search(r"内部编号(\d+)", plain)
                if m:
                    return int(m.group(1))
            except Exception:
                return None
        except Exception:
            return None
        return None

    def _resolve_group_name_by_group_id(self, group_id: str) -> Optional[str]:
        try:
            from config import get_settings
            settings = get_settings()
            for gname, group in settings.account_groups.items():
                if str(group.manage_group_id) == str(group_id):
                    return gname
        except Exception:
            pass
        return None

    def _resolve_group_name_by_self_id(self, self_id: str) -> Optional[str]:
        try:
            from config import get_settings
            settings = get_settings()
            for gname, group in settings.account_groups.items():
                if str(group.main_account.qq_id) == str(self_id):
                    return gname
                for minor in group.minor_accounts:
                    if str(minor.qq_id) == str(self_id):
                        return gname
        except Exception:
            pass
        return None

    async def _handle_audit_command(self, group_id: str, submission_id: int, cmd: str, operator_id: str, extra: Optional[str]) -> bool:
        try:
            if not self.audit_service:
                await self.send_group_message(group_id, "审核服务未就绪")
                return True

            # 将未知指令作为快捷回复键交给审核服务 quick_reply 兜底
            result = await self.audit_service.handle_command(submission_id, cmd, operator_id, extra)

            # 审核通过：触发发布并通知投稿者（解耦地调用服务层）
            pub_ok = None
            notif_ok = None
            if cmd == "是":
                try:
                    if self.submission_service:
                        pub_ok = await self.submission_service.publish_single_submission(submission_id)
                except Exception as e:
                    self.logger.error(f"审核通过后发布失败: {e}")
                    pub_ok = False
                try:
                    if self.notification_service:
                        notif_ok = await self.notification_service.send_submission_approved(submission_id)
                except Exception as e:
                    self.logger.error(f"审核通过后通知投稿者失败: {e}")
                    notif_ok = False

            # 特殊命令：立即 -> 同步触发发送暂存区并单发当前投稿
            if cmd == "立即":
                try:
                    # 仅单发当前，避免与暂存区重复发送
                    if self.submission_service:
                        await self.submission_service.publish_single_submission(submission_id)
                except Exception as e:
                    self.logger.error(f"立即发送失败: {e}")

            # 结果反馈
            msg = result.get("message") if isinstance(result, dict) else str(result)
            if cmd == "是":
                parts = []
                if pub_ok is not None:
                    parts.append("已发布到QQ空间" if pub_ok else "发布到QQ空间失败")
                if notif_ok is not None:
                    parts.append("已私聊通知投稿者" if notif_ok else "通知投稿者失败")
                if parts:
                    extra_line = "；".join(parts)
                    msg = (msg or "") + ("\n" + extra_line if extra_line else "")
            if result.get("need_reaudit"):
                msg = (msg or "") + "\n请继续发送审核指令"
            await self.send_group_message(group_id, msg or "已处理")
            return True
        except Exception as e:
            self.logger.error(f"执行审核指令异常: {e}", exc_info=True)
            await self.send_group_message(group_id, f"指令执行失败: {e}")
            return True

    async def _handle_global_command(self, group_id: str, group_name: str, text: str) -> bool:
        try:
            # 规范化：按空白切分
            parts = text.split()
            if not parts:
                return False
            cmd = parts[0]
            arg1 = parts[1] if len(parts) > 1 else None
            arg_rest = " ".join(parts[1:]) if len(parts) > 1 else None

            # 帮助
            if cmd in ("帮助", "help", "指令"):
                await self.send_group_message(group_id, self._build_help_text())
                return True

            # 设定编号 N
            if cmd == "设定编号" and arg1 and arg1.isdigit():
                try:
                    from pathlib import Path
                    num_dir = Path("data/cache/numb")
                    num_dir.mkdir(parents=True, exist_ok=True)
                    with open(num_dir / f"{group_name}_numfinal.txt", "w", encoding="utf-8") as f:
                        f.write(str(int(arg1)))
                    await self.send_group_message(group_id, f"外部编号已设定为{arg1}")
                except Exception as e:
                    await self.send_group_message(group_id, f"设定编号失败: {e}")
                return True

            # 自动重新登录 / 手动重新登录（统一按刷新登录处理）
            if cmd in ("自动重新登录", "手动重新登录"):
                try:
                    from core.plugin import plugin_manager
                    publisher = plugin_manager.get_publisher("qzone_publisher")
                    if not publisher:
                        await self.send_group_message(group_id, "QQ空间发送器未就绪")
                        return True
                    # 找到本组的所有账号
                    accounts = [
                        acc_id for acc_id, info in getattr(publisher, "accounts", {}).items()
                        if info.get("group_name") == group_name
                    ]
                    if not accounts:
                        await self.send_group_message(group_id, "未找到本组账号")
                        return True
                    ok_list = []
                    fail_list = []
                    for acc in accounts:
                        try:
                            ok = await publisher.refresh_login(acc)
                            (ok_list if ok else fail_list).append(acc)
                        except Exception:
                            fail_list.append(acc)
                    msg = "自动登录QQ空间尝试完毕\n" if cmd == "自动重新登录" else "手动登录刷新尝试完毕\n"
                    if ok_list:
                        msg += f"成功: {', '.join(ok_list)}\n"
                    if fail_list:
                        msg += f"失败: {', '.join(fail_list)}"
                    await self.send_group_message(group_id, msg.strip())
                except Exception as e:
                    await self.send_group_message(group_id, f"刷新登录失败: {e}")
                return True

            # 重渲染 <id> -> 仅重渲染
            if cmd == "重渲染" and arg1 and arg1.isdigit():
                if not self.audit_service:
                    await self.send_group_message(group_id, "审核服务未就绪")
                    return True
                res = await self.audit_service.rerender(int(arg1), operator_id=group_id)
                await self.send_group_message(group_id, res.get("message", "已处理"))
                return True

            # 调出 <id> -> 仅重渲染（等价命令）
            if cmd == "调出" and arg1 and arg1.isdigit():
                if not self.audit_service:
                    await self.send_group_message(group_id, "审核服务未就绪")
                    return True
                res = await self.audit_service.rerender(int(arg1), operator_id=group_id)
                await self.send_group_message(group_id, res.get("message", "已处理"))
                return True

            # 信息 <id>
            if cmd == "信息" and arg1 and arg1.isdigit():
                from core.database import get_db
                from sqlalchemy import select
                from core.models import Submission
                db = await get_db()
                async with db.get_session() as session:
                    r = await session.execute(select(Submission).where(Submission.id == int(arg1)))
                    sub = r.scalar_one_or_none()
                    if not sub:
                        await self.send_group_message(group_id, "投稿不存在")
                        return True
                    llm = sub.llm_result or {}
                    msg = (
                        f"接收者：{sub.receiver_id}\n"
                        f"发送者：{sub.sender_id}\n"
                        f"所属组：{sub.group_name}\n"
                        f"处理后json：{llm if llm else '无'}\n"
                        f"状态：{sub.status} 匿名：{ '是' if sub.is_anonymous else '否'}"
                    )
                    await self.send_group_message(group_id, msg)
                return True

            # 待处理
            if cmd == "待处理":
                if not self.submission_service:
                    await self.send_group_message(group_id, "投稿服务未就绪")
                    return True
                pendings = await self.submission_service.get_pending_submissions(group_name)
                if not pendings:
                    await self.send_group_message(group_id, "本组没有待处理项目")
                else:
                    ids = "\n".join(str(s.id) for s in pendings)
                    await self.send_group_message(group_id, f"本组待处理项目:\n{ids}")
                return True

            # 删除待处理 -> 全部标为已删除
            if cmd == "删除待处理":
                try:
                    from core.database import get_db
                    from sqlalchemy import select, update
                    from core.models import Submission
                    from core.enums import SubmissionStatus
                    db = await get_db()
                    async with db.get_session() as session:
                        r = await session.execute(select(Submission).where(
                            (Submission.group_name == group_name) & (Submission.status.in_([
                                SubmissionStatus.PENDING.value,
                                SubmissionStatus.PROCESSING.value,
                                SubmissionStatus.WAITING.value
                            ]))
                        ))
                        subs = r.scalars().all()
                        if subs:
                            await session.execute(update(Submission).where(Submission.id.in_([s.id for s in subs])).values(status=SubmissionStatus.DELETED.value))
                            await session.commit()
                    await self.send_group_message(group_id, "已清空待处理列表")
                except Exception as e:
                    await self.send_group_message(group_id, f"清空失败: {e}")
                return True

            # 删除暂存区
            if cmd == "删除暂存区":
                if not self.submission_service:
                    await self.send_group_message(group_id, "投稿服务未就绪")
                    return True
                ok = await self.submission_service.clear_stored_posts(group_name)
                await self.send_group_message(group_id, "已清空暂存区" if ok else "清空暂存区失败")
                return True

            # 发送暂存区
            if cmd == "发送暂存区":
                if not self.submission_service:
                    await self.send_group_message(group_id, "投稿服务未就绪")
                    return True
                ok = await self.submission_service.publish_stored_posts(group_name)
                await self.send_group_message(group_id, "投稿已发送" if ok else "发送失败")
                return True

            # 自检
            if cmd == "自检":
                try:
                    from core.database import get_db
                    db = await get_db()
                    db_ok = await db.health_check()
                except Exception:
                    db_ok = False
                # 登录状态
                login_ok = False
                try:
                    from core.plugin import plugin_manager
                    publisher = plugin_manager.get_publisher("qzone_publisher")
                    if publisher:
                        login_ok = await publisher.check_login_status()
                except Exception:
                    login_ok = False
                msg = (
                    "== 系统自检报告 ==\n"
                    f"数据库: {'正常' if db_ok else '异常'}\n"
                    f"QQ空间登录: {'正常' if login_ok else '异常'}\n"
                    "==== 自检完成 ===="
                )
                await self.send_group_message(group_id, msg)
                return True

            # 取消拉黑 <qq>
            if cmd == "取消拉黑" and arg1:
                try:
                    from core.database import get_db
                    from sqlalchemy import delete
                    from core.models import BlackList
                    db = await get_db()
                    async with db.get_session() as session:
                        await session.execute(delete(BlackList).where((BlackList.user_id == str(arg1)) & (BlackList.group_name == group_name)))
                        await session.commit()
                    await self.send_group_message(group_id, f"已取消拉黑 senderid: {arg1}")
                except Exception as e:
                    await self.send_group_message(group_id, f"取消拉黑失败: {e}")
                return True

            # 列出拉黑
            if cmd == "列出拉黑":
                try:
                    from core.database import get_db
                    from sqlalchemy import select
                    from core.models import BlackList
                    db = await get_db()
                    async with db.get_session() as session:
                        r = await session.execute(select(BlackList).where(BlackList.group_name == group_name))
                        rows = r.scalars().all()
                    if not rows:
                        await self.send_group_message(group_id, "当前账户组没有被拉黑的账号")
                    else:
                        lines = ["被拉黑账号列表："]
                        for row in rows:
                            lines.append(f"账号: {row.user_id}，理由: {row.reason or '无'}")
                        await self.send_group_message(group_id, "\n".join(lines))
                except Exception as e:
                    await self.send_group_message(group_id, f"查询失败: {e}")
                return True

            # 快捷回复 管理
            if cmd == "快捷回复":
                subcmd = parts[1] if len(parts) > 1 else None
                if subcmd == "添加" and len(parts) >= 3:
                    kv = " ".join(parts[2:])
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        ok, msg = self._quick_reply_update(group_name, k.strip(), v.strip(), op="add")
                        await self.send_group_message(group_id, msg)
                        return True
                    await self.send_group_message(group_id, "错误：格式不正确，请使用 '指令名=内容'")
                    return True
                if subcmd == "删除" and len(parts) >= 3:
                    k = " ".join(parts[2:]).strip()
                    ok, msg = self._quick_reply_update(group_name, k, None, op="del")
                    await self.send_group_message(group_id, msg)
                    return True
                # 查看列表
                ok, msg = self._quick_reply_list(group_name)
                await self.send_group_message(group_id, msg)
                return True

            # 未识别
            return False
        except Exception as e:
            self.logger.error(f"处理全局指令失败: {e}", exc_info=True)
            return False

    async def _try_handle_private_command(self, user_id: str, self_id: str, raw_text: str) -> bool:
        """解析并处理私聊指令。目前支持：
        - #评论 <投稿ID> <内容>  -> 投稿者本人为其投稿追加匿名评论
        识别到并处理返回 True；未识别返回 False。
        """
        try:
            text = (raw_text or "").strip()
            # 反馈指令：#反馈 <内容>
            m_fb = re.match(r"^#?\s*反馈\s+(.+)$", text)
            if m_fb:
                feedback_text = m_fb.group(1).strip()
                if not feedback_text:
                    await self.send_private_message(user_id, "错误：反馈内容不能为空")
                    return True
                try:
                    from pathlib import Path
                    from config import get_settings
                    settings = get_settings()
                    base_dir = Path(settings.system.data_dir or "./data")
                    fb_dir = base_dir / "feedback"
                    fb_dir.mkdir(parents=True, exist_ok=True)
                    # 按日期分别记录
                    day_str = time.strftime("%Y-%m-%d", time.localtime())
                    ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    group_name = self._resolve_group_name_by_self_id(self_id) or "unknown"
                    line = f"[{ts_str}] uid={user_id} sid={self_id} group={group_name} feedback={feedback_text}\n"
                    with open(fb_dir / f"{day_str}.log", "a", encoding="utf-8") as f:
                        f.write(line)
                    self.logger.info(f"已记录用户反馈: uid={user_id}, group={group_name}")
                    await self.send_private_message(user_id, "感谢反馈，我们已记录")
                except Exception as e:
                    self.logger.error(f"保存反馈失败: {e}", exc_info=True)
                    await self.send_private_message(user_id, "反馈保存失败，请稍后重试")
                return True
            # 允许前缀可选的 #
            m = re.match(r"^#?评论\s+(\d+)\s+(.+)$", text)
            if not m:
                return False

            submission_id = int(m.group(1))
            comment_text = m.group(2).strip()
            if not comment_text:
                await self.send_private_message(user_id, "错误：评论内容不能为空")
                return True

            # 查询投稿并进行状态校验
            from core.database import get_db
            from sqlalchemy import select
            from core.models import Submission
            from core.enums import SubmissionStatus

            db = await get_db()
            async with db.get_session() as session:
                r = await session.execute(select(Submission).where(Submission.id == submission_id))
                submission = r.scalar_one_or_none()

                if not submission:
                    await self.send_private_message(user_id, "错误：投稿不存在")
                    return True

                # 仅允许对已发布的投稿同步评论
                if submission.status != SubmissionStatus.PUBLISHED.value:
                    await self.send_private_message(user_id, "当前投稿尚未发布，无法同步评论到QQ空间")
                    return True

            # 记录审核日志（若可用），根据配置决定是否匿名记录操作者
            try:
                if self.audit_service:
                    try:
                        from config import get_settings
                        settings = get_settings()
                        # 需要 submission 的组名以判断配置
                        group_name = None
                        try:
                            # 重新读取一次提交记录获取组名（上面查询的 submission 已存在于局部作用域，但作用域外不可用）
                            db2 = await get_db()
                            async with db2.get_session() as s2:
                                from sqlalchemy import select as _select
                                from core.models import Submission as _Submission
                                rr = await s2.execute(_select(_Submission).where(_Submission.id == submission_id))
                                sub_row = rr.scalar_one_or_none()
                                if sub_row:
                                    group_name = sub_row.group_name
                        except Exception:
                            group_name = None
                        allow_anon = True
                        if group_name and group_name in settings.account_groups:
                            grp = settings.account_groups.get(group_name)
                            allow_anon = bool(getattr(grp, 'allow_anonymous_comment', True))
                        operator_for_log = "anonymous" if allow_anon else user_id
                    except Exception:
                        operator_for_log = user_id
                    await self.audit_service.log_audit(submission_id, operator_for_log, "评论", comment_text)
            except Exception:
                pass

            # 同步到QQ空间：使用对应发布账号调用API
            try:
                from core.plugin import plugin_manager
                publisher = plugin_manager.get_publisher("qzone_publisher")
                if not publisher:
                    await self.send_private_message(user_id, "发送器未就绪，稍后再试")
                    return True
                result = await publisher.add_comment_for_submission(submission_id, comment_text)
                if result.get("success"):
                    await self.send_private_message(user_id, f"评论成功：已同步到QQ空间（投稿 {submission_id}）")
                else:
                    await self.send_private_message(user_id, f"评论失败：{result.get('message','未知错误')}")
                return True
            except Exception as e:
                self.logger.error(f"QQ空间评论同步失败: {e}")
                await self.send_private_message(user_id, "评论失败：系统异常")
                return True

            # ===== 私聊反馈指令 =====
            # 语法: #反馈 <内容>
            fm = re.match(r"^#?反馈\s+(.+)$", text, re.S)
            if fm:
                feedback_text = fm.group(1).strip()
                if not feedback_text:
                    await self.send_private_message(user_id, "错误：反馈内容不能为空")
                    return True
                try:
                    from pathlib import Path
                    from datetime import datetime
                    # 保存到 data/feedback 目录下，按时间和用户ID区分文件
                    fb_dir = Path("data/feedback")
                    fb_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    fb_file = fb_dir / f"{ts}_{user_id}.txt"
                    with open(fb_file, "w", encoding="utf-8") as f:
                        f.write(feedback_text)
                    await self.send_private_message(user_id, "反馈已收到，感谢您的意见！")
                except Exception as e:
                    self.logger.error(f"保存反馈失败: {e}", exc_info=True)
                    await self.send_private_message(user_id, f"反馈保存失败: {e}")
                return True

            # 不应到达此处
            return False
        except Exception as e:
            self.logger.error(f"处理私聊评论指令失败: {e}", exc_info=True)
            try:
                await self.send_private_message(user_id, f"处理失败：{e}")
            except Exception:
                pass
            return True

    def _quick_reply_update(self, group_name: str, key: str, value: Optional[str], op: str) -> Tuple[bool, str]:
        try:
            from config import get_settings
            settings = get_settings()
            group = settings.account_groups.get(group_name)
            if not group:
                return False, "找不到账号组配置"
            # 冲突检查
            if op == "add":
                audit_cmds = {"是","否","匿","等","删","拒","立即","刷新","重渲染","扩列审查","评论","回复","展示","拉黑"}
                if key in audit_cmds:
                    return False, f"错误：快捷回复指令 '{key}' 与审核指令冲突"
                group.quick_replies[key] = value or ""
            elif op == "del":
                if key not in group.quick_replies:
                    return False, f"错误：快捷回复指令 '{key}' 不存在"
                del group.quick_replies[key]
            else:
                return False, "无效操作"
            # 持久化
            settings.save_yaml()
            return True, (f"已添加快捷回复指令：{key}" if op == "add" else f"已删除快捷回复指令：{key}")
        except Exception as e:
            return False, f"快捷回复更新失败: {e}"

    def _quick_reply_list(self, group_name: str) -> Tuple[bool, str]:
        try:
            from config import get_settings
            settings = get_settings()
            group = settings.account_groups.get(group_name)
            qrs = (group.quick_replies if group else {}) or {}
            if not qrs:
                return True, "当前账户组未配置快捷回复"
            lines = ["当前账户组快捷回复列表："]
            for k, v in qrs.items():
                lines.append(f"指令: {k}\n内容: {v}")
            return True, "\n".join(lines)
        except Exception as e:
            return False, f"获取快捷回复失败: {e}"

    def _build_help_text(self) -> str:
        return (
            "全局指令:\n"
            "语法: @本账号 指令\n\n"
            "调出 <编号>\n信息 <编号>\n待处理\n删除待处理\n删除暂存区\n发送暂存区\n"
            "取消拉黑 <QQ>\n列出拉黑\n设定编号 <数字>\n快捷回复 [添加 指令=内容|删除 指令]\n自检\n\n"
            "审核指令:\n语法: @本账号 <内部编号> 指令 或 回复审核消息 指令\n"
            "是/否/匿/等/删/拒/立即/刷新/重渲染/扩列审查/评论 <内容>/回复 <内容>/展示/拉黑 [理由]\n"
            "也可使用已配置的快捷回复键"
        )


