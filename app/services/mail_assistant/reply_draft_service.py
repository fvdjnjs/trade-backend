from app.core.config import get_settings
from app.prompts import SYSTEM_PROMPTS
from app.schemas.email import ReplyDraftRequest
from app.services.mail_assistant.rag_service import retrieve_relevant_context


async def generate_reply_draft(payload: ReplyDraftRequest) -> str:
    context = await retrieve_relevant_context(payload.customer_message)
    settings = get_settings()

    if not settings.openai_api_key:
        return (
            "Draft reply only - please review before sending.\n\n"
            "Hi,\n\n"
            "Thanks for your message. I understand your question and we are checking the details carefully. "
            "I will come back with a clear answer shortly.\n\n"
            f"Reference context: {context}\n"
            f"Preferred tone: {payload.tone}\n\n"
            "Best regards,"
        )

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPTS["inquiry_reply"]},
            {
                "role": "user",
                "content": (
                    f"Preferred tone: {payload.tone}\n\n"
                    f"Relevant context:\n{context}\n\n"
                    f"Customer email:\n{payload.customer_message[:6000]}"
                ),
            },
        ],
    )

    draft = response.choices[0].message.content or ""
    return f"Draft reply only - please review before sending.\n\n{draft.strip()}"
