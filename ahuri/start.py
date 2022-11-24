"""
The MIT License (MIT)

Copyright (c) 2022-present SqdNoises

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import json
import asyncio
import argparse
import readline
import requests
import websockets
from . import (
    __title__,
    __display_version__,
    config
)
from .utils import *
from yarl import URL
from datetime import datetime

config.check()

# Create the parser
parser = argparse.ArgumentParser(
    prog = __title__,
    description = "Use Ahuri from the command line!",
    epilog = f"""subcommands:
  account  manage your account
  channel  create, get or delete channels
  config   view or edit config variables

Config file located at {config.config}""",
    allow_abbrev = False,
    formatter_class = argparse.RawDescriptionHelpFormatter
)
subparser = parser.add_subparsers(help="subcommands")

# Checking some config values
api_url = config.get("api_url")
if api_url == None:
    warn("No 'api_url' found in config file.")
elif api_url == "":
    warn("'api_url' not set in config. This may cause errors.")
else:
    api_url = URL(api_url)

token = config.get("user")
if token == None:
    warn("No 'user' found in config file. Please log in to fix this.")
else:
    token = token.get("token")
    if token == None:
        warn("Not logged in. This may cause errors.")
    elif type(token) != str:
        warn("Invalid token, Log in to fix this.")
    else:
        # Re-adding user details to config
        headers = {
            "Authorization": token
        }
        
        try:
            response = requests.get(
                api_url/"account",
                headers = headers
            )
        except:
            warn("Failed to fetch user details.")
        else:
            try:
                rjson = response.json()
            except ValueError:
                is_json = False
                has_message = False
            else:
                is_json = True
                if "message" in rjson:
                    has_message = True

            if response.status_code == 200:
                if is_json:
                    user_details = rjson["payload"]
                    config.set("user", user_details)
                else:
                    warn(f"Invalid response text received from {response.url} while fetching user details.")
            else:
                if has_message:
                    warn(f"Invalid status code returned while fetching user details. ({response.status_code})\n{response.status_code}: {rjson['message']}")
                else:
                    warn(f"Invalid status code returned while fetching user details. ({response.status_code})")

# websocket code for connecting to a channel
async def listen(
    token: str,
    id: str,
    api_url: URL,
    ws_url: str,
    time_format: str,
    verbose: bool = False
) -> None:
    """
    Websockets code for connecting to a channel

    Args:
        token (str): token of the user
        id (str): the channel id of the channel to connect to
        api_url (URL): api url
        ws_url (str): websocket url
        time_format (str): time format
        verbose (bool, optional): whether to show more output or not. Defaults to False.
    """
    last_message = ""

    headers = {
        "Authorization": token
    }

    if verbose:
        log(f"Sending GET request to API\nAPI URL: {api_url}")
    
    info(f"Getting channel from ID '{id}'")

    response = requests.get(
        api_url/"channel"/id,
        headers = headers
    )

    try:
        if verbose:
            log("Converting JSON response to python dictionary")
        rjson = response.json()
    except ValueError:
        if verbose:
            log("err: No JSON in response")
        is_json = False
        has_message = False
    else:
        is_json = True
        if "message" in rjson:
            has_message = True

    if verbose:
        if is_json:
            log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
        else:
            log(f"Response Text:\n{response.text}")

    if response.status_code == 200:
        if is_json:
            channel = rjson["payload"]
        else:
            channel_connect.error(f"Invalid response text received from {response.url}.")
    else:
        if has_message:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}")
            channel_connect.error(f"{response.status_code}: {rjson['message']}")
        else:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}\nResponse text: {response.text}")
            channel_connect.error(f"Status code {response.status_code} returned.")    
    if verbose:
        log(f"Establishing connection to websocket server at {ws_url}")
    info(f"Connecting to channel '{channel['name']}'")
    try:
        async with websockets.connect(ws_url) as ws:
            if verbose:
                log("Connection established!")
                log("Authorizing connection...")
            await ws.send(json.dumps({
                "command": "authorize",
                "arguments": {
                    "token": token
                }
            }))
            if verbose:
                log("Authorized connection!")
                log("Opening channel...")
            await ws.send(json.dumps({
                "command": "open channel",
                "arguments": {
                    "id": id
                }
            }))
            if verbose:
                log("Opened channel!")

            info("Success!")
            info(f"You are now connected to channel '{channel['name']}' owned by {channel['owner']['username']}.{channel['owner']['tag']}")
            while True:
                msg = await ws.recv()
                msgtime = datetime.now()
                time = datetime.strftime(msgtime, time_format)
                wsr = json.loads(msg)
                if verbose:
                    log(f"Message received from server: {msg}")
                    if "message" in wsr:
                        log(wsr["message"])

                if "payload" == None:
                    print()
                    if "message" in wsr:
                        winfo(f"Invalid websocket response returned. Message: {wsr['message']}")
                    else:
                        winfo(f"Invalid websocket response returned. Websocket response:\n{json.dumps(wsr, indent=2)}")
                    winfo("Exiting")
                    exit()

                message = wsr["payload"]
                sender = message["sender"]
                if last_message == sender["id"]:
                    print(f"{time} > {message['content']}")
                else:
                    print()
                    print(f"{message['sender']['username']}.{message['sender']['tag']} at {time}\n> {message['content']}")
                last_message = sender["id"]
    except KeyboardInterrupt:
        winfo("Keyboard Interrupt sent. Exiting")

# Add functions that run after subcommands are used
def mainfunc(args: argparse.Namespace) -> None:
    if args.version:
        print(__display_version__)
    else:
        parser.error("Specify a subcommand to run.")

def account_deletefunc(args: argparse.Namespace) -> None:
    """
    Function that executes when delete subcommand of account subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    sure_inp = input("Are you sure you want to delete your account?\nYour channels and messages will be entirely deleted.\nYou can not recover your account after deleting it.\n>> Yes/No: ").strip().lower()
    if sure_inp == "yes" or sure_inp == "y":
        pass
    elif sure_inp == "no" or sure_inp == "n":
        print("Operation Cancelled.")
        exit()
    else:
        print("Invalid input, cancelled.")
        exit()

    sure_inp2 = input("Double-Confirm: Are you sure you want to delete your account? (This action is irreversible!): ").strip().lower()
    if sure_inp2 == "yes" or sure_inp2 == "y":
        pass
    elif sure_inp2 == "no" or sure_inp2 == "n":
        print("Operation Cancelled.")
        exit()
    else:
        print("Invalid input, cancelled.")
        exit()

    api_url = config.get("api_url", verbose=args.verbose)
    if api_url == None:
        account_delete.error("No 'api_url' found in config file.")
    else:
        api_url = URL(api_url)
    
    token = config.get("user", verbose=args.verbose)
    if token == None:
        account_delete.error("No 'user' found in config file. Please log in to fix this.")
    else:
        token = token.get("token")
        if token == None:
            account_delete.error("Not logged in. Please log in.")
        elif type(token) != str:
            account_delete.error("Invalid token, Log in again to fix this.")
    
    headers = {
        "Authorization": token
    }

    if args.verbose:
        log(f"Sending DELETE request to API\nAPI URL: {api_url}")
    response = requests.delete(
        api_url/"account",
        headers = headers
    )

    try:
        if args.verbose:
            log("Converting JSON response to python dictionary")
        rjson = response.json()
    except ValueError:
        if args.verbose:
            log("err: No JSON in response")
        is_json = False
        has_message = False
    else:
        is_json = True
        if "message" in rjson:
            has_message = True

    if args.verbose:
        if is_json:
            log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
        else:
            log(f"Response Text:\n{response.text}")

    if response.status_code == 200:
        if is_json:
            user_details = rjson["payload"]
            config.set("user", {"token": None})
            print(f"Deleted your account!\n\nAccount Details\nUsername: {user_details['username']}.{user_details['tag']}\nID: {user_details['id']}\nEmail: {user_details['email']}\nCreated at: {user_details['createdAt']} UTC")
        else:
            account_delete.error(f"Invalid response text received from {response.url} while fetching user details.")
    else:
        if has_message:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}")
            account_delete.error(f"{response.status_code}: {rjson['message']}")
        else:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}\nResponse text: {response.text}")
            account_delete.error(f"Status code {response.status_code} returned.")

def account_infofunc(args: argparse.Namespace) -> None:
    """
    Function that executes when info subcommand of account subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    api_url = config.get("api_url", verbose=args.verbose)
    if api_url == None:
        account_info.error("No 'api_url' found in config file.")
    else:
        api_url = URL(api_url)
    
    token = config.get("user")
    if token == None:
        account_info.error("No 'user' found in config file. Please log in to fix this.")
    else:
        token = token.get("token")
        if token == None:
            account_info.error("Not logged in. Please log in.")
        elif type(token) != str:
            account_info.error("Invalid token, Log in to fix this.")
    
    headers = {
        "Authorization": token
    }

    if args.verbose:
        log(f"Sending GET request to API\nAPI URL: {api_url}")
    response = requests.get(
        api_url/"account",
        headers = headers
    )
    
    try:
        if args.verbose:
            log("Converting JSON response to python dictionary")
        rjson = response.json()
    except ValueError:
        if args.verbose:
            log("err: No JSON in response")
        is_json = False
        has_message = False
    else:
        is_json = True
        if "message" in rjson:
            has_message = True
    
    if args.verbose:
        if is_json:
            log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
        else:
            log(f"Response Text:\n{response.text}")
    if response.status_code == 200:
        if is_json:
            user_details = rjson["payload"]
            config.set("user", user_details, verbose=args.verbose)
            print(f"Account Details\nUsername: {user_details['username']}.{user_details['tag']}\nID: {user_details['id']}\nEmail: {user_details['email']}\nCreated at: {user_details['createdAt']} UTC")
        else:
            account_info.error(f"Invalid response text received from {response.url} while fetching user details.")
    else:
        if has_message:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}")
            account_info.error(f"{response.status_code}: {rjson['message']}")
        else:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}\nResponse text: {response.text}")
            account_info.error(f"Status code {response.status_code} returned.")

def account_loginfunc(args: argparse.Namespace) -> None:
    """
    Function that executes when login subcommand of account subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    email = args.email.strip()
    password = input(f"Enter password for {email}: ").strip()
    
    api_url = config.get("api_url", verbose=args.verbose)
    if api_url == None:
        account_login.error("No 'api_url' found in config file.")
    else:
        api_url = URL(api_url)
    
    data = {
        "email": email,
        "password": password
    }

    if args.verbose:
        log(f"Sending POST request to API\nAPI URL: {api_url}\nJSON Data: {json.dumps(data, indent=2)}")
    response = requests.post(
        api_url/"auth"/"login",
        json = data
    )

    try:
        if args.verbose:
            log("Converting JSON response to python dictionary")
        rjson = response.json()
    except ValueError:
        if args.verbose:
            log("err: No JSON in response")
        is_json = False
        has_message = False
    else:
        is_json = True
        if "message" in rjson:
            has_message = True
    
    if args.verbose:
        if is_json:
            log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
        else:
            log(f"Response Text:\n{response.text}")
    if response.status_code == 200:
        if is_json:
            user_details = rjson["payload"]
            config.set("user", user_details, verbose=args.verbose)
            print(f"Logged in as {user_details['username']}.{user_details['tag']} successfully!")
        else:
            account_login.error(f"Invalid response text received from {response.url}.")
    else:
        if has_message:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}")
            account_login.error(f"{response.status_code}: {rjson['message']}")
        else:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}\nResponse text: {response.text}")
            account_login.error(f"Status code {response.status_code} returned.")

def account_registerfunc(args: argparse.Namespace) -> None:
    """
    Function that executes when register subcommand of account subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    email = args.email.strip()
    username = input(f"Create a username for {email}: ").strip()
    password = input(f"Create a password for {username}: ").strip()
    confirm_password = input(f"Confirm your password: ").strip()

    if password == confirm_password:
        api_url = config.get("api_url", verbose=args.verbose)
        if api_url == None:
            account_register.error("No 'api_url' found in config file.")
        else:
            api_url = URL(api_url)
        
        data = {
            "email": email,
            "username": username,
            "password": password
        }

        if args.verbose:
            log(f"Sending POST request to API\nAPI URL: {api_url}\nJSON Data: {json.dumps(data, indent=2)}")
        response = requests.post(
            api_url/"auth"/"register",
            json = data
        )

        try:
            if args.verbose:
                log("Converting JSON response to python dictionary")
            rjson = response.json()
        except ValueError:
            if args.verbose:
                log("err: No JSON in response")
            is_json = False
            has_message = False
        else:
            is_json = True
            if "message" in rjson:
                has_message = True
        
        if args.verbose:
            if is_json:
                log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
            else:
                log(f"Response Text:\n{response.text}")

        if response.status_code == 201:
            if is_json:
                user_details = rjson["payload"]
                config.set("user", user_details, verbose=args.verbose)
                print(f"\nRegistered an account successfully!\nAccount Details\nEmail: {email}\nUsername: {user_details['username']}.{user_details['tag']}")
            else:
                account_register.error(f"Invalid response text received from {response.url}.")
        else:
            if has_message:
                print(f"An error occured! Request did not return status code 201.\nStatus code: {response.status_code}")
                account_register.error(f"{response.status_code}: {rjson['message']}")
            else:
                print(f"An error occured! Request did not return status code 201.\nStatus code: {response.status_code}\nResponse text: {response.text}")
                account_register.error(f"Status code {response.status_code} returned.")
    else:
        account_register.error("Passwords do not match.")

def channel_connectfunc(args: argparse.Namespace) -> None:
    """
    Function that executes when create subcommand of channel subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    id = args.id.strip()

    api_url = config.get("api_url", verbose=args.verbose)
    if api_url == None:
        channel_connect.error("No 'api_url' found in config file.")
    else:
        api_url = URL(api_url)
    
    ws_url = config.get("ws_url", verbose=args.verbose)
    if ws_url == None:
        channel_connect.error("No 'ws_url' found in config file.")
    elif type(ws_url) != str:
        channel_connect.error("Invalid format. Please reset config file to fix this.")

    time_format = config.get("time_format", verbose=args.verbose)
    if time_format == None:
        channel_connect.error("No 'time_format' found in config file.")
    elif type(time_format) != str:
        channel_connect.error("Invalid format. Please reset config file to fix this.")

    token = config.get("user", verbose=args.verbose)
    if token == None:
        channel_connect.error("No 'user' found in config file. Please log in to fix this.")
    else:
        token = token.get("token")
        if token == None:
            channel_connect.error("Not logged in. Please log in.")
        elif type(token) != str:
            channel_connect.error("Invalid token, Log in again to fix this.")

    try:
        asyncio.get_event_loop().run_until_complete(listen(token, id, api_url, ws_url, time_format, args.verbose))
    except KeyboardInterrupt:
        winfo("Keyboard Interrupt sent. Exiting")

def channel_createfunc(args: argparse.Namespace) -> None:
    """
    Function that executes when create subcommand of channel subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    name = args.name.strip()

    api_url = config.get("api_url", verbose=args.verbose)
    if api_url == None:
        channel_create.error("No 'api_url' found in config file.")
    else:
        api_url = URL(api_url)
    
    token = config.get("user", verbose=args.verbose)
    if token == None:
        channel_create.error("No 'user' found in config file. Please log in to fix this.")
    else:
        token = token.get("token")
        if token == None:
            channel_create.error("Not logged in. Please log in.")
        elif type(token) != str:
            channel_create.error("Invalid token, Log in again to fix this.")
    
    data = {
        "channelName": name
    }
    headers = {
        "Authorization": token
    }

    if args.verbose:
        log(f"Sending POST request to API\nAPI URL: {api_url}\nJSON Data: {json.dumps(data, indent=2)}")
    response = requests.post(
        api_url/"channel",
        json = data,
        headers = headers
    )

    try:
        if args.verbose:
            log("Converting JSON response to python dictionary")
        rjson = response.json()
    except ValueError:
        if args.verbose:
            log("err: No JSON in response")
        is_json = False
        has_message = False
    else:
        is_json = True
        if "message" in rjson:
            has_message = True

    if args.verbose:
        if is_json:
            log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
        else:
            log(f"Response Text:\n{response.text}")

    if response.status_code == 201:
        if is_json:
            channel = rjson["payload"]
            print(f"Created channel successfully!\n\nChannel Details\nName: {channel['name']}\nID: {channel['id']}")
        else:
            channel_create.error(f"Invalid response text received from {response.url}.")
    else:
        if has_message:
            print(f"An error occured! Request did not return status code 201.\nStatus code: {response.status_code}")
            channel_create.error(f"{response.status_code}: {rjson['message']}")
        else:
            print(f"An error occured! Request did not return status code 201.\nStatus code: {response.status_code}\nResponse text: {response.text}")
            channel_create.error(f"Status code {response.status_code} returned.")

def channel_deletefunc(args: argparse.Namespace) -> None:
    """
    Function that executes when delete subcommand of channel subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    sure_inp = input("Are you sure you want to delete the channel?\nYour messages will be entirely deleted.\nYou can not recover your messages after deleting the channel.\n>> Yes/No: ").strip().lower()
    if sure_inp == "yes" or sure_inp == "y":
        pass
    elif sure_inp == "no" or sure_inp == "n":
        print("Operation Cancelled.")
        exit()
    else:
        print("Invalid input, cancelled.")
        exit()

    id = args.id.strip()

    api_url = config.get("api_url", verbose=args.verbose)
    if api_url == None:
        channel_delete.error("No 'api_url' found in config file.")
    else:
        api_url = URL(api_url)
    
    token = config.get("user", verbose=args.verbose)
    if token == None:
        channel_delete.error("No 'user' found in config file. Please log in to fix this.")
    else:
        token = token.get("token")
        if token == None:
            channel_delete.error("Not logged in. Please log in.")
        elif type(token) != str:
            channel_delete.error("Invalid token, Log in again to fix this.")
    
    headers = {
        "Authorization": token
    }

    if args.verbose:
        log(f"Sending DELETE request to API\nAPI URL: {api_url}")
    response = requests.delete(
        api_url/"channel"/id,
        headers = headers
    )

    try:
        if args.verbose:
            log("Converting JSON response to python dictionary")
        rjson = response.json()
    except ValueError:
        if args.verbose:
            log("err: No JSON in response")
        is_json = False
        has_message = False
    else:
        is_json = True
        if "message" in rjson:
            has_message = True

    if args.verbose:
        if is_json:
            log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
        else:
            log(f"Response Text:\n{response.text}")

    if response.status_code == 200:
        if is_json:
            channel = rjson["payload"]
            print(f"Deleted channel cuccessfully!\n\nChannel Details\nName: {channel['name']}\nID: {channel['id']}\nCreated at: {channel['createdAt']} UTC\nOwner: {channel['owner']['username']}.{channel['owner']['tag']} ({channel['owner']['id']})")
        else:
            channel_delete.error(f"Invalid response text received from {response.url}.")
    else:
        if has_message:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}")
            channel_delete.error(f"{response.status_code}: {rjson['message']}")
        else:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}\nResponse text: {response.text}")
            channel_delete.error(f"Status code {response.status_code} returned.")

def channel_infofunc(args: argparse.Namespace) -> None:
    """
    Function that executes when get subcommand of channel subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    id = args.id.strip()

    api_url = config.get("api_url", verbose=args.verbose)
    if api_url == None:
        channel_info.error("No 'api_url' found in config file.")
    else:
        api_url = URL(api_url)
    
    token = config.get("user", verbose=args.verbose)
    if token == None:
        channel_info.error("No 'user' found in config file. Please log in to fix this.")
    else:
        token = token.get("token")
        if token == None:
            channel_info.error("Not logged in. Please log in.")
        elif type(token) != str:
            channel_info.error("Invalid token, Log in again to fix this.")
    
    headers = {
        "Authorization": token
    }

    if args.verbose:
        log(f"Sending GET request to API\nAPI URL: {api_url}")
    response = requests.get(
        api_url/"channel"/id,
        headers = headers
    )

    try:
        if args.verbose:
            log("Converting JSON response to python dictionary")
        rjson = response.json()
    except ValueError:
        if args.verbose:
            log("err: No JSON in response")
        is_json = False
        has_message = False
    else:
        is_json = True
        if "message" in rjson:
            has_message = True

    if args.verbose:
        if is_json:
            log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
        else:
            log(f"Response Text:\n{response.text}")

    if response.status_code == 200:
        if is_json:
            channel = rjson["payload"]
            print(f"Channel Details\nName: {channel['name']}\nID: {channel['id']}\nCreated at: {channel['createdAt']} UTC\nOwner: {channel['owner']['username']}.{channel['owner']['tag']} ({channel['owner']['id']})")
        else:
            channel_info.error(f"Invalid response text received from {response.url}.")
    else:
        if has_message:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}")
            channel_info.error(f"{response.status_code}: {rjson['message']}")
        else:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}\nResponse text: {response.text}")
            channel_info.error(f"Status code {response.status_code} returned.")

def channel_sendfunc(args: argparse.Namespace) -> None:
    """
    Function that executes when send subcommand of channel subcommand is used.

    Args:
        args (argparse.Namespace)
    """
    id = args.id.strip()
    content = args.message.strip()

    api_url = config.get("api_url", verbose=args.verbose)
    if api_url == None:
        channel_send.error("No 'api_url' found in config file.")
    else:
        api_url = URL(api_url)
    
    time_format = config.get("time_format")
    if time_format == None:
        channel_send.error("No 'time_format' found in config file.")
    elif type(time_format) != str:
        channel_send.error("Invalid format. Please reset config file to fix this.")
    
    token = config.get("user", verbose=args.verbose)
    if token == None:
        channel_send.error("No 'user' found in config file. Please log in to fix this.")
    else:
        token = token.get("token")
        if token == None:
            channel_send.error("Not logged in. Please log in.")
        elif type(token) != str:
            channel_send.error("Invalid token, Log in again to fix this.")
    
    data = {
        "content": content
    }
    headers = {
        "Authorization": token
    }

    if args.verbose:
        log(f"Sending POST request to API\nAPI URL: {api_url}\nJSON Data: {json.dumps(data, indent=2)}")
    info("Sending message")
    response = requests.post(
        api_url/"channel"/id/"send-message",
        json = data,
        headers = headers
    )
    msgtime = datetime.now()
    msgtime = msgtime.strftime(time_format)

    try:
        if args.verbose:
            log("Converting JSON response to python dictionary")
        rjson = response.json()
    except ValueError:
        if args.verbose:
            log("err: No JSON in response")
        is_json = False
        has_message = False
    else:
        is_json = True
        if "message" in rjson:
            has_message = True

    if args.verbose:
        if is_json:
            log(f"JSON Response:\n{json.dumps(rjson, indent=2)}")
        else:
            log(f"Response Text:\n{response.text}")

    if response.status_code == 200:
        if is_json:
            message = rjson["payload"]
            info("Sent!")
            print(f"Message preview:\n{message['sender']['username']}.{message['sender']['tag']} at {msgtime}\n> {message['content']}")
        else:
            channel_send.error(f"Invalid response text received from {response.url}.")
    else:
        if has_message:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}")
            channel_send.error(f"{response.status_code}: {rjson['message']}")
        else:
            print(f"An error occured! Request did not return status code 200.\nStatus code: {response.status_code}\nResponse text: {response.text}")
            channel_send.error(f"Status code {response.status_code} returned.")

def configfunc(args: argparse.Namespace) -> None:
    """
    Function that executes when config subcommmand is used.

    Args:
        args (argparse.Namespace)
    """
    if args.reset:
        config.reset(verbose=args.verbose)
    elif args.value == None:
        print(config.get(args.variable, verbose=args.verbose))
    else:
        config.set(args.variable, args.value, verbose=args.verbose)
        print(f"Successfully changed value of '{args.variable}' in the config file to '{args.value}'.")

# main command
parser.add_argument(
    "-V", "--version",
    action = "store_true",
    help = "display the version and exit"
)
parser.set_defaults(func=mainfunc)

# account subcommand
account = subparser.add_parser(
    "account",
    prog = "account",
    description = "manage your account",
    epilog = """subcommands:
  delete    delete your account
  info      get info on your account
  login     login to an account
  register  register an account
""",
    allow_abbrev = False,
    formatter_class = argparse.RawDescriptionHelpFormatter
)
account_subparser = account.add_subparsers(help="subcommands")

# delete subcommmand of account subcommand
account_delete = account_subparser.add_parser(
    "delete",
    prog = "delete",
    description = "delete your account",
    allow_abbrev = False
)
account_delete.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
account_delete.set_defaults(func=account_deletefunc)

# info subcommmand of account subcommand
account_info = account_subparser.add_parser(
    "info",
    prog = "info",
    description = "get info on your account",
    allow_abbrev = False
)
account_info.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
account_info.set_defaults(func=account_infofunc)

# login subcommand of account subcommand
account_login = account_subparser.add_parser(
    "login",
    prog = "login",
    description = "login to an account",
    allow_abbrev = False
)
account_login.add_argument(
    "email",
    action = "store",
    type = str,
    help = "email to login with"
)
account_login.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
account_login.set_defaults(func=account_loginfunc)

# register subcommand of account subcommand
account_register = account_subparser.add_parser(
    "register",
    prog = "register",
    description = "register an account",
    allow_abbrev = False
)
account_register.add_argument(
    "email",
    action = "store",
    type = str,
    help = "email to login with"
)
account_register.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
account_register.set_defaults(func=account_registerfunc)

# channel subcommand
channel = subparser.add_parser(
    "channel",
    prog = "channel",
    description = "create, get or delete channels",
    epilog = """subcommands:
  connect  connect to a channel
  create   create channels
  delete   delete channels
  info     get info about channels
  send     send a message to a channel
""",
    allow_abbrev = False,
    formatter_class = argparse.RawDescriptionHelpFormatter
)
channel_subparser = channel.add_subparsers(help="subcommands")

# connect subcommmand of channel subcommand
channel_connect = channel_subparser.add_parser(
    "connect",
    prog = "connect",
    description = "connect to a channel",
    allow_abbrev = False
)
channel_connect.add_argument(
    "id",
    action = "store",
    type = str,
    help = "id of channel"
)
channel_connect.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
channel_connect.set_defaults(func=channel_connectfunc)

# create subcommmand of channel subcommand
channel_create = channel_subparser.add_parser(
    "create",
    prog = "create",
    description = "create channels",
    allow_abbrev = False
)
channel_create.add_argument(
    "name",
    action = "store",
    type = str,
    help = "name of the channel to be created"
)
channel_create.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
channel_create.set_defaults(func=channel_createfunc)

# delete subcommmand of channel subcommand
channel_delete = channel_subparser.add_parser(
    "delete",
    prog = "delete",
    description = "delete info about channels",
    allow_abbrev = False
)
channel_delete.add_argument(
    "id",
    action = "store",
    type = str,
    help = "id of channel to delete"
)
channel_delete.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
channel_delete.set_defaults(func=channel_deletefunc)

# info subcommmand of channel subcommand
channel_info = channel_subparser.add_parser(
    "info",
    prog = "info",
    description = "get info about channels",
    allow_abbrev = False
)
channel_info.add_argument(
    "id",
    action = "store",
    type = str,
    help = "id of channel to get info about"
)
channel_info.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
channel_info.set_defaults(func=channel_infofunc)

# send subcommmand of channel subcommand
channel_send = channel_subparser.add_parser(
    "send",
    prog = "send",
    description = "send messages to channel",
    allow_abbrev = False
)
channel_send.add_argument(
    "id",
    action = "store",
    type = str,
    help = "id of channel to send message to"
)
channel_send.add_argument(
    "-m", "--message",
    action = "store",
    type = str,
    help = "message to send"
)
channel_send.add_argument(
    "-v", "--verbose",
    action = "store_true",
    help = "show more output"
)
channel_send.set_defaults(func=channel_sendfunc)

# config subcommand
_config = subparser.add_parser(
    "config",
    prog = "config",
    description = "view or edit config variables",
    allow_abbrev = False,
    epilog = "(you might want to specify any variable name while resetting the config, for example: `ahuri config a -r`)"
)
_config.add_argument(
    "variable",
    action = "store",
    type = str,
    help = "variable to view or edit"
)
_config.add_argument(
    "-v", "--value",
    action = "store",
    type = str,
    required = False,
    help = "value to change variable to"
)
_config.add_argument(
    "-V", "--verbose",
    action = "store_true",
    help = "show more output"
)
_config.add_argument(
    "-r", "--reset",
    action = "store_true",
    help = "reset config"
)
_config.set_defaults(func=configfunc)

# parse the arguments
def main(args=None):
    if args == None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)
    if "func" in dir(args):
        args.func(args)
    else:
        parser.error("No default function for this command.")