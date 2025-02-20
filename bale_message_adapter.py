import sys
import uuid
import asyncio

from astrbot.api.platform import Platform, AstrBotMessage, MessageMember, PlatformMetadata, MessageType
from astrbot.api.event import MessageChain
from astrbot.api.message_components import Plain, Image, Record
from astrbot.core.platform.astr_message_event import MessageSesion
from astrbot.api.platform import register_platform_adapter

from telegram import Update, File
from telegram.ext import ApplicationBuilder, ContextTypes, filters
from telegram.constants import ChatType
from telegram.ext import MessageHandler as TelegramMessageHandler
from .bale_message_event import BalePlatformEvent

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

@register_platform_adapter("bale", "bale 适配器", default_config_tmpl={
    "bale_token": "your_token",
    "start_message": "Hello, I'm AstrBot!",
    "提示": "由于 Bale 无法在中国大陆访问，如果你的网络环境为中国大陆，记得在 `其他配置` 处设置代理！"
})
class BalePlatformAdapter(Platform):

    def __init__(self, platform_config: dict, platform_settings: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(event_queue)
        self.config = platform_config
        self.settingss = platform_settings
        self.client_self_id = uuid.uuid4().hex[:8]
    
    @override
    async def send_by_session(self, session: MessageSesion, message_chain: MessageChain):
        from_username = session.session_id
        await BalePlatformEvent.send_with_client(self.client, message_chain, from_username)
        await super().send_by_session(session, message_chain)
    
    @override
    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            "bale",
            "bale 适配器",
        )

    @override
    async def run(self):
        self.application = ApplicationBuilder().token(self.config['bale_token']).base_url('https://tapi.bale.ai/bot').build()
        message_handler = TelegramMessageHandler(
            filters=None,
            callback=self.convert_message
        )
        self.application.add_handler(message_handler)
        await self.application.initialize()
        await self.application.start()
        queue = self.application.updater.start_polling()
        self.client = self.application.bot
        print("Bale Platform Adapter is running.")
        await queue

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self.config["start_message"])

    async def convert_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> AstrBotMessage:
        message = AstrBotMessage()
        # 获得是群聊还是私聊
        if update.effective_chat.type == ChatType.PRIVATE:
            message.type = MessageType.FRIEND_MESSAGE
        else:
            message.type = MessageType.GROUP_MESSAGE
            message.group_id = update.effective_chat.id
        message.message_id = str(update.message.message_id)
        message.session_id = str(update.effective_chat.id)
        message.sender = MessageMember(str(update.effective_user.id), update.effective_user.username)
        message.self_id = str(context.bot.id)
        message.raw_message = update
        message.message_str = ""
        
        if update.message.text:
            plain_text = update.message.text
            message.message = [Plain(plain_text),]
            message.message_str = plain_text
            
        elif update.message.voice:
            file = await update.message.voice.get_file()
            message.message = [Record(file=file.file_path, url=file.file_path),]
            
        
        await self.handle_msg(message)
    
    async def handle_msg(self, message: AstrBotMessage):
        message_event = BalePlatformEvent(
            message_str=message.message_str,
            message_obj=message,
            platform_meta=self.meta(),
            session_id=message.session_id,
            client=self.client
        )
        self.commit_event(message_event)