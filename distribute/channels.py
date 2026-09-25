#!/usr/bin/env python3
"""
Canais de distribuicao social: Threads, Bluesky e Telegram.

Clientes finos sobre as APIs oficiais (somente requests + stdlib).
Nenhuma chamada de IA: o conteudo e 100% deterministico.
"""

import datetime

import requests


def _mask(message, *secrets):
    """Remove credenciais de mensagens de erro (defensivo)."""
    for secret in secrets:
        if secret:
            message = message.replace(secret, "***")
    return message


class ThreadsClient:
    """Publica texto no Threads via Graph API (Instagram/Threads)."""

    BASE = "https://graph.threads.net/v1.0"
    MAX_LEN = 500

    def __init__(self, token, user_id):
        self.token = token
        self.user_id = user_id

    def post_text(self, text):
        """Cria container de texto e publica; retorna o id do post."""
        if len(text) > self.MAX_LEN:
            raise ValueError(
                "Threads text too long: %d > %d (trunque antes de chamar)"
                % (len(text), self.MAX_LEN)
            )
        container = self._post(
            "%s/%s/threads" % (self.BASE, self.user_id),
            {"media_type": "TEXT", "text": text, "access_token": self.token},
        )
        published = self._post(
            "%s/%s/threads_publish" % (self.BASE, self.user_id),
            {"creation_id": container["id"], "access_token": self.token},
        )
        return published["id"]

    def reply_to(self, post_id, text):
        """Cria e publica uma resposta (link no primeiro comentario). Best-effort."""
        try:
            container = self._post(
                "%s/%s/threads" % (self.BASE, self.user_id),
                {
                    "media_type": "TEXT",
                    "text": text,
                    "reply_to": post_id,
                    "access_token": self.token,
                },
            )
            published = self._post(
                "%s/%s/threads_publish" % (self.BASE, self.user_id),
                {"creation_id": container["id"], "access_token": self.token},
            )
            return published["id"]
        except Exception:
            return None

    def _post(self, url, payload):
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code >= 300:
            raise RuntimeError(
                "Threads API error %s: %s"
                % (resp.status_code, _mask(resp.text[:300], self.token))
            )
        return resp.json()


class BlueskyClient:
    """Publica texto no Bluesky via AT Protocol (com.atproto)."""

    BASE = "https://bsky.social/xrpc"
    MAX_LEN = 300

    def __init__(self, handle, app_password):
        self.handle = handle
        self.app_password = app_password

    def post_text(self, text, link_url=None):
        """Cria sessao e publica um post; retorna o URI do record.

        Se link_url for passado, adiciona um facet de link na URL
        (necessario para o link ser clicavel no cliente Bluesky).
        """
        if len(text) > self.MAX_LEN:
            raise ValueError(
                "Bluesky text too long: %d > %d (trunque antes de chamar)"
                % (len(text), self.MAX_LEN)
            )
        session = self._post(
            "%s/com.atproto.server.createSession" % self.BASE,
            {"identifier": self.handle, "password": self.app_password},
        )
        access_jwt = session["accessJwt"]
        did = session["did"]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        record = {"$type": "app.bsky.feed.post", "text": text, "createdAt": now}
        if link_url:
            start = text.find(link_url)
            if start != -1:
                prefix = text[:start].encode("utf-8")
                byte_start = len(prefix)
                byte_end = byte_start + len(link_url.encode("utf-8"))
                record["facets"] = [
                    {
                        "index": {"byteStart": byte_start, "byteEnd": byte_end},
                        "features": [
                            {"$type": "app.bsky.richtext.facet#link", "uri": link_url}
                        ],
                    }
                ]
        record = self._post(
            "%s/com.atproto.repo.createRecord" % self.BASE,
            {
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
            headers={"Authorization": "Bearer %s" % access_jwt},
        )
        return record["uri"]

    def _post(self, url, payload, headers=None):
        resp = requests.post(url, json=payload, headers=headers or {}, timeout=30)
        if resp.status_code >= 300:
            raise RuntimeError(
                "Bluesky API error %s: %s"
                % (resp.status_code, _mask(resp.text[:300], self.app_password))
            )
        return resp.json()


class TelegramClient:
    """Envia mensagem para um chat do Telegram via Bot API."""

    BASE = "https://api.telegram.org"

    def __init__(self, bot_token):
        self.bot_token = bot_token

    def send_message(self, chat_id, text):
        """Envia mensagem HTML; retorna o message_id.

        O caller DEVE escapar o conteudo dinamico com html.escape antes de
        chamar (parse_mode=HTML).
        """
        resp = requests.post(
            "%s/bot%s/sendMessage" % (self.BASE, self.bot_token),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(
                "Telegram API error %s: %s"
                % (resp.status_code, _mask(resp.text[:300], self.bot_token))
            )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError("Telegram API error: %s" % data.get("description", "unknown"))
        return data["result"]["message_id"]