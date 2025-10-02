import telebot
from telebot.util import is_command
from telebot.util import generate_random_token
from telebot.util import extract_command
from telebot.util import extract_arguments

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

API_TOKEN = "6525810649:AAG6l3P_51yNvDsAUwkFaJIVi0_UPEtBLLo"

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://eskigemetgamebot-default-rtdb.firebaseio.com/'
})

# Get a database reference to our user
ref = db.reference('game')
users_ref = ref.child('users')



bot = telebot.TeleBot(API_TOKEN)

class Player:
    def __init__(self, chatid,secretnumber,gameid,gameturn):
        self.chatId = chatid
        self.secretNumber = secretnumber
        self.gameId = gameid
        self.GameTurn = gameturn
    def to_dict(self):
        return{
            'chatID' : self.chatId,
            'secretNumber' : self.secretNumber,
            'gameID' : self.gameId,
            'gameTurn' : self.GameTurn
        }

#@bot.message_handler(commands=['start','quit'])
def send_welcome(message):
    msg = bot.send_message(message.chat.id, """\
Hi there, I am Game bot.
What's your secret number?
""")
    bot.register_next_step_handler(msg, process_secret_step)

def process_secret_step(message):
    try:
        chat_id = message.chat.id
        secretNum = message.text
        if not secretNum.isdigit():
            msg = bot.reply_to(message, 'Secret number should be a number. Write again')
            bot.register_next_step_handler(msg, process_secret_step)
            return
        if not isValid(secretNum):
            msg = bot.reply_to(message, 'Something wrong. write secret number again?')
            bot.register_next_step_handler(msg, process_secret_step)
            return
        gameID = generate_random_token()

        gameIdLink = "https://t.me/YidnekGameBot?start="+gameID
        # 2 means your turn 3 = oponenet turn, 0 game not started, 1 means started
        player = Player(chat_id,secretNum,gameID,1)
        bot.send_message(chat_id, "Share the below link to your friend to start")
        #save to firebase
        firebaseID = str(player.chatId)
        users_ref.child(firebaseID).set(player.to_dict())

        gamecontroler = bot.send_message(chat_id, gameIdLink + "\nHey Lets play guess a number game with me. click the link to join")
        bot.register_next_step_handler(gamecontroler, game)

    except Exception as e:
        bot.reply_to(message, 'Sorry Something wrong !!')


def join_game(message):
    try:
       # gameid = message.text.split()[1]  it is optional
        gameid = extract_arguments(message.text)
        query = users_ref.order_by_child("gameID").equal_to(gameid).get()
        # print(query)
        for key, value in query.items():
            gamecreator = Player(value['chatID'],value['secretNumber'],value['gameID'],value['gameTurn'])
        if((gameid == gamecreator.gameId) & (gamecreator.GameTurn == 1)):
            bot.send_message(message.chat.id, "Game Joined")
            msg = bot.send_message(message.chat.id, "Please write your secret number")
            bot.register_next_step_handler(msg, process_secret2_step, gameid,value['chatID'])
    except Exception as e:
        bot.send_message(message.chat.id, "Something went wrong try again")

def process_secret2_step(message,gameid,chtID):
    try:
        chat_id = message.chat.id
        secretNum2 = message.text
        joinedgameID = gameid
        creatorId = chtID
        if not secretNum2.isdigit():
            msg = bot.reply_to(message, 'Secret number must be a number. write again?')
            bot.register_next_step_handler(msg, process_secret2_step)
            return
        if not isValid(secretNum2):
            msg = bot.reply_to(message, 'Something wrong. write secret number again?')
            bot.register_next_step_handler(msg, process_secret2_step)
            return
        joinedPlayer = Player(chat_id,secretNum2,joinedgameID,3)
        firebaseID = str(joinedPlayer.chatId)
        users_ref.child(firebaseID).set(joinedPlayer.to_dict())
        bot.send_message(creatorId,"***Oponnent Player Joined***")
        #update data
        update_ref = users_ref.child(str(creatorId))
        update_ref.update({"gameTurn": 2})
        bot.send_message(creatorId,"Your Turn now")
        bot.send_message(chat_id,"***GAME STARTED***")
        bot.send_message(chat_id,"Oponnent Turn Now")
    except Exception as e:
        bot.send_message(message.chat.id, "Something went wrong try again")


@bot.message_handler(func=lambda message: True)
def game(message):
    print(extract_command(message.text))
    if(is_command(message.text)):
        cmd = extract_command(message.text)
        #join game
        if(extract_arguments(message.text)):
            join_game(message)
            return
        if(cmd == 'quit'):
            quit_game(message)
            return
        if(cmd == 'start'):
            send_welcome(message)
            return
        if(cmd == 'gamerule'):
            how_to_play(message)
            return

    chat_id = message.chat.id
    gueessednumber = message.text
    try:
        query = users_ref.order_by_child("chatID").equal_to(chat_id).get()
        print(query)
        for key, value in query.items():
            gamedata = Player(value['chatID'],value['secretNumber'],value['gameID'],value['gameTurn'])
        gameTurn = gamedata.GameTurn
        gameid = gamedata.gameId
    except Exception as e:
        msg = bot.send_message(chat_id,"No Game ID")
        return
        #bot.register_next_step_handler(msg, game)

    print(gameTurn)
    if(checkGameTurn(gameTurn)==True):
        if not gueessednumber.isdigit():
            msg = bot.reply_to(message, 'Only number should try. write again?')
            bot.register_next_step_handler(msg, game)
            return
        if not isValid(gueessednumber):
            msg = bot.reply_to(message, 'Something wrong. write proper number again?')
            bot.register_next_step_handler(msg, game)
            return

 ### and chat id differ to this user
        querytochange = users_ref.order_by_child("gameID").equal_to(gameid).get()
        for key, value in querytochange.items():
            if(value['chatID'] != chat_id ):
                # change another player turn 2
                changedPlayer = Player(value['chatID'],value['secretNumber'],value['gameID'],value['gameTurn'])
            # call guess_compare function
                result = guess_compare(gueessednumber,changedPlayer.secretNumber)
                count,position = result
                bot.send_message(chat_id,"Number of Digit you got: "+str(count)+"\n"+
                                 "In Postion : "+ str(position))
            #Check winner
                if(count == 4 & position == 4):
                    bot.send_message(chat_id,"****YOU WIN****")
                    bot.send_message(changedPlayer.chatId,"#YOU LOST#")
                    quit_game(message)
                    return

                update_ref = users_ref.child(str(changedPlayer.chatId))
                update_ref.update({"gameTurn": 2})
            if(value['chatID'] == chat_id ):
                # change this player turn
                changeThisTurn = Player(value['chatID'],value['secretNumber'],value['gameID'],value['gameTurn'])
                update_ref = users_ref.child(str(changeThisTurn.chatId))
                update_ref.update({"gameTurn": 3})
        bot.send_message(changedPlayer.chatId,"Your Turn now")
        bot.register_next_step_handler(msg, game)
    else:
        print(checkGameTurn(gameTurn))
        bot.send_message(chat_id,checkGameTurn(gameTurn))
        #bot.register_next_step_handler(mess, game)

#@bot.message_handler(command=['quit'])
def quit_game(message):
    chat_id = message.chat.id
    try:
        query = users_ref.order_by_child("chatID").equal_to(chat_id).get()
        for key, value in query.items():
            quitgamedata = Player(value['chatID'],value['secretNumber'],value['gameID'],value['gameTurn'])
        quitgameid = quitgamedata.gameId
        querytoquit = users_ref.order_by_child("gameID").equal_to(quitgameid).get()
        for key, value in querytoquit.items():
            update_ref = users_ref.child(str(key))
            update_ref.update({"gameTurn": 0})
            bot.send_message(key, "Game Exited")
    except Exception as e:
        bot.send_message(chat_id,"can not quit game")
        return

def guess_compare(guessNum , secNum):
    count = 0
    position = 0
    index = 0
    for i in range(len(guessNum)):
        if guessNum[index] == secNum[index]:
            position +=1
        index += 1
        for j in range(len(secNum)):
            if guessNum[i] == secNum[j]:
                count +=1
    return count,position
   # print("count : " + str(count))
   # print("position : " + str(position))

def how_to_play(message):
    bot.send_message(message.chat.id, "How to Play")
    bot.send_message(message.chat.id, """\
click start menu .
1.Write Four different Digit Secret number.
2.share the link to your friend.
3.Your oponent also did 4 digit secret number.
4.Then try to get your oponent secret number by guessing.
The bot send you your guess result by giving number of digit you get and postion
Enjoy The Game
""")



def checkGameTurn(status):
    if status == 0:
        return "Game not Started"
    elif status == 1:
        return "Game Started, Please wait your opponent to join"
    elif status == 2:
        return  True
    elif status == 3:
        return  "Oponent Turn Please wait"
    else :
        return  "Game not known"




def isValid(input):
    if(int(input) < 0):
        return False
    if(len(str(input))!=4):
        return False
    inputstr = str(input)
    for i in range(len(inputstr)):
        for j in range(len(inputstr)):
            #check duplicate digit
            if ((inputstr[i] == inputstr[j]) & (i != j)):
                return False
    return True

# Enable saving next step handlers to file "./.handlers-saves/step.save".
# Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
# saving will hapen after delay 2 seconds.
bot.enable_save_next_step_handlers(delay=2)

# Load next_step_handlers from save file (default "./.handlers-saves/step.save")
# WARNING It will work only if enable_save_next_step_handlers was called!
bot.load_next_step_handlers()

bot.infinity_polling()