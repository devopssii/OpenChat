from uuid import uuid4

from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from web.models.chatbot import Chatbot
from web.models.chatbot_settings import ChatbotSetting
from web.models.chat_histories import ChatHistory
from web.services.handle_pdf_datasource import HandlePdfDataSource
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseServerError
from web.signals.chatbot_was_created import chatbot_was_created
from web.enums.chatbot_initial_prompt_enum import ChatBotInitialPromptEnum
from web.enums.common_enums import ChatBotDefaults
from uuid import uuid4
from web.utils.common import get_session_id
from web.utils.common import generate_chatbot_name
from api.utils.get_prompts import get_qa_prompt_by_mode
from django.utils import timezone

import requests
from uuid import uuid4
import re

from django.shortcuts import get_object_or_404

def index(request):
    chatbots = Chatbot.objects.all()
    return render(request, 'index.html', {'chatbots': chatbots})

@require_POST
def create_via_website_flow(request):
    name = request.POST.get('name') or ChatBotDefaults.NAME.value
    website = request.POST.get('website')
    prompt_message = request.POST.get('prompt_message') or ChatBotInitialPromptEnum.AI_ASSISTANT_INITIAL_PROMPT.value

    chatbot = Chatbot.objects.create(
        id=uuid4(),
        name=name,
        token=str(uuid4())[:20],
        website=website,
        prompt_message=prompt_message
    )
    
    return HttpResponseRedirect(reverse('onboarding.config', args=[str(chatbot.id)]))


@require_POST
def update_character_settings(request, id):
    print("update_character_settings", str(id))

    chatbot_id = id # request.POST.get('chatbot_id')
    character_name = request.POST.get('character_name')

    chatbot = Chatbot.objects.get(id=chatbot_id)
    # chatbot.create_or_update_setting('character_name', character_name)
    ChatbotSetting.objects.update_or_create(chatbot_id=chatbot.id, defaults={'name': character_name})
    return HttpResponseRedirect(reverse('onboarding.done', args=[str(chatbot.id)]))

@require_POST
def send_message(request, token):
    # Find the chatbot by token
    bot = get_object_or_404(Chatbot, token=token)

    # Get the question and history from the request
    question = request.POST.get('question')
    session_id = get_session_id(request=request, bot_id=bot.id)
    history = ChatHistory.objects.filter(session_id=session_id)

    print(history)
    mode = request.POST.get('mode')
    initial_prompt = bot.prompt_message

    # Remove null and empty values and empty arrays or objects from the history
    history = [value for value in history if value is not None and value != '' and value != [] and value != {}]

    # Call the API to send the message to the chatbot with a timeout of 5 seconds
    try:
        response = requests.post("http://localhost:3000/api/chat", json={
            'question': question,
            'history': history,
            'namespace': str(bot.id),
            'mode': mode,
            'initial_prompt': initial_prompt,
        }, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        return HttpResponseServerError('Something went wrong')

    # Create a ChatbotResponse instance from the API response
    bot_response = response.json()

    session_id = get_session_id(request, bot.id)

    if session_id is not None:
        # Save chat history
        ChatHistory.objects.create(
            id=uuid4(),
            chatbot=bot,
            from_user=True,
            message=question,
            session_id=session_id
        )
        ChatHistory.objects.create(
            id=uuid4(),
            chatbot=bot,
            from_user=False,
            message=bot_response['botReply'],
            session_id=session_id
        )

    # Return the response from the chatbot
    return JsonResponse({
        'botReply': bot_response['botReply'],
        'sources': bot_response['sources'],
    })


def get_chat_view(request, token):
    # Find the chatbot by token
    bot = get_object_or_404(Chatbot, token=token)

    # Initiate a cookie if it doesn't exist
    cookie_name = 'chatbot_' + str(bot.id)
    if cookie_name not in request.COOKIES:
        cookie_value = str(uuid4())[:20]
        response = render(request, 'chat.html', {'bot': bot})
        response.set_cookie(cookie_name, cookie_value, max_age=60 * 60 * 24 * 365)  # 1 year
        return response

    return render(request, 'chat.html', {'bot': bot})
