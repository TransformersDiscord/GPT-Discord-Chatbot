import discord
from discord.ext import commands, tasks
import asyncio
import openai
import regex
from dotenv import load_dotenv

import os
import random
import time
import json
from collections import deque
from difflib import SequenceMatcher
from difflib import get_close_matches



# #####################################
# GLOBAL VARIABLES

# keys
load_dotenv()
openai.api_key = os.environ['OPENAI_TOKEN']
BotKey = os.environ['DISCORD_TOKEN']

# bot
client = commands.Bot(command_prefix='$', intents=discord.Intents().all())
client.channel_dict = {}

# config
with open('.config') as f:    config = json.load(f)
personality       = config['personality']
use_chatgpt_model = bool(config['use_chatgpt_model'])
chatgpt_model     = config['chatgpt_model']
gpt4_model     = config['gpt4_model']
gpt3_model     = config['gpt3_model']
admin_role        = config['admin_role']

# GLOBAL VARIABLES
# #####################################



# #####################################
# HELPER DEFINITIONS AND FUNCTIONS 

# a deque dict class
class FixSizedDict(dict):
    def __init__(self, *args, maxlen=0, **kwargs):
        self._maxlen = maxlen
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        if self._maxlen > 0:
            if len(self) > self._maxlen:
                self.pop(next(iter(self)))

def message_clean_up(string):
    # strip
    result = string.strip()
    
    # remove the id inside discord emotes
    string2 = string.replace(':', ' ').replace('>', ' ').replace('<', ' ')
    numbers = [int(word) for word in string2.split() if word.isdigit()]
    for i in numbers:
        if i > 1000000:
            result = result.replace(str(i), '')
    return result

# get messages by author
def get_messages_by_author(message_list, author):
    result_message_list = []
    for message in message_list:
        if (message.author == author):
            result_message_list.append(message)
    return result_message_list

# remove messages by author
def remove_messages_by_author(message_list, author):
    for message in message_list.copy():
        if (message.author == author):
            message_list.remove(message)

# calculate repetition ratio in a message list ( has bug, don't use)
def get_repetition_ratio(message_list):
    if (len(message_list) < 2):
        return 0
    
    total_ratio = 0
    for idx in range(0, len(message_list)-1):
        msg_a = message_list[idx  ].clean_content
        msg_b = message_list[idx+1].clean_content
        total_ratio += SequenceMatcher(None, msg_a, msg_b).ratio()
    total_ratio /= (len(message_list)-1)
    return total_ratio


# get chatgpt response
def get_chatgpt_response(message_list):
    # chatgpt prompt
    prompt = []
    
    # system prompt
    system_prompt = {
        'role' : 'system', 
        'content' : personality
    }
    prompt.append(system_prompt)

    # format the message for the prompt and clear out numbers and other garbage that will confuse the AI
    for msg in message_list:
        # # bot message
        msg_prompt = ''
        if msg.author == client.user:
            msg_prompt = {
                'role' : 'assistant', 
                'content' : message_clean_up(msg.author.display_name) + ': ' + message_clean_up(msg.clean_content)
            }
        # # user message
        else:
            msg_prompt = {
                'role' : 'user', 
                'content' : message_clean_up(msg.author.display_name) + ': ' + message_clean_up(msg.clean_content)
            }
        # # add to prompt
        prompt.append(msg_prompt)

    # Get AI response
    response = openai.ChatCompletion.create(
        model=chatgpt_model,
        messages=prompt,
        temperature=1,
        max_tokens=150,
        top_p=1,
        frequency_penalty=1.5,
        presence_penalty=0.2 # ,
        # stop=[client.user.name + ':', message_clean_up(msg.author.display_name) + ':']
    )
    rspns_text = response['choices'][0]['message']['content']
    rspns_text = regex.sub(client.user.display_name + ':', '', rspns_text)
    return rspns_text

# get gpt4 response
def get_gpt4_response(message_list):
    # gpt4 prompt
    prompt = []
    
    # system prompt
    system_prompt = {
        'role' : 'system', 
        'content' : personality
    }
    prompt.append(system_prompt)

    # format the message for the prompt and clear out numbers and other garbage that will confuse the AI
    for msg in message_list:
        # # bot message
        msg_prompt = ''
        if msg.author == client.user:
            msg_prompt = {
                'role' : 'assistant', 
                'content' : message_clean_up(msg.author.display_name) + ': ' + message_clean_up(msg.clean_content)
            }
        # # user message
        else:
            msg_prompt = {
                'role' : 'user', 
                'content' : message_clean_up(msg.author.display_name) + ': ' + message_clean_up(msg.clean_content)
            }
        # # add to prompt
        prompt.append(msg_prompt)

    # Get AI response
    response = openai.ChatCompletion.create(
        model=gpt4_model,
        messages=prompt,
        temperature=1,
        max_tokens=150,
        top_p=1,
        frequency_penalty=1.5,
        presence_penalty=0.2 # ,
        # stop=[client.user.name + ':', message_clean_up(msg.author.display_name) + ':']
    )
    rspns_text = response['choices'][0]['message']['content']
    rspns_text = regex.sub(client.user.display_name + ':', '', rspns_text)
    return rspns_text

def get_gpt3_response(message_list):
    # gpt3 prompt
    prompt = ''

    # format the message for the prompt and clear out numbers and other garbage that will confuse the AI
    for msg in message_list:
        prompt += message_clean_up(msg.author.display_name) + ': ' + message_clean_up(msg.clean_content) + '\n'
        
    prompt += '(Continue the conversation. ' + personality + ')\n'
    prompt += client.user.name + ':'

    # Get AI response
    response = openai.Completion.create(
        model=gpt3_model,
        prompt=prompt,
        temperature=1,
        max_tokens=150,
        top_p=1,
        frequency_penalty=1.5,
        presence_penalty=0.2,
        stop=[client.user.name + ':', message_clean_up(msg.author.display_name) + ':']
    )
    rspns_text = response['choices'][0]['text']
    return rspns_text
    
# HELPER DEFINITIONS AND FUNCTIONS
# #####################################


# #####################################
# ASYNC FUNCTIONS

@client.command(name='flush')
async def flush(ctx, mention, channel: discord.TextChannel = None):
    if mention == client.user.mention and [r for r in ctx.author.roles if r.name == admin_role]:
        if channel == None:
            channel = ctx.channel
        client.channel_dict[channel.id] = [deque(maxlen=5), FixSizedDict(maxlen=12), deque(maxlen=9)]
        await ctx.send(f'My memory in {channel.mention} channel has been flushed.')


@client.command(name='model')
async def model(ctx, mention, *args):
    if mention == client.user.mention and [r for r in ctx.author.roles if r.name == admin_role]:
        # incorrect arguments
        if len(args) != 1 or (args[0] != 'gpt3' and args[0] != 'chatgpt' and args[0] != 'gpt4'):
            await ctx.send('Please use command\n`$model @{0} gpt3` or\n`$model @{0} chatgpt`.'.format(client.user.name))
        
        # gpt3
        elif args[0] == 'gpt3':
            use_chatgpt_model = False
            use_gpt4_model = False
            await ctx.send('I will use openai\'s gpt3 model.')
        elif args[0] == 'chatgpt':
            use_gpt4_model = False
            use_chatgpt_model = True          
            await ctx.send('I will use openai\'s chatgpt model.')
        elif args[0] == 'gpt4':
            use_chatgpt_model = False
            use_gpt4_model = True
            await ctx.send('I will use openai\'s gpt4 model.')
        else:
            print('Should not get here')


@client.event
async def on_ready():
    global personality
    personality = personality.format(clientName=client.user.name)
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    
    # ignore DMs
    if str(message.channel.type) == 'private':
        return
        
    # keep a history of conversations across channels and servers
    
    # # fetch the history in this channel
    if message.channel.id in client.channel_dict:
        history = client.channel_dict[message.channel.id]
        message_list = history[0]
        name_to_user = history[1]
        last_users   = history[2]
    # # initialize the history in this channel
    else:
        history = [deque(maxlen=5), FixSizedDict(maxlen=12), deque(maxlen=9)]
        client.channel_dict[message.channel.id] = history
        message_list = history[0]
        name_to_user = history[1]
        last_users   = history[2]
    
    # # append non-empty message
    if len(message.content) > 1:
        message_list.append(message)
        
    # flush history of responses when answers get repetitive
    rspns_list = get_messages_by_author(message_list, client.user)
    if get_repetition_ratio(rspns_list) > 0.8:
        remove_messages_by_author(message_list, client.user)

    # put author in this message to last_users
    last_users.append(message.author)
    
    # talk if it's mentioned (sometimes ignore if author is bot)
    invoke_talk = False
    for mention in message.mentions:
        if (mention == client.user):
            random.seed(time.time())
            if (message.author != client.user
                    and not (message.author.bot and random.random() < 0.2)):
                invoke_talk = True
            break
    
    if invoke_talk:
        # # put all mentioned users in name_to_user
        for mention in message.mentions:
            if mention != client.user:
                name_to_user[message_clean_up(mention.display_name)] = mention
        name_to_user[message_clean_up(message.author.display_name)] = message.author
        # # talk
        await talk(message, history)
        
    # process commands
    await client.process_commands(message)


async def talk(message, history):
    await asyncio.sleep(0.5)
    
    # set the its status as typing for user-friendliness
    async with message.channel.typing():
            
        # get members of history
        message_list = history[0]
        name_to_user = history[1]
        last_users   = history[2]
        
        # get gpt 3.5 response
        if use_chatgpt_model:
            rspns_text = get_chatgpt_response(message_list)
        # get gpt 3 response if deem inappropriate
        if not use_chatgpt_model or 'inappropriate' in rspns_text:
            rspns_text = get_gpt3_response(message_list)
        
        # sometimes response comes back blank - trying to print blank message to discord causes an exceptions
        if len(rspns_text) < 1:
            rspns_text = 'I am...speechless. '
    
        # clean up the raw response
        print('This is response: ', rspns_text)
        
        # remove starting whitespace
        rspns_text = rspns_text.strip()
        # remove repeating \n
        while '\n\n' in rspns_text:
            rspns_text=rspns_text.replace('\n\n','\n')
        
        # convert all the name to mentions
        record_mentions=[]
        for name in name_to_user:
            # # specify ping cases
            if len(name) > 5:
                ping_case1 = r'(?i)(?b)@(?:' + regex.escape(name) + r'){i<=1,d<=1,s<=1,e<=2}'
                ping_case2 = r'(?i)(?b)(?:'  + regex.escape(name) + r'){i<=0,d<=1,s<=1,e<=2}'
            else:
                ping_case1 = r'(?i)(?b)@(?:' + regex.escape(name) + r'){i<=0,d<=0,s<=0,e<=0}'
                ping_case2 = r'(?i)(?b)(?:'  + regex.escape(name) + r'){i<=0,d<=0,s<=0,e<=0}'
            check_case2 = True
            # # check ping case 1
            if regex.search(ping_case1, rspns_text):
                if name_to_user[name] in last_users:
                    rspns_text = regex.sub(ping_case1, name_to_user[name].mention, rspns_text)
                    record_mentions.append(name_to_user[name].mention)
                else:
                    rspns_text = regex.sub(ping_case1, name, rspns_text)
                check_case2 = False
            # # check ping case 2
            if check_case2 and regex.search(ping_case2, rspns_text):
                if name_to_user[name] in last_users:
                    rspns_text = regex.sub(ping_case2, name_to_user[name].mention, rspns_text)
                    record_mentions.append(name_to_user[name].mention)
                else:
                    rspns_text = regex.sub(ping_case2, name, rspns_text)
        
        # add an @author if it forgot
        if message.author.mention not in rspns_text:
            rspns_text = message.author.mention + rspns_text
            record_mentions.append(message.author.mention)
        
        # mentions related clean ups
        for mention in record_mentions:
            mention_case1 = r'(?i)(?b)(?:' + regex.escape(mention + mention) + r'){i<=1}'
            mention_case2 = mention + '\n'
            mention_case3 = r'(' + regex.escape(mention) + r')([^ ])'
            mention_case4 = mention + ':'
            # # remove repeating mentions
            while regex.search(mention_case1, rspns_text):
                rspns_text = regex.sub(mention_case1, mention, rspns_text)
            # # remove \n after mentions
            while mention_case2 in rspns_text:
                rspns_text = rspns_text.replace(mention_case2, mention)
            # # add space after mention
            rspns_text = regex.sub(mention_case3, r'\1 \2', rspns_text)
            # # remove everything after @<...>:
            rspns_text = rspns_text.split(mention_case4, 1)[0]
        
        # remove stray @ symbol
        rspns_text = regex.sub(r'([^<])(@)', r'\1', rspns_text)
        
        # convert <:emoji:> to emoji
        
        # # get a list of all server emojis
        name_to_emoji = {}
        emoji_case1 = r'<(?::){i<=1,d<=1,e<=1}([A-Za-z0-9_]+)(?::){i<=1,d<=1,e<=1}>'
        emoji_case2 = r'[^<]:([A-Za-z0-9_]+):[^>]'
        
        if regex.search(emoji_case1, rspns_text) or regex.search(emoji_case2, rspns_text):
            for emoji in message.guild.emojis:
                name_to_emoji[str(emoji.name)] = '<:' + str(emoji.name) + ':' + str(emoji.id) + '>'
        
        # # convert the emojis in rspns_text
        while regex.search(emoji_case1, rspns_text):
            # # # find in the rspns_text
            emoji_in_rspns = regex.search(emoji_case1, rspns_text).group(0)
            name_in_rspns = regex.search(emoji_case1, rspns_text).group(1)
            # # # match in name_to_emoji
            names_in_dict = get_close_matches(name_in_rspns, name_to_emoji.keys(), n=1, cutoff=0.5)
            if names_in_dict:
                name_in_dict = names_in_dict[0]
            else:
                continue
            emoji_in_dict = name_to_emoji[name_in_dict]
            # # # sub
            rspns_text = regex.sub(emoji_in_rspns, emoji_in_dict, rspns_text)
        while regex.search(emoji_case2, rspns_text):
            # # # find in the rspns_text
            emoji_in_rspns = regex.search(emoji_case2, rspns_text).group(0)
            name_in_rspns = regex.search(emoji_case2, rspns_text).group(1)
            # # # match in name_to_emoji
            names_in_dict = get_close_matches(name_in_rspns, name_to_emoji.keys(), n=1, cutoff=0.6)
            if names_in_dict:
                name_in_dict = names_in_dict[0]
            else:
                continue
            emoji_in_dict = name_to_emoji[name_in_dict]
            # # # sub
            rspns_text = regex.sub(emoji_in_rspns, emoji_in_dict, rspns_text)
            
    # send out word
    await message.channel.send(rspns_text)

# ASYNC FUNCTIONS
# #####################################



# get pid
with open('.pid', "w") as f:
    f.write(str(os.getpid()))
# start the bot
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.create_task(client.start(BotKey))
loop.run_forever()