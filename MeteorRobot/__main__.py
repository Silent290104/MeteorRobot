import html
import os
import json
import importlib
import time
import re
import sys
import traceback
import MeteorRobot.modules.sql.users_sql as sql
from sys import argv
from typing import Optional
from telegram import __version__ as peler
from platform import python_version as memek
from MeteorRobot import (
    ALLOW_EXCL,
    CERT_PATH,
    DONATION_LINK,
    BOT_USERNAME as bu,
    LOGGER,
    OWNER_ID,
    PORT,
    SUPPORT_CHAT,
    TOKEN,
    URL,
    WEBHOOK,
    SUPPORT_CHAT,
    dispatcher,
    StartTime,
    telethn,
    pbot,
    updater,
)

# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from MeteorRobot.modules import ALL_MODULES
from MeteorRobot.modules.helper_funcs.chat_status import is_user_admin
from MeteorRobot.modules.helper_funcs.misc import paginate_modules
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import (
    BadRequest,
    ChatMigrated,
    NetworkError,
    TelegramError,
    TimedOut,
    Unauthorized,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.ext.dispatcher import DispatcherHandlerStop, run_async
from telegram.utils.helpers import escape_markdown


def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time


PM_START_TEXT = """
*Hello {} !*
✪ I'm an anime-theme management bot ᴡɪᴛʜ ꜱᴏᴍᴇ ꜰᴜɴ ᴇxᴛʀᴀꜱ ;)[✨](https://te.legra.ph/file/653cc589cef8ce310a9f2.jpg)
────────────────────────
ᴀ ᴘᴏᴡᴇʀꜰᴜʟ ɢʀᴏᴜᴘ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ʙᴏᴛ ʙᴜɪʟᴛ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴇᴀꜱɪʟʏ ᴀɴᴅ ᴛᴏ ᴘʀᴏᴛᴇᴄᴛ ʏᴏᴜʀ ɢʀᴏᴜᴘ ꜰʀᴏᴍ ꜱᴄᴀᴍᴍᴇʀꜱ ᴀɴᴅ ꜱᴘᴀᴍᴍᴇʀꜱ.
ᴡʀɪᴛᴛᴇɴ ɪɴ ᴩʏᴛʜᴏɴ ᴡɪᴛʜ sǫʟᴀʟᴄʜᴇᴍʏ ᴀɴᴅ ᴍᴏɴɢᴏᴅʙ ᴀs ᴅᴀᴛᴀʙᴀsᴇ.
────────────────────────
× *Uptime:* `{}`
× `{}` *users, across* `{}` *chats.*
────────────────────────
✪ ᴄʟɪᴄᴋ ᴏɴ ʜᴇʟᴘ ᴛᴏ ʟᴇᴀʀɴ ᴍᴏʀᴇ!
"""

buttons = [
    [
        InlineKeyboardButton(
            text="Aᴅᴅ ᴍᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ Bᴀʙʏ", url=f"t.me/{bu}?startgroup=new"),
    ],
    [
        InlineKeyboardButton(text="Hᴇʟᴘ & Cᴏᴍᴍᴀɴᴅs", callback_data="help_back"),
    ],
    [
        InlineKeyboardButton(text=f"❄️ᴀʙᴏᴜᴛ❄️", callback_data="meteor_"),
        InlineKeyboardButton(
            text="Dᴇᴠᴇʟᴏᴘᴇʀ", url="https://github.com/Revenger2901""
        ),    
    ],
    [
        InlineKeyboardButton(text=f"🎵Mᴜsɪᴄ🎵", callback_data="source_"),
        InlineKeyboardButton(
            text="ᴏᴡɴᴇʀ", url="https://t.me/Wolf_2904"
        ),
    ],
]


HELP_STRINGS = """
Click on the button bellow to get description about specifics command."""


DONATE_STRING = """Heya, glad to hear you want to donate!
 You can support the project by contacting @Silent_Smile_04 \
 Supporting isnt always financial! \
 Those who cannot provide monetary support are welcome to help us develop the bot at ."""

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []
CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("MeteorRobot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )


def test(update: Update, context: CallbackContext):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("This person edited a message")
    print(update.effective_message)


def start(update: Update, context: CallbackContext):
    args = context.args
    uptime = get_readable_time((time.time() - StartTime))
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower().startswith("ghelp_"):
                mod = args[0].lower().split("_", 1)[1]
                if not HELPABLE.get(mod, False):
                    return
                send_help(
                    update.effective_chat.id,
                    HELPABLE[mod].__help__,
                    InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="◁", callback_data="help_back")]]
                    ),
                )

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            uptime = get_readable_time((time.time() - StartTime))
            update.effective_message.reply_text(
                PM_START_TEXT.format(
                    escape_markdown(first_name),
                    escape_markdown(uptime),
                    sql.num_users(),
                    sql.num_chats()),                        
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
            )
    else:
        update.effective_message.reply_text(
            f"👋 Hi, I'm {dispatcher.bot.first_name}. Nice to meet You.",
            parse_mode=ParseMode.HTML
       )


def error_handler(update, context):
    """𝑳𝒐𝒈 𝒕𝒉𝒆 𝒆𝒓𝒓𝒐𝒓 𝒂𝒏𝒅 𝒔𝒆𝒏𝒅 𝒂 𝒕𝒆𝒍𝒆𝒈𝒓𝒂𝒎 𝒎𝒆𝒔𝒔𝒂𝒈𝒆 𝒕𝒐 𝒏𝒐𝒕𝒊𝒇𝒚 𝒕𝒉𝒆 𝒅𝒆𝒗𝒆𝒍𝒐𝒑𝒆𝒓."""
    # 𝑳𝒐𝒈 𝒕𝒉𝒆 𝒆𝒓𝒓𝒐𝒓 𝒃𝒆𝒇𝒐𝒓𝒆 𝒘𝒆 𝒅𝒐 𝒂𝒏𝒚𝒕𝒉𝒊𝒏𝒈 𝒆𝒍𝒔𝒆, 𝒔𝒐 𝒘𝒆 𝒄𝒂𝒏 𝒔𝒆𝒆 𝒊𝒕 𝒆𝒗𝒆𝒏 𝒊𝒇 𝒔𝒐𝒎𝒆𝒕𝒉𝒊𝒏𝒈 𝒃𝒓𝒆𝒂𝒌𝒔.
    LOGGER.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    message = (
        "𝑨𝒏 𝒆𝒙𝒄𝒆𝒑𝒕𝒊𝒐𝒏 𝒘𝒂𝒔 𝒓𝒂𝒊𝒔𝒆𝒅 𝒘𝒉𝒊𝒍𝒆 𝒉𝒂𝒏𝒅𝒍𝒊𝒏𝒈 𝒂𝒏 𝒖𝒑𝒅𝒂𝒕𝒆\n"
        "<pre>update = {}</pre>\n\n"
        "<pre>{}</pre>"
    ).format(
        html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False)),
        html.escape(tb),
    )

    if len(message) >= 4096:
        message = message[:4096]
    # Finally, send the message
    context.bot.send_message(chat_id=OWNER_ID, text=message, parse_mode=ParseMode.HTML)


# for test purposes
def error_callback(update: Update, context: CallbackContext):
    error = context.error
    try:
        raise error
    except Unauthorized:
        print("no nono1")
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print("no nono2")
        print("BadRequest caught")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("no nono3")
        # handle slow connection problems
    except NetworkError:
        print("no nono4")
        # handle other connection problems
    except ChatMigrated as err:
        print("no nono5")
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


def help_button(update, context):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    print(query.message.chat.id)

    try:
        if mod_match:
            module = mod_match.group(1)
            text = (
                "Here is the help for the *{}* module:\n".format(
                    HELPABLE[module].__mod_name__
                )
                + HELPABLE[module].__help__
            )
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="◁", callback_data="help_back")]]
                ),
            )

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                ),
            )

        elif back_match:
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, HELPABLE, "help")
                ),
            )

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)
        # query.message.delete()

    except BadRequest:
        pass


def meteor_about_callback(update, context):
    query = update.callback_query
    if query.data == "meteor_":
        query.message.edit_text(
            text=f"๏ 𝑰'𝒎 *{dispatcher.bot.first_name}*, 𝒂 𝒑𝒐𝒘𝒆𝒓𝒇𝒖𝒍 𝒈𝒓𝒐𝒖𝒑 𝒎𝒂𝒏𝒂𝒈𝒆𝒎𝒆𝒏𝒕 𝒃𝒐𝒕 𝒃𝒖𝒊𝒍𝒕 𝒕𝒐 𝒉𝒆𝒍𝒑 𝒚𝒐𝒖 𝒎𝒂𝒏𝒂𝒈𝒆 𝒚𝒐𝒖𝒓 𝒈𝒓𝒐𝒖𝒑 𝒆𝒂𝒔𝒊𝒍𝒚."
            "\n• 𝑰 𝒄𝒂𝒏 𝒓𝒆𝒔𝒕𝒓𝒊𝒄𝒕 𝒖𝒔𝒆𝒓𝒔."
            "\n• 𝑰 𝒄𝒂𝒏 𝒈𝒓𝒆𝒆𝒕 𝒖𝒔𝒆𝒓𝒔 𝒘𝒊𝒕𝒉 𝒄𝒖𝒔𝒕𝒐𝒎𝒊𝒛𝒂𝒃𝒍𝒆 𝒘𝒆𝒍𝒄𝒐𝒎𝒆 𝒎𝒆𝒔𝒔𝒂𝒈𝒆𝒔 𝒂𝒏𝒅 𝒆𝒗𝒆𝒏 𝒔𝒆𝒕 𝒂 𝒈𝒓𝒐𝒖𝒑'𝒔 𝒓𝒖𝒍𝒆𝒔."
            "\n• 𝑰 𝒉𝒂𝒗𝒆 𝒂𝒏 𝒂𝒅𝒗𝒂𝒏𝒄𝒆𝒅 𝒂𝒏𝒕𝒊-𝒇𝒍𝒐𝒐𝒅 𝒔𝒚𝒔𝒕𝒆𝒎."
            "\n• 𝑰 𝒄𝒂𝒏 𝒘𝒂𝒓𝒏 𝒖𝒔𝒆𝒓𝒔 𝒖𝒏𝒕𝒊𝒍 𝒕𝒉𝒆𝒚 𝒓𝒆𝒂𝒄𝒉 𝒎𝒂𝒙 𝒘𝒂𝒓𝒏𝒔, 𝒘𝒊𝒕𝒉 𝒆𝒂𝒄𝒉 𝒑𝒓𝒆𝒅𝒆𝒇𝒊𝒏𝒆𝒅 𝒂𝒄𝒕𝒊𝒐𝒏𝒔 𝒔𝒖𝒄𝒉 𝒂𝒔 𝒃𝒂𝒏, 𝒎𝒖𝒕𝒆, 𝒌𝒊𝒄𝒌, 𝒆𝒕𝒄."
            "\n• 𝑰 𝒉𝒂𝒗𝒆 𝒂 𝒏𝒐𝒕𝒆 𝒌𝒆𝒆𝒑𝒊𝒏𝒈 𝒔𝒚𝒔𝒕𝒆𝒎, 𝒃𝒍𝒂𝒄𝒌𝒍𝒊𝒔𝒕𝒔, 𝒂𝒏𝒅 𝒆𝒗𝒆𝒏 𝒑𝒓𝒆𝒅𝒆𝒕𝒆𝒓𝒎𝒊𝒏𝒆𝒅 𝒓𝒆𝒑𝒍𝒊𝒆𝒔 𝒐𝒏 𝒄𝒆𝒓𝒕𝒂𝒊𝒏 𝒌𝒆𝒚𝒘𝒐𝒓𝒅𝒔."
            "\n• 𝑰 𝒄𝒉𝒆𝒄𝒌 𝒇𝒐𝒓 𝒂𝒅𝒎𝒊𝒏𝒔' 𝒑𝒆𝒓𝒎𝒊𝒔𝒔𝒊𝒐𝒏𝒔 𝒃𝒆𝒇𝒐𝒓𝒆 𝒆𝒙𝒆𝒄𝒖𝒕𝒊𝒏𝒈 𝒂𝒏𝒚 𝒄𝒐𝒎𝒎𝒂𝒏𝒅 𝒂𝒏𝒅 𝒎𝒐𝒓𝒆 𝒔𝒕𝒖𝒇𝒇𝒔"
            f"\n\n_{dispatcher.bot.first_name}'𝒔 𝒍𝒊𝒄𝒆𝒏𝒔𝒆𝒅 𝒖𝒏𝒅𝒆𝒓 𝒕𝒉𝒆 𝑮𝑵𝑼 𝑮𝒆𝒏𝒆𝒓𝒂𝒍 𝑷𝒖𝒃𝒍𝒊𝒄 𝑳𝒊𝒄𝒆𝒏𝒔𝒆 𝒗3.0_"
            f"\n\n 𝑪𝒍𝒊𝒄𝒌 𝒐𝒏 𝒃𝒖𝒕𝒕𝒐𝒏 𝒃𝒆𝒍𝒍𝒐𝒘 𝒕𝒐 𝒈𝒆𝒕 𝒃𝒂𝒔𝒊𝒄 𝒉𝒆𝒍𝒑 𝒇𝒐𝒓 {dispatcher.bot.first_name}.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="ᴀᴅᴍɪɴs", callback_data="meteor_admin"),
                    InlineKeyboardButton(text="ɴᴏᴛᴇs", callback_data="meteor_notes"),
                 ],
                 [
                    InlineKeyboardButton(text="Mᴇᴛᴇᴏʀ sᴜᴘᴘᴏʀᴛ", callback_data="meteor_support"),
                    InlineKeyboardButton(text="ᴏᴡɴᴇʀ", callback_data="meteor_credit"),
                 ],
                 [
                    InlineKeyboardButton(text="sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ", url="https://github.com/Revenger2901/MeteorRobot"),
                 ],
                 [
                    InlineKeyboardButton(text="◁", callback_data="meteor_back"),
                 ]
                ]
            ),
        )

    elif query.data == "meteor_admin":
        query.message.edit_text(
            text=f"*๏ 𝑳𝒆𝒕'𝒔 𝒎𝒂𝒌𝒆 𝒚𝒐𝒖𝒓 𝒈𝒓𝒐𝒖𝒑 𝒃𝒊𝒕 𝒆𝒇𝒇𝒆𝒄𝒕𝒊𝒗𝒆 𝒏𝒐𝒘*"
            f"\n𝑪𝒐𝒏𝒈𝒓𝒂𝒈𝒖𝒍𝒂𝒕𝒊𝒐𝒏𝒔, {dispatcher.bot.first_name} 𝒏𝒐𝒘 𝒓𝒆𝒂𝒅𝒚 𝒕𝒐 𝒎𝒂𝒏𝒂𝒈𝒆 𝒚𝒐𝒖𝒓 𝒈𝒓𝒐𝒖𝒑."
            "\n\n*𝑨𝒅𝒎𝒊𝒏 𝑻𝒐𝒐𝒍𝒔*"
            "\n𝑩𝒂𝒔𝒊𝒄 𝑨𝒅𝒎𝒊𝒏 𝒕𝒐𝒐𝒍𝒔 𝒉𝒆𝒍𝒑 𝒚𝒐𝒖 𝒕𝒐 𝒑𝒓𝒐𝒕𝒆𝒄𝒕 𝒂𝒏𝒅 𝒑𝒐𝒘𝒆𝒓𝒖𝒑 𝒚𝒐𝒖𝒓 𝒈𝒓𝒐𝒖𝒑."
            "\n𝒀𝒐𝒖 𝒄𝒂𝒏 𝒃𝒂𝒏 𝒎𝒆𝒎𝒃𝒆𝒓𝒔, 𝑲𝒊𝒄𝒌 𝒎𝒆𝒎𝒃𝒆𝒓𝒔, 𝑷𝒓𝒐𝒎𝒐𝒕𝒆 𝒔𝒐𝒎𝒆𝒐𝒏𝒆 𝒂𝒔 𝒂𝒅𝒎𝒊𝒏 𝒕𝒉𝒓𝒐𝒖𝒈𝒉 𝒄𝒐𝒎𝒎𝒂𝒏𝒅𝒔 𝒐𝒇 𝒃𝒐𝒕."
            "\n\n*𝑮𝒓𝒆𝒆𝒕𝒊𝒏𝒈𝒔*"
            "\n𝑳𝒆𝒕𝒔 𝒔𝒆𝒕 𝒂 𝒘𝒆𝒍𝒄𝒐𝒎𝒆 𝒎𝒆𝒔𝒔𝒂𝒈𝒆 𝒕𝒐 𝒘𝒆𝒍𝒄𝒐𝒎𝒆 𝒏𝒆𝒘 𝒖𝒔𝒆𝒓𝒔 𝒄𝒐𝒎𝒊𝒏𝒈 𝒕𝒐 𝒚𝒐𝒖𝒓 𝒈𝒓𝒐𝒖𝒑."
            "\n𝒔𝒆𝒏𝒅 `/setwelcome [message]` 𝒕𝒐 𝒔𝒆𝒕 𝒂 𝒘𝒆𝒍𝒄𝒐𝒎𝒆 𝒎𝒆𝒔𝒔𝒂𝒈𝒆!",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="◁", callback_data="meteor_")]]
            ),
        )

    elif query.data == "meteor_notes":
        query.message.edit_text(
            text=f"<b>๏ 𝑺𝒆𝒕𝒕𝒊𝒏𝒈 𝒖𝒑 𝒏𝒐𝒕𝒆𝒔</b>"
            f"\n𝒀𝒐𝒖 𝒄𝒂𝒏 𝒔𝒂𝒗𝒆 𝒎𝒆𝒔𝒔𝒂𝒈𝒆/𝒎𝒆𝒅𝒊𝒂/𝒂𝒖𝒅𝒊𝒐 𝒐𝒓 𝒂𝒏𝒚𝒕𝒉𝒊𝒏𝒈 𝒂𝒔 𝒏𝒐𝒕𝒆𝒔"
            f"\n𝒕𝒐 𝒈𝒆𝒕 𝒂 𝒏𝒐𝒕𝒆 𝒔𝒊𝒎𝒑𝒍𝒚 𝒖𝒔𝒆 # 𝒂𝒕 𝒕𝒉𝒆 𝒃𝒆𝒈𝒊𝒏𝒏𝒊𝒏𝒈 𝒐𝒇 𝒂 𝒘𝒐𝒓𝒅"
            f"\n\n𝒀𝒐𝒖 𝒄𝒂𝒏 𝒂𝒍𝒔𝒐 𝒔𝒆𝒕 𝒃𝒖𝒕𝒕𝒐𝒏𝒔 𝒇𝒐𝒓 𝒏𝒐𝒕𝒆𝒔 𝒂𝒏𝒅 𝒇𝒊𝒍𝒕𝒆𝒓𝒔 (𝒓𝒆𝒇𝒆𝒓 𝒉𝒆𝒍𝒑 𝒎𝒆𝒏𝒖)",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="◁", callback_data="meteor_")]]
            ),
        )
    elif query.data == "meteor_support":
        query.message.edit_text(
            text="*๏ 𝑴𝒆𝒕𝒆𝒐𝒓 𝒔𝒖𝒑𝒑𝒐𝒓𝒕 𝒄𝒉𝒂𝒕𝒔*"
            f"\n𝑱𝒐𝒊𝒏 𝑴𝒚 𝑺𝒖𝒑𝒑𝒐𝒓𝒕 𝑮𝒓𝒐𝒖𝒑/𝑪𝒉𝒂𝒏𝒏𝒆𝒍 𝒇𝒐𝒓 𝒔𝒆𝒆 𝒐𝒓 𝒓𝒆𝒑𝒐𝒓𝒕 𝒂 𝒑𝒓𝒐𝒃𝒍𝒆𝒎 𝒐𝒏 {dispatcher.bot.first_name}.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="Sᴜᴘᴘᴏʀᴛ", url="t.me/Silent_robo_11"),
                    InlineKeyboardButton(text="Uᴘᴅᴀᴛᴇ", url="https://t.me/Mine_Bots"),
                 ],
                 [
                    InlineKeyboardButton(text="◁", callback_data="meteor_"),
                 
                 ]
                ]
            ),
        )


    elif query.data == "meteor_credit":
        query.message.edit_text(
            text=f"๏ 𝑪𝒓𝒆𝒅𝒊𝒔 𝒇𝒐𝒓 {dispatcher.bot.first_name}\n"
            f"\n𝑯𝒆𝒓𝒆 𝒅𝒆𝒗𝒆𝒍𝒐𝒑𝒆𝒓 𝒐𝒇 𝒕𝒉𝒊𝒔 𝒓𝒆𝒑𝒐",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="Wᴏʟғ", url="https://github.com/Revenger2901"),
                 ],
                 [
                    InlineKeyboardButton(text="◁", callback_data="meteor_"),
                 ]
                ]
            ),
        )

def Source_about_callback(update, context):
    query = update.callback_query
    if query.data == "source_":
        query.message.edit_text(
            text="๏›› 𝑻𝒉𝒊𝒔 𝒂𝒅𝒗𝒂𝒏𝒄𝒆 𝒄𝒐𝒎𝒎𝒂𝒏𝒅 𝒇𝒐𝒓 𝑴𝒖𝒔𝒊𝒄𝒑𝒍𝒂𝒚𝒆𝒓."
            "\n\n๏ 𝑪𝒐𝒎𝒎𝒂𝒏𝒅 𝒇𝒐𝒓 𝒂𝒅𝒎𝒊𝒏𝒔 𝒐𝒏𝒍𝒚."
            "\n • `/reload` - 𝑭𝒐𝒓 𝒓𝒆𝒇𝒓𝒆𝒔𝒉𝒊𝒏𝒈 𝒕𝒉𝒆 𝒂𝒅𝒎𝒊𝒏𝒍𝒊𝒔𝒕."
            "\n • `/pause` - 𝑻𝒐 𝒑𝒂𝒖𝒔𝒆 𝒕𝒉𝒆 𝒑𝒍𝒂𝒚𝒃𝒂𝒄𝒌."
            "\n • `/resume` - 𝑻𝒐 𝒓𝒆𝒔𝒖𝒎𝒊𝒏𝒈 𝒕𝒉𝒆 𝒑𝒍𝒂𝒚𝒃𝒂𝒄𝒌 𝒀𝒐𝒖'𝒗𝒆 𝒑𝒂𝒖𝒔𝒆𝒅."
            "\n • `/skip` - 𝑻𝒐 𝒔𝒌𝒊𝒑𝒑𝒊𝒏𝒈 𝒕𝒉𝒆 𝒑𝒍𝒂𝒚𝒆𝒓."
            "\n • `/end` - 𝑭𝒐𝒓 𝒆𝒏𝒅 𝒕𝒉𝒆 𝒑𝒍𝒂𝒚𝒃𝒂𝒄𝒌."
            "\n • `/musicplayer <on/off>` - 𝑻𝒐𝒈𝒈𝒍𝒆 𝒇𝒐𝒓 𝒕𝒖𝒓𝒏 𝑶𝑵 𝒐𝒓 𝒕𝒖𝒓𝒏 𝑶𝑭𝑭 𝒕𝒉𝒆 𝒎𝒖𝒔𝒊𝒄𝒑𝒍𝒂𝒚𝒆𝒓."
            "\n\n๏ 𝑪𝒐𝒎𝒎𝒂𝒏𝒅 𝒇𝒐𝒓 𝒂𝒍𝒍 𝒎𝒆𝒎𝒃𝒆𝒓𝒔."
            "\n • `/play` <𝒒𝒖𝒆𝒓𝒚 /𝒓𝒆𝒑𝒍𝒚 𝒂𝒖𝒅𝒊𝒐> - 𝑷𝒍𝒂𝒚𝒊𝒏𝒈 𝒎𝒖𝒔𝒊𝒄 𝒗𝒊𝒂 𝒀𝒐𝒖𝑻𝒖𝒃𝒆."
            "\n • `/playlist` - 𝑻𝒐 𝒑𝒍𝒂𝒚𝒊𝒏𝒈 𝒂 𝒑𝒍𝒂𝒚𝒍𝒊𝒔𝒕 𝒐𝒇 𝒈𝒓𝒐𝒖𝒑𝒔 𝒐𝒓 𝒚𝒐𝒖𝒓 𝒑𝒆𝒓𝒔𝒐𝒏𝒂𝒍 𝒑𝒍𝒂𝒚𝒍𝒊𝒔𝒕",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="◁", callback_data="meteor_")
                 ]
                ]
            ),
        )
    elif query.data == "source_back":
        first_name = update.effective_user.first_name
        uptime = get_readable_time((time.time() - StartTime))
        query.message.edit_text(
                PM_START_TEXT.format(
                    escape_markdown(first_name),
                    escape_markdown(uptime),
                    sql.num_users(),
                    sql.num_chats()),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
        )

def get_help(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:
        if len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
            module = args[1].lower()
            update.effective_message.reply_text(
                f" Cᴏɴᴛᴇᴄᴛ ᴍᴇ ɪɴ ᴘᴍ ᴛᴏ ɢᴀᴛ ʜᴇʟᴘ ᴏғ  {module.capitalize()}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Hᴇʟᴘ",
                                url="t.me/{}?start=ghelp_{}".format(
                                    context.bot.username, module
                                ),
                            )
                        ]
                    ]
                ),
            )
            return
        update.effective_message.reply_text(
            "𝑪𝒐𝒏𝒕𝒂𝒄𝒕 𝒎𝒆 𝒊𝒏 𝑷𝑴 𝒕𝒐 𝒈𝒆𝒕 𝒕𝒉𝒆 𝒍𝒊𝒔𝒕 𝒐𝒇 𝒑𝒐𝒔𝒔𝒊𝒃𝒍𝒆 𝒄𝒐𝒎𝒎𝒂𝒏𝒅𝒔.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Hᴇʟᴘ",
                            url="t.me/{}?start=help".format(context.bot.username),
                        )
                    ]
                ]
            ),
        )
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = (
            "𝑯𝒆𝒓𝒆 𝒊𝒔 𝒕𝒉𝒆 𝒂𝒗𝒂𝒊𝒍𝒂𝒃𝒍𝒆 𝒉𝒆𝒍𝒑 𝒇𝒐𝒓 𝒕𝒉𝒆 *{}* module:\n".format(
                HELPABLE[module].__mod_name__
            )
            + HELPABLE[module].__help__
        )
        send_help(
            chat.id,
            text,
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="◁", callback_data="help_back")]]
            ),
        )

    else:
        send_help(chat.id, HELP_STRINGS)


def start_back(update: Update, _: CallbackContext):
    query = update.callback_query
    uptime = get_readable_time((time.time() - StartTime))
    if query.data == "meteor_back":
        first_name = update.effective_user.first_name
        query.message.edit_text(
            PM_START_TEXT.format(
                escape_markdown(first_name),
                escape_markdown(uptime),
                sql.num_users(),
                sql.num_chats(),
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
            timeout=60,
            disable_web_page_preview=True,
        )


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id))
                for mod in USER_SETTINGS.values()
            )
            dispatcher.bot.send_message(
                user_id,
                "𝑻𝒉𝒆𝒔𝒆 𝒂𝒓𝒆 𝒚𝒐𝒖𝒓 𝒄𝒖𝒓𝒓𝒆𝒏𝒕 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            dispatcher.bot.send_message(
                user_id,
                "𝑺𝒆𝒆𝒎𝒔 𝒍𝒊𝒌𝒆 𝒕𝒉𝒆𝒓𝒆 𝒂𝒓𝒆𝒏'𝒕 𝒂𝒏𝒚 𝒖𝒔𝒆𝒓 𝒔𝒑𝒆𝒄𝒊𝒇𝒊𝒄 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔 𝒂𝒗𝒂𝒊𝒍𝒂𝒃𝒍𝒆 :'(",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(
                user_id,
                text="𝑾𝒉𝒊𝒄𝒉 𝒎𝒐𝒅𝒖𝒍𝒆 𝒘𝒐𝒖𝒍𝒅 𝒚𝒐𝒖 𝒍𝒊𝒌𝒆 𝒕𝒐 𝒄𝒉𝒆𝒄𝒌 {}'𝒔 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔 𝒇𝒐𝒓?".format(
                    chat_name
                ),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
        else:
            dispatcher.bot.send_message(
                user_id,
                "𝑺𝒆𝒆𝒎𝒔 𝒍𝒊𝒌𝒆 𝒕𝒉𝒆𝒓𝒆 𝒂𝒓𝒆𝒏'𝒕 𝒂𝒏𝒚 𝒄𝒉𝒂𝒕 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔 𝒂𝒗𝒂𝒊𝒍𝒂𝒃𝒍𝒆 :'(\nSend this "
                "𝒊𝒏 𝒂 𝒈𝒓𝒐𝒖𝒑 𝒄𝒉𝒂𝒕 𝒚𝒐𝒖'𝒓𝒆 𝒂𝒅𝒎𝒊𝒏 𝒊𝒏 𝒕𝒐 𝒇𝒊𝒏𝒅 𝒊𝒕𝒔 𝒄𝒖𝒓𝒓𝒆𝒏𝒕 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔!",
                parse_mode=ParseMode.MARKDOWN,
            )


def settings_button(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    bot = context.bot
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(
                escape_markdown(chat.title), CHAT_SETTINGS[module].__mod_name__
            ) + CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="◁",
                                callback_data="stngs_back({})".format(chat_id),
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                "𝑯𝒊 𝒕𝒉𝒆𝒓𝒆! 𝑻𝒉𝒆𝒓𝒆 𝒂𝒓𝒆 𝒒𝒖𝒊𝒕𝒆 𝒂 𝒇𝒆𝒘 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔 𝒇𝒐𝒓 {} - 𝒈𝒐 𝒂𝒉𝒆𝒂𝒅 𝒂𝒏𝒅 𝒑𝒊𝒄𝒌 𝒘𝒉𝒂𝒕 "
                "𝒚𝒐𝒖'𝒓𝒆 𝒊𝒏𝒕𝒆𝒓𝒆𝒔𝒕𝒆𝒅 𝒊𝒏.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                "𝑯𝒊 𝒕𝒉𝒆𝒓𝒆! 𝑻𝒉𝒆𝒓𝒆 𝒂𝒓𝒆 𝒒𝒖𝒊𝒕𝒆 𝒂 𝒇𝒆𝒘 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔 𝒇𝒐𝒓 {} - 𝒈𝒐 𝒂𝒉𝒆𝒂𝒅 𝒂𝒏𝒅 𝒑𝒊𝒄𝒌 𝒘𝒉𝒂𝒕 "
                "𝒚𝒐𝒖'𝒓𝒆 𝒊𝒏𝒕𝒆𝒓𝒆𝒔𝒕𝒆𝒅 𝒊𝒏.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                text="𝑯𝒊 𝒕𝒉𝒆𝒓𝒆! 𝑻𝒉𝒆𝒓𝒆 𝒂𝒓𝒆 𝒒𝒖𝒊𝒕𝒆 𝒂 𝒇𝒆𝒘 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔 𝒇𝒐𝒓 {} - 𝒈𝒐 𝒂𝒉𝒆𝒂𝒅 𝒂𝒏𝒅 𝒑𝒊𝒄𝒌 𝒘𝒉𝒂𝒕 "
                "𝒚𝒐𝒖'𝒓𝒆 𝒊𝒏𝒕𝒆𝒓𝒆𝒔𝒕𝒆𝒅 𝒊𝒏.".format(escape_markdown(chat.title)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message not in [
            "Message is not modified",
            "Query_id_invalid",
            "Message can't be deleted",
        ]:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


def get_settings(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "𝑪𝒍𝒊𝒄𝒌 𝒉𝒆𝒓𝒆 𝒕𝒐 𝒈𝒆𝒕 𝒕𝒉𝒊𝒔 𝒄𝒉𝒂𝒕'𝒔 𝒔𝒆𝒕𝒕𝒊𝒏𝒈𝒔, 𝒂𝒔 𝒘𝒆𝒍𝒍 𝒂𝒔 𝒚𝒐𝒖𝒓𝒔."
            msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Settings",
                                url="t.me/{}?start=stngs_{}".format(
                                    context.bot.username, chat.id
                                ),
                            )
                        ]
                    ]
                ),
            )
        else:
            text = "Click here to check your settings."

    else:
        send_settings(chat.id, user.id, True)


def donate(update: Update, context: CallbackContext):
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]
    bot = context.bot
    if chat.type == "private":
        update.effective_message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

        if OWNER_ID != 5642504245:
            update.effective_message.reply_text(
                "I'm free for everyone ❤️ If you wanna make me smile, just join"
                "[My Channel]({})".format(DONATION_LINK),
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        try:
            bot.send_message(
                user.id,
                DONATE_STRING,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )

            update.effective_message.reply_text(
                "I've PM'ed you about donating to my creator!"
            )
        except Unauthorized:
            update.effective_message.reply_text(
                "Contact me in PM first to get donation information."
            )


def migrate_chats(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Successfully migrated!")
    raise DispatcherHandlerStop


def main():

    if SUPPORT_CHAT is not None and isinstance(SUPPORT_CHAT, str):
        try:
            dispatcher.bot.sendMessage(
                f"@{SUPPORT_CHAT}", 
                "👋 Hi, i'm alive.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Unauthorized:
            LOGGER.warning(
                "Bot isnt able to send message to support_chat, go and check!"
            )
        except BadRequest as e:
            LOGGER.warning(e.message)

    test_handler = CommandHandler("test", test, run_async=True)
    start_handler = CommandHandler("start", start, run_async=True)

    help_handler = CommandHandler("help", get_help, run_async=True)
    help_callback_handler = CallbackQueryHandler(
        help_button, pattern=r"help_.*", run_async=True
    )
    start_callback_handler = CallbackQueryHandler(
        start_back, pattern=r"meteor_back", run_async=True
    )

    settings_handler = CommandHandler("settings", get_settings, run_async=True)
    settings_callback_handler = CallbackQueryHandler(
        settings_button, pattern=r"stngs_", run_async=True
    )

    about_callback_handler = CallbackQueryHandler(
        meteor_about_callback, pattern=r"meteor_", run_async=True
    )

    source_callback_handler = CallbackQueryHandler(
        Source_about_callback, pattern=r"source_", run_async=True
    )

    donate_handler = CommandHandler("donate", donate, run_async=True)
    migrate_handler = MessageHandler(
        Filters.status_update.migrate, migrate_chats, run_async=True
    )

    dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(about_callback_handler)
    dispatcher.add_handler(start_callback_handler)
    dispatcher.add_handler(source_callback_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(donate_handler)

    dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN, certificate=open(CERT_PATH, "rb"))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Using long polling.")
        updater.start_polling(timeout=15, read_latency=4, drop_pending_updates=True)

    if len(argv) not in (1, 3, 4):
        telethn.disconnect()
    else:
        telethn.run_until_disconnected()

    updater.idle()


if __name__ == "__main__":
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    telethn.start(bot_token=TOKEN)
    pbot.start()
    main()
