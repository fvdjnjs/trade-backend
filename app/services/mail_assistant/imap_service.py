async def fetch_recent_messages(mailbox: str) -> list[dict]:
    return [
        {
            "mailbox": mailbox,
            "subject": "占位邮件",
            "sender": "customer@example.com",
        }
    ]
