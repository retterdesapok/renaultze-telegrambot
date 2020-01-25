#!/usr/bin/env python

# Third party library; "pip install requests" if getting import errors.
import requests

# We use JSON to parse tokens and our token file storage.
import json

# We read JWT tokens which are base64 encoded.
import base64

# We check the token expiry time.
import time

# Datebase access
from database_access import DatabaseAccess


class ZEServices(object):
    # API Gateway.
    servicesHost = 'https://www.services.renault-ze.com'

    # This prevents the requests module from creating its own user-agent.
    stealthyHeaders = {'User-Agent': None, 'DNT': '1'}

    def __init__(self, da, userid, user, password):
        # Generate the ZE Services token.
        self.userid = userid
        self.user = user
        self.password = password
        self.token = None
        self.dba = da

    def refreshTokenIfNecessary(self):
        user = self.dba.getUser(self.userid)

        if user != None:
            tokenString = user['tokenJson']
            try:
                tokenData = json.loads(tokenString)
                # We could be using python_jwt but even the official ZE Services ("decodeToken") does it this crude way, so why overcomplicate things?
                splitToken = tokenData['token'].split('.')
                # Check it looks semi-valid.
                if len(splitToken) != 3: raise ValueError('Not a well formed JWT token')
                # Get the JSON payload of the JWT token.
                b64payload = splitToken[1]
            except:
                print("Unexpected error getting token: " + tokenString)

            # Check the base64 padding.
            missing_padding = len(b64payload) % 4
            if missing_padding:
                b64payload += '=' * (4 - missing_padding)

            # Decode the base64 JWT token.
            jsonPayload = base64.b64decode(b64payload).decode("utf-8")

            # Parse it as JSON.
            tokenJson = json.loads(jsonPayload)

            # Is the token still valid? If not, refresh it.
            if (time.gmtime() > time.gmtime(tokenJson['exp'])):
                print("Token for user", self.userid, "was not valid. Logging in again.")
            else:
                print("Token for user", self.userid, "was still valid.")
                self.token = tokenData['token']

        # We have never cached an access token before.
        if self.token == None:
            print("Trying login for", self.userid, self.user)
            if self.password == None:
                self.password = user['password']

            url = ZEServices.servicesHost + '/api/user/login'
            payload = {'username': self.user, 'password': self.password}
            ses = requests.Session()
            api_json = ses.post(url, headers=ZEServices.stealthyHeaders, json=payload).json()
            print("Received answer from ZE Services")

            # We do not want to save all the user data returned on login, so we create a smaller file of just the mandatory information.
            tokenData = {'refreshToken': ses.cookies['refreshToken'], 'xsrfToken': api_json['xsrfToken'],
                         'token': api_json['token']}
            self.token = tokenData['token']

            if user == None:
                print("New user: Insert")
                vin = api_json['user']['associated_vehicles'][0]['VIN']

                # Save this refresh token and JWT token for future use so we are nicer to Renault's authentication server.
                self.dba.insertUser(self.userid, self.user, self.password, vin, json.dumps(tokenData))
            else:
                print("Old user: Update token")
                self.dba.updateToken(self.userid, json.dumps(tokenData))

        return self.token

    def apiCall(self, path):
        url = ZEServices.servicesHost + path
        headers = {'Authorization': 'Bearer ' + self.token, 'User-Agent': None}
        return requests.get(url, headers=headers).json()

    def postApiCall(self, path):
        url = ZEServices.servicesHost + path
        headers = {'Authorization': 'Bearer ' + self.token, 'User-Agent': None}
        return requests.post(url, headers=headers).json()
