import json
import os
import time
import urllib.request
import urllib.error

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_ID = os.environ.get("TELEGRAM_ADMIN_ID", "").strip()
CHANNEL_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

if not TOKEN or not ADMIN_ID or not CHANNEL_ID:
    raise RuntimeError("Telegram üçün tələb olunan dəyişənlər tapılmadı")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"


def telegram(method, data=None, timeout=40):
    payload = json.dumps(data or {}).encode("utf-8")

    request = urllib.request.Request(
        BASE_URL + method,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(f"{method} xətası: {result}")

    return result["result"]


def answer_callback(callback_id, text):
    telegram("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text
    })


def handle_callback(callback):
    callback_id = callback["id"]
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat = message.get("chat", {})
    message_id = message.get("message_id")

    # Yalnız admin təsdiq verə bilər.
    if str(callback.get("from", {}).get("id")) != ADMIN_ID:
        answer_callback(callback_id, "Bu əməliyyata icazəniz yoxdur.")
        return

    # Düymə yalnız şəxsi bot mesajında işləməlidir.
    if str(chat.get("id")) != ADMIN_ID or not message_id:
        answer_callback(callback_id, "Mesaj düzgün deyil.")
        return

    if data == "share":
        telegram("copyMessage", {
            "chat_id": CHANNEL_ID,
            "from_chat_id": ADMIN_ID,
            "message_id": message_id
        })

        telegram("editMessageReplyMarkup", {
            "chat_id": ADMIN_ID,
            "message_id": message_id,
            "reply_markup": {"inline_keyboard": []}
        })

        answer_callback(callback_id, "Meme kanalda paylaşıldı! ✅")
        print(f"Meme kanalda paylaşıldı: {message_id}")

    elif data == "cancel":
        telegram("editMessageReplyMarkup", {
            "chat_id": ADMIN_ID,
            "message_id": message_id,
            "reply_markup": {"inline_keyboard": []}
        })

        answer_callback(callback_id, "Meme ləğv edildi. ❌")
        print(f"Meme ləğv edildi: {message_id}")

    else:
        answer_callback(callback_id, "Naməlum əməliyyat.")


def main():
    print("Futbol AZ təsdiq botu işə düşdü.")
    offset = None

    while True:
        try:
            params = {
                "timeout": 30,
                "allowed_updates": ["callback_query"]
            }

            if offset is not None:
                params["offset"] = offset

            updates = telegram("getUpdates", params, timeout=40)

            for update in updates:
                offset = update["update_id"] + 1

                callback = update.get("callback_query")
                if callback:
                    try:
                        handle_callback(callback)
                    except Exception as error:
                        print(f"Callback xətası: {error}")
                        try:
                            answer_callback(
                                callback["id"],
                                "Xəta baş verdi. Yenidən yoxlayın."
                            )
                        except Exception:
                            pass

        except Exception as error:
            print(f"Bot bağlantı xətası: {error}")
            time.sleep(5)


if __name__ == "__main__":
    main()
