async def send_email(to_address: str, subject: str, body: str) -> dict:
    return {
        "status": "pending",
        "to": to_address,
        "subject": subject,
        "body_length": len(body),
    }
