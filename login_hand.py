


import requests
import re
import sys
import time

ALL_COOKIES={}

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

    response = requests.post(url,
            data={ 'request_type': 'RESPONSE', 'email': 'aze@chenot.me', 'password': 'eiGuTHa1kighoor'},
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



def getValues():
    if len(ALL_COOKIES) == 0:
        print("Login...")
        login()

    count=0
    while True:
        count += 1
        response = requests.get('https://comfort-online.com/',
                cookies=ALL_COOKIES,
                )
        if response.status_code != 200:
            sys.exit("Unable to get temp")

        temp_values={}
        for key in ['val_000_00442', 'val_000_00444', 'val_000_00445', 'val_000_00446']:
            # id="val_000_00446">36.2</span>
            pattern = re.compile('id="' + key + '">(\d+\.?\d*)</span')
            match = pattern.search(response.text)
            if match:
                temp_values[key]= match.group(1)
            else:
                sys.exit("No temp" + key)

        print(temp_values)

        if (count % 2

        time.sleep(2)


getValues()
