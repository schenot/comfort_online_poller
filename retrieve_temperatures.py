#!/usr/bin/python3


import fcntl
import os
import re
import requests
import sys
import time
import datetime
import json

ALL_COOKIES={}

def lock_script(label="default"):
    file = "/tmp/instance_" + label + ".lock"

    if not os.path.exists(file):
        create_file_handle = open(file, "w")
        create_file_handle.close()

    lock_file_pointer = os.open(file, os.O_WRONLY)
    try:
        fcntl.lockf(lock_file_pointer, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        sys.exit("Script is already running")


def add_secret(data):
    # expect somethinkg like
    #    {
    #        "email": "...",
    #        "password": "..."
    #    } 
    file_path= os.path.dirname(__file__) + '/login.secret.json'
    file_handle = open(file_path)
    secrets = json.load(file_handle)
    data.update(secrets)
    file_handle.close()

def concat_cookies(response):
    for cookie in response.cookies:
        ALL_COOKIES[cookie.name] = cookie.value


def login():
    response = requests.get('https://comfort-online.com/',
             allow_redirects=False )

    if response.status_code != 302:
        sys.exit("Unable to get comfort")

    # redirection url with GET parameters, expect something like: https://kwblogin.b2clogin.com/kwblogin.onmicrosoft.com/b2c_1_signinup/oauth2/v2.0/authorize?client_id=...
    url = response.headers['Location']

    # with requests.Session cookies seems to be lost between domains (SameSite param ingnored?)
    concat_cookies(response)

    response = requests.get(url, cookies=ALL_COOKIES)
    if response.status_code != 200:
        sys.exit("Unable to get 2")

    # get CSRF token and "StateProperties"
    pattern = re.compile('.*"csrf":"([^"]+)".*"transId":"([^"]+)".*')

    # add all cookies
    concat_cookies(response)

    csrf=''
    trans_id=''
    match = pattern.search(response.text)
    if match:
        csrf = match.group(1)
        trans_id = match.group(2)
    else:
        sys.exit("No CSRF / transId")

    #print("CSRF: " + csrf)
    #print("transId: " + trans_id)

    headers = {'X-CSRF-TOKEN':  csrf}

    url = 'https://kwblogin.b2clogin.com/kwblogin.onmicrosoft.com/B2C_1_signinup/SelfAsserted?tx=' + trans_id + '&p=B2C_1_signinup'

    data={'request_type': 'RESPONSE'}
    add_secret(data)

    response = requests.post(url,
            data=data,
            headers=headers,
            cookies=ALL_COOKIES,
            )
    if response.status_code != 200:
        sys.exit("Unable to post login")

    # add all cookies
    concat_cookies(response)

    url = 'https://kwblogin.b2clogin.com/kwblogin.onmicrosoft.com/B2C_1_signinup/api/CombinedSigninAndSignup/confirmed?rememberMe=false&csrf_token=' + csrf + '=&tx=' + trans_id

    response = requests.get(url,
            headers=headers,
            cookies=ALL_COOKIES,
            )

    if response.status_code != 200:
        sys.exit("Unable to get login value")

    login_values={}
    for key in ['state', 'id_token', 'code']:
        # id='id_token' value='eyJh...rpw'/>
        pattern = re.compile("id='" + key + "' value='([^']+)'/>")
        match = pattern.search(response.text)
        if match:
            login_values[key]= match.group(1)
        else:
            sys.exit("No " + key)

    response = requests.post('https://comfort-online.com/',
            data=login_values,
            cookies=ALL_COOKIES,
            allow_redirects=False,
            )

    #print(response)
    if response.status_code != 302:
        sys.exit("Unable to post on comfort")

    # add all cookies
    concat_cookies(response)

    print("Logged in")


# for test purpose
def logout():
    print("Logout")
    response = requests.post('https://comfort-online.com/fr/Account/LogOff',
            cookies=ALL_COOKIES
            )
    print(response)
    response = requests.post('https://comfort-online.com/Account/Signout',
        cookies=ALL_COOKIES
        )
    print(response)



def write_temperatures(values):
    today = datetime.datetime.today()
    file_path = os.path.dirname(__file__) + '/temp_' + str(today.isocalendar()[1]) + '.csv'

    file_handle = open(file_path, "a")

    line = str(int(time.time()))
    for value in values:
        line += ', ' + str(value)

    print(line)

    file_handle.write(line + "\n")
    file_handle.close()

def get_values():
    if len(ALL_COOKIES) == 0:
        print("Login...")
        login()

    count=0
    re_login=0
    while True:
        count += 1

        if re_login > 2:
            sys.exit("Can't retrieve temp despite relogin")

        response = requests.get('https://comfort-online.com/',
                cookies=ALL_COOKIES,
                )
        if response.status_code != 200:
            sys.exit("Unable to get tank temp")

        all_text = response.text

        response = requests.get('https://comfort-online.com/fr/Measurand/Values?plant=AZE-11913&name=CC%201.1%20radiateurs%20maison-1_2',
                cookies=ALL_COOKIES,
                )
        if response.status_code != 200:
            sys.exit("Unable to get ext temp")

        all_text += response.text

        print(all_text)

        all_values=[]
        for key in ['val_002_00334', 'val_000_00442', 'val_000_00444', 'val_000_00445', 'val_000_00446']:
            # id="val_000_00446">36.2</span>
            pattern = re.compile('id="' + key + '">(\d+[,\.]?\d*)</span')
            match = pattern.search(all_text)
            if match:
                # some temp avec "," as separator, some other avec "."
                value = match.group(1)
                value = value.replace(',', '.')
                all_values.append(float(value))
            else:
                print("No temp" + key + " re login")
                break
        else:
            re_login=0

            tank_values = all_values[1:5] 

            avg = sum(tank_values) / len(tank_values) 
            all_values.append(avg)

            write_temperatures(all_values)

            # to test reconnection
            #if count % 7 == 0:
            #    logout()

            time.sleep(60)
            continue


        login()
        re_login += 1

lock_script(label = 'retrieve_temperatures.py')
get_values()
