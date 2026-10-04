import asyncio
import json
import logging
import os
import random
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

# Токен берется автоматически из настроек Render (Environment Variables)
TOKEN = os.getenv("BOT_TOKEN")

# Загружаем вопросы из JSON-файла
with open("questions.json", "r", encoding="utf-8") as f:
  QUESTIONS_DB = json.load(f)


class QuizState(StatesGroup):
  waiting_for_answer = State()


router = Router()


async def send_random_question(message_or_callback, state: FSMContext):
  # Выбираем случайный вопрос
  q_data = random.choice(QUESTIONS_DB)

  # Сохраняем текущий вопрос в состояние пользователя
  await state.update_data(current_question=q_data)
  await state.set_state(QuizState.waiting_for_answer)

  # Формируем полный список вариантов, чтобы они были отлично видны в тексте
  options_text = ""
  for idx, opt in enumerate(q_data["options_nl"]):
    options_text += f"<b>{idx + 1}.</b> {opt}\n"

  text = (
      f"<b>Вопрос VCA VOL:</b>\n\n"
      f"🇳🇱 <i>{q_data['question_nl']}</i>\n"
      f"🇷🇺 <b>({q_data['question_ru']})</b>\n\n"
      f"<b>Варианты ответа:</b>\n{options_text}\n"
      f"👇 <i>Нажми соответствующую кнопку ниже:</i>"
  )

  # Делаем кнопки короткими (только цифры/варианты), чтобы они никогда не обрезались
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text=f"Вариант {i+1}", callback_data=f"answer_{i}"
              )
          ]
          for i in range(len(q_data["options_nl"]))
      ]
  )

  if isinstance(message_or_callback, CallbackQuery):
    await message_or_callback.message.edit_text(
        text, reply_markup=keyboard, parse_mode="HTML"
    )
    await message_or_callback.answer()
  else:
    await message_or_callback.answer(
        text, reply_markup=keyboard, parse_mode="HTML"
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
  await state.clear()
  await message.answer(
      "Привет! Это бот-тренажер для подготовки к экзамену VCA VOL.\n\n"
      "Я буду задавать вопросы на английском с русским переводом. "
      "Все варианты будут видны в сообщении, а внизу будут удобные кнопки.\n\n"
      "Нажми /next, чтобы получить первый вопрос!"
  )


@router.message(Command("next"))
async def cmd_next(message: Message, state: FSMContext):
  await send_random_question(message, state)


@router.callback_query(QuizState.waiting_for_answer, F.data.startswith("answer_"))
async def process_answer(callback: CallbackQuery, state: FSMContext):
  user_choice = int(callback.data.split("_")[1])
  data = await state.get_data()
  q_data = data.get("current_question")

  correct_idx = q_data["correct_index"]
  is_correct = user_choice == correct_idx

  # Формируем результат
  result_emoji = "✅ Верно!" if is_correct else "❌ Неверно!"

  options_translation_text = ""
  for i, (opt_nl, opt_ru) in enumerate(
      zip(q_data["options_nl"], q_data["options_ru"])
  ):
    marker = "👉 " if i == correct_idx else "    "
    options_translation_text += f"{marker}{i+1}. {opt_nl}\n    🇷🇺 <i>{opt_ru}</i>\n"

  response_text = (
      f"<b>{result_emoji}</b>\n\n"
      f"<b>Вопрос:</b>\n🇳🇱 {q_data['question_nl']}\n🇷🇺"
      f" {q_data['question_ru']}\n\n"
      f"<b>Все варианты и перевод:</b>\n{options_translation_text}\n"
      f"💡 <b>Пояснение:</b> {q_data['explanation_ru']}"
  )

  next_keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="Следующий вопрос ➡️", callback_data="next_question"
              )
          ]
      ]
  )

  await callback.message.edit_text(
      response_text, reply_markup=next_keyboard, parse_mode="HTML"
  )


@router.callback_query(F.data == "next_question")
async def next_question_callback(callback: CallbackQuery, state: FSMContext):
  await send_random_question(callback, state)


async def main():
  logging.basicConfig(level=logging.INFO)
  bot = Bot(token=TOKEN)
  dp = Dispatcher()
  dp.include_router(router)

  print("Бот успешно запущен и ждет сообщения...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
