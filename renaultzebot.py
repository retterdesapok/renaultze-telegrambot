# -*- coding: utf8 -*-
import json

import requests
import telegram
from telegram.ext import *
from renault_api import ZEServices
from database_access import DatabaseAccess

def start(update, context):
    update.message.reply_text('Hallo!\nUm Statusmeldungen zu erhalten, wird dein ZE-Services-Nutzername '
                              'sowie dein Passwort benötigt. Das Passwort wird auf dem Server dieses Bots gespeichert da die Renault-ZE-API leider regelmäßig neue Logins benötigt. '
                              'Deine Nutzerdaten sind prinzipiell für Dritte einsehbar:\n'
                              '* Mich (@retterdesapok)\n'
                              '* Die Betreiber von Telegram\n'
                              '* Jeden, der meinen Server hackt.\n\n'
                              'Ich betreibe diesen Dienst privat und er befindet sich in der Beta-Phase, '
                              'mit Fehlern, Ausfällen und nicht perfekter Sicherheit ist also zu rechnen. Ich übernehme keine Verantwortung dafür, wenn dein Auto eines Tages weg ist.\n'
                              'Wenn du dem zustimmst und den Bot nutzen möchtest, sende die Daten wie folgt:\n'
                              '/register max.musterman@example.com meinrenaultzepasswort')


def status(update, context):
    chat_id = update.message.chat_id
    da = DatabaseAccess()
    user = da.getUser(chat_id)
    chat_id = user['userid']
    zes = ZEServices(da, chat_id, user['username'], None)
    token = zes.refreshTokenIfNecessary()
    if token is not None:
        newBatteryStatus = zes.apiCall('/api/vehicle/' + user['vin'] + '/battery')
        result = getStatusString(newBatteryStatus)
        context.bot.sendMessage(chat_id, result)
        da.updateApiResultForUser(chat_id, json.dumps(newBatteryStatus))
    else:
        context.bot.sendMessage(chat_id,
                                "Could not connect to ZE Services, you have been logged out. Register again to continue receiving updates.")
        da.deleteUser(chat_id)

def register(update, context):
    da = DatabaseAccess()

    chat_id = update.message.chat_id
    print("Registering Chat ID", chat_id)

    da.deleteUser(chat_id)

    username = context.args[0]
    password = context.args[1]

    zes = ZEServices(da, chat_id, username, password)
    token = zes.refreshTokenIfNecessary()
    if token is not None:
        update.message.reply_text("Login successful!")
    else:
        update.message.reply_text("Login was not successful :(")
        da.deleteUser(chat_id)


def unregister(update, context):
    chat_id = update.message.chat_id
    bot.sendMessage(chat_id, "Your data has been deleted")
    da = DatabaseAccess()
    da.deleteUser(chat_id)

def precondition(update, context):
    chat_id = update.message.chat_id
    da = DatabaseAccess()
    user = da.getUser(chat_id)
    chat_id = user['userid']
    zes = ZEServices(da, chat_id, user['username'], None)
    token = zes.refreshTokenIfNecessary()
    if token is not None:
        newBatteryStatus = zes.postApiCall('/api/vehicle/' + user['vin'] + '/air-conditioning')
        context.bot.sendMessage(chat_id, "Attempted to preheat.")
    else:
        context.bot.sendMessage(chat_id, "Could not connect to ZE Services, you have been logged out. Register again to continue receiving updates.")
        da.deleteUser(chat_id)

def sendUpdates(context):
    da = DatabaseAccess()
    users = da.getUsers()
    for user in users:
        chat_id = user['userid']
        zes = ZEServices(da, chat_id, user['username'], None)
        token = zes.refreshTokenIfNecessary()
        if token != None:
            newBatteryStatus = zes.apiCall('/api/vehicle/' + user['vin'] + '/battery')
            oldBatteryStatusString = user['lastApiResult']
            oldBatteryStatus = json.loads(oldBatteryStatusString) if oldBatteryStatusString != None else {}

            result = getStatusString(newBatteryStatus)
            if result != getStatusString(oldBatteryStatus):
                context.bot.sendMessage(chat_id, result)
                da.updateApiResultForUser(chat_id, json.dumps(newBatteryStatus))
        else:
            context.bot.sendMessage(chat_id,
                                    "Could not connect to ZE Services, you have been logged out. Register again to continue receiving updates.")
            da.deleteUser(chat_id)


def getStatusString(status):
    plugged = status['plugged'] if 'plugged' in status else False
    charge_level = status['charge_level'] if 'charge_level' in status else 0
    charging = status['charging'] if 'charging' in status else False
    remaining_time = status['remaining_time'] if 'remaining_time' in status else 0
    remaining_range = int(status['remaining_range']) if 'remaining_range' in status else 0

    if charge_level == 100:
        return "🔋 100% - Ladung beendet (" + str(remaining_range) + " km)"
    else:
        if charging:
            emissionsStr = getEmissionsString()
            return "⚡ " + str(charge_level) + "% (⏳ " + str(remaining_time) + " min, 💨 " + emissionsStr + ")"
        elif plugged:
            return "❎ " + str(charge_level) + "% Ladung abgebrochen"
        else:
            return "🔋 " + str(charge_level) + "% (" + str(remaining_range) + " km)"

    return ""

def emissions(update, context):
    context.bot.send_chat_action(chat_id=update.message.chat_id,
                                 action=telegram.ChatAction.TYPING)
    emissionsStr = getEmissionsString()
    chat_id = update.message.chat_id
    context.bot.sendMessage(chat_id, "💨 " + emissionsStr)

def dump(update, context):
    print("Database content:")
    da = DatabaseAccess()
    da.dumpUsersTable()
    print("---")

def getEmissionsString():
    with open('tokens.json') as f:
        d = json.load(f)
        url = "https://api.co2signal.com/v1/latest?countryCode=DE"
        headers = {'auth-token': d['co2signal'], 'User-Agent': None}
        emissionsApiResult = requests.get(url, headers=headers).json()
        return str(round(emissionsApiResult['data']['carbonIntensity'])) + ' ' + emissionsApiResult['units']['carbonIntensity']
    return "Keine Emissionsdaten verfügbar"

def main():
    with open('tokens.json') as f:
        d = json.load(f)
        updater = Updater(d['telegram'], use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start, pass_chat_data=True))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("unregister", unregister, pass_chat_data=True))
    dp.add_handler(CommandHandler("register", register, pass_chat_data=True))
    dp.add_handler(CommandHandler("status", status, pass_chat_data=True))
    dp.add_handler(CommandHandler("precondition", precondition, pass_chat_data=True))
    dp.add_handler(CommandHandler("dump", dump, pass_chat_data=True))
    dp.add_handler(CommandHandler("emissions", emissions, pass_chat_data=True))


    # Start the Bot
    updater.start_polling()

    # Start scheduled work
    queue = JobQueue()
    queue.set_dispatcher(dp)
    queue.start()
    new_job = queue.run_repeating(sendUpdates, interval=600, first=0, context=updater.bot)

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
