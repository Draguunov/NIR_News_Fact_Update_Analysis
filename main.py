import os
import json
import requests
import feedparser
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# =========================
# НАСТРОЙКИ
# =========================
RSS_SOURCES = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "Habr AI": "https://habr.com/ru/rss/hubs/artificial_intelligence/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
}

# # GigaChat
# API_URL = os.getenv("LLM_API_URL", "")
# API_KEY = os.getenv("LLM_API_KEY", "")
# MODEL_NAME = os.getenv("LLM_MODEL_NAME", "")
# # Deepseek
# API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
# API_KEY = os.getenv("LLM_API_KEY", "")
# MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
#Z.ai
API_URL = os.getenv("LLM_API_URL", "https://api.z.ai/api/paas/v4/chat/completions") # Базовый URL Z.AI
API_KEY = os.getenv("LLM_API_KEY", "93be00b540504e3ebc6f6d070a2d8860.zqW6qbNWSmhKR8Mw")
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "GLM-4.7-Flash") # название модели
# # GPT-4-o-mini
# API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions") ,  # Базовый URL Z.AI
# API_KEY = os.getenv("LLM_API_KEY", "")
# MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini") # название модели

st.write(API_URL, API_KEY[:5] + "...", MODEL_NAME)


# =========================
# RSS
# =========================
def load_rss_articles(rss_url: str, limit: int = 5):
    feed = feedparser.parse(rss_url)

    articles = []
    for entry in feed.entries[:limit]:
        title = getattr(entry, "title", "").strip()
        summary = getattr(entry, "summary", "").strip()
        link = getattr(entry, "link", "").strip()

        text = f"Заголовок: {title}\nОписание: {summary}\nСсылка: {link}"
        articles.append(
            {
                "title": title,
                "summary": summary,
                "link": link,
                "text": text,
            }
        )
    return articles


# =========================
# ПРОМПТ
# =========================
def build_prompt(article_texts: list[str]) -> str:
    joined_articles = "\n\n".join(
        [f"Статья {i+1}:\n{text}" for i, text in enumerate(article_texts)]
    )

    prompt = f"""
Ты выступаешь как аналитик новостных событий.

Ниже приведены несколько новостных статей.

Твоя задача:
1. Определи, описывают ли статьи одно и то же событие.
2. Если да, сформируй краткую сводку известных фактов.
3. Сравни последнюю статью с предыдущими.
4. Определи, содержит ли последняя статья новый факт.
5. Если новый факт есть, выпиши его отдельно.
6. Ответ верни в JSON формате со следующими полями:
{{
  "same_event": true/false,
  "summary": "краткая сводка",
  "has_new_fact": true/false,
  "new_fact": "текст нового факта или пустая строка",
  "reason": "краткое объяснение"
}}

Статьи:
{joined_articles}
"""
    return prompt.strip()


# =========================
# ВЫЗОВ LLM
# =========================
def call_llm_api(prompt: str) -> str:
    """
    Универсальный вызов OpenAI-compatible API.
    Для GigaChat/DeepSeek может понадобиться поправить поля.
    """

    if not API_URL or not API_KEY or not MODEL_NAME:
        return demo_llm_response()

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "Ты аккуратный аналитик новостей. Отвечай строго в JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2
    }

    response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()

    # для OpenAI-compatible API
    return data["choices"][0]["message"]["content"]


# =========================
# ДЕМО-РЕЖИМ
# =========================
def demo_llm_response() -> str:
    demo = {
        "same_event": True,
        "summary": "Статьи описывают одно технологическое событие и содержат частично пересекающиеся факты о новом ИИ-продукте или обновлении.",
        "has_new_fact": True,
        "new_fact": "В последней статье присутствует новое уточнение о функции продукта или сроках запуска.",
        "reason": "Основная тема совпадает, но последняя статья добавляет уточняющую информацию."
    }
    return json.dumps(demo, ensure_ascii=False, indent=2)


# =========================
# ОБРАБОТКА ОТВЕТА
# =========================
def parse_llm_response(raw_text: str):
    try:
        cleaned = raw_text.strip()

        # Убираем markdown-обёртку ```json ... ```
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[len("```"):].strip()

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        return json.loads(cleaned), None

    except Exception as e:
        return None, str(e)
# def parse_llm_response(raw_text: str):
#     try:
#         return json.loads(raw_text), None
#     except Exception as e:
#         return None, str(e)


# =========================
# GUI
# =========================
st.set_page_config(page_title="Анализ новостных обновлений", layout="wide")

st.title("Система анализа обновлений фактов в новостях")
st.write(
    "Прототип получает новости из RSS, отправляет их в LLM и определяет, "
    "относятся ли статьи к одному событию, а также выделяет новые факты."
)

with st.sidebar:
    st.header("Настройки")
    source_name = st.selectbox("Выберите RSS-источник", list(RSS_SOURCES.keys()))
    article_limit = st.slider("Количество новостей", min_value=2, max_value=10, value=4)

    st.markdown("### Режим API")
    if API_URL and API_KEY and MODEL_NAME:
        st.success("API настроен")
    else:
        st.warning("API не настроен — будет использован демо-режим")

rss_url = RSS_SOURCES[source_name]

if st.button("Загрузить новости"):
    st.session_state["articles"] = load_rss_articles(rss_url, article_limit)

articles = st.session_state.get("articles", [])

if articles:
    st.subheader("Загруженные новости")

    selected_indices = []
    for idx, article in enumerate(articles):
        with st.expander(f"Статья {idx+1}: {article['title']}"):
            st.write(article["summary"])
            st.markdown(f"[Открыть источник]({article['link']})")
            use_article = st.checkbox(
                f"Использовать статью {idx+1} в анализе",
                value=True,
                key=f"use_article_{idx}"
            )
            if use_article:
                selected_indices.append(idx)

    if len(selected_indices) < 2:
        st.info("Выберите хотя бы 2 статьи для анализа.")
    else:
        if st.button("Анализировать"):
            selected_texts = [articles[i]["text"] for i in selected_indices]
            prompt = build_prompt(selected_texts)

            with st.expander("Показать промпт"):
                st.code(prompt, language="text")

            with st.spinner("Отправка запроса в модель..."):
                try:
                    raw_answer = call_llm_api(prompt)
                    parsed_answer, error = parse_llm_response(raw_answer)

                    st.subheader("Ответ модели")
                    st.code(raw_answer, language="json")

                    if error:
                        st.error(f"Не удалось распарсить JSON: {error}")
                    else:
                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric("Одно событие", "Да" if parsed_answer.get("same_event") else "Нет")
                            st.metric("Новый факт", "Да" if parsed_answer.get("has_new_fact") else "Нет")

                        with col2:
                            st.write("**Краткое объяснение:**")
                            st.write(parsed_answer.get("reason", ""))

                        st.write("### Сводка")
                        st.write(parsed_answer.get("summary", ""))

                        st.write("### Новый факт")
                        st.write(parsed_answer.get("new_fact", ""))

                except Exception as e:
                    st.error(f"Ошибка при вызове модели: {e}")
else:
    st.info("Нажми «Загрузить новости», чтобы начать.")