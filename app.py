import requests
import json
import datetime
import time
import os
from flask import Flask, request

###GLOBAL VARIABLES TO SET###
#resource name from AAD
resourcename = os.getenv("RESOURCE")

#client name from AAD
clientid = os.getenv("CLIENTID")

#token endpoint from AAD
tokenendpoint = os.getenv("TOKEN_ENDPOINT")

#length of time in seconds before token expires to request a refresh
timebeforerefresh = os.getenv("REFRESH_TIME", 600) #default to 10 minutes

##### DO NOT EDIT BELOW THIS LINE #####

#port number on which to listen
portnumber = 5000

#dynamic object class to use for sending responses to the requester
class Expando(object):
    pass

#class to hold retrieved tokens in memory
class Token(object):
    def __init__(self, accesstoken=None, refreshtoken=None, expires_on=None, username=None, password=None):
        self.accesstoken = accesstoken
        self.refreshtoken = refreshtoken
        self.expires_on = expires_on
        self.username = username
        self.password = password

#create an empty list to hold retrieved tokens
tokens = []

#initialize the flask app
app = Flask(__name__)

#function to query azure ad for a token
def gettokenfromazure(action, userreq, refreshtoken):
    tokenpost={}
    if action=="new":
        #build a new token request
        tokenpost = {
            'client_id':clientid,
            'resource':resourcename,
            'username':userreq['username'],
            'password':userreq['password'],
            'grant_type':'password'
        }

    else:
        #build a refresh request
        tokenpost = {
            'client_id':clientid,
            'resource':resourcename,
            'refresh_token':refreshtoken,
            'grant_type':'refresh_token'
        }

    #make the token refresh request
    tokenres = requests.post(tokenendpoint, data=tokenpost)

    #extract the access token
    try:
        mytoken = Token()
        mytoken.accesstoken = tokenres.json()['access_token']
        mytoken.refreshtoken = tokenres.json()['refresh_token']
        mytoken.username = userreq['username']
        mytoken.password = userreq['password']
        mytoken.expires_on = tokenres.json()['expires_on']
        return mytoken
    except:
        try:
            #if we received an error message from the endpoint, handle it
            errorobj = Expando()
            errorobj.error = tokenres.json()['error']
            errorobj.description = tokenres.json()['error_description']
            return errorobj
        except:
            #for all other errors, return "unknon error"
            errorobj = Expando()
            errorobj.error = "error"
            errorobj.description = "unknown error"
            return errorobj

#function to parse the retrieved token and generate the response output for the requesting client
def generatetokenresponse(token, action):
    #generate an object to return the refreshed token to the requestor
    tokenobj = Expando()
    tokenobj.accesstoken = token.accesstoken
    tokenobj.expires_on = token.expires_on
    if action=="refresh":
        tokenobj.action = "refreshed existing token"
    if action=="existing":
        tokenobj.action = "returned existing token"
    if action=="new":
        tokenobj.action = "retrieved new token"
    if action=="expired":
        tokenobj.action = "retrieved new token to replace expired token"

    tokenresponse = json.dumps(tokenobj.__dict__)
    return tokenresponse

@app.route('/requesttoken',methods=['GET', 'POST'])
def requesttoken():
    #get the user request
    userreq = request.get_json(silent=True)

    #check if there's an existing token 
    existingtokens = list(filter(lambda x:x.username == userreq['username'] and x.password == userreq['password'], tokens))
    
    #if there is an existing token
    if len(existingtokens)>0:
        existingtoken = existingtokens[0]

        #if token has expired
        if(float(existingtoken.expires_on)<time.time()):
            #remove the existing token from the cache
            tokens.remove(existingtoken)

            #request a new token
            newtoken = gettokenfromazure("new", userreq, None)
            try:
                #generate an object to return the refreshed token to the requestor
                response = generatetokenresponse(newtoken, "expired")

                #cache the new token
                tokens.append(newtoken)

                return response
            except:
                #if the newtoken object doesn't have an accesstoken attribute, assume it's an error and return it
                response = json.dumps(newtoken.__dict__)
                return response

        #check difference between expiration time and current time
        #if it's less than the secondsbeforerefresh value, then refresh it
        if (float(existingtoken.expires_on)-time.time()) < float(timebeforerefresh):
            #create a refresh request
            refreshedtoken = gettokenfromazure("refresh", userreq, existingtoken.refreshtoken)
            try:
                #generate the client response. if we got an error talking to the endpoint, it will be handled as an exception
                response = generatetokenresponse(refreshedtoken, "refresh")

                #remove the old token
                tokens.remove(existingtoken)

                #cache the new token
                tokens.append(refreshedtoken)

                return response
            except:
                #if we're handling an error, just return whatever is in the retrieved token object, which should be an error message
                response = json.dumps(refreshedtoken.__dict__)
                return response
        else:
            #the cached token is still ok, so return it to the user
            response = generatetokenresponse(existingtoken, "existing")
            return response
    else:
        #no cached token, so need to request a new one
        newtoken = gettokenfromazure("new", userreq, None)
        try:
            #generate the client response. if we got an error talking to the endpoint, it will be handled as an exception
            response = generatetokenresponse(newtoken, "new")

            #cache the new token
            tokens.append(newtoken)

            return response
        except:
            #if we're handling an error, just return whatever is in the retrieved token object, which should be an error message
            response = json.dumps(newtoken.__dict__)
            return response

if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0',port=portnumber)