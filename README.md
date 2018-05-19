# azuread-oauth2-helper
A simple microservice for requesting and caching OAuth2 authorization tokens from Azure Active Directory

# About
This microservice abstracts the retrieval, caching and refreshing of OAuth2 access tokens from Azure Active Directory so that a client application only needs to supply a username and password to retrieve a valid access token.

Here is a sample request:

```
{
	"username":"lucasalexander@somed365org.onmicrosoft.com",
	"password":"XXXXXXXX"
}
```

And here is a corresponding sample response:
```
{
	"accesstoken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6ImlCakwxUmNxemhp...", 
	"expires_on": "1526704330", 
	"action": "returned existing token"
}
```

When a request containing a username and password arrives for the first time, the microservice retrieves an OAuth2 access token from Azure AD and returns it to the requester. The microservice also caches an object that contains the access token, refresh token, username, password and expiration time.

When subsequent requests arrive, the microservice checks its cache for an existing token that matches the username and password. If it finds one, it checks if the token has expired or needs to be refreshed.

If the existing token has expired, a new one is requested. If the token existing token has not expired, but will expire within a specified period of time (10 minutes is the default value), the microservice will execute a refresh request to Azure AD, cache the updated token and return it to the requester. If there's an unexpired existing token that doesn't need to be refreshed, the cached access token will be returned to the requester.

# Run with Docker
Pull the image from [Docker Hub](https://hub.docker.com):

    docker pull lucasalexander/azuread-oauth2-helper:latest

#### Required Environment variables
|Name | Value |
|-----|-------|
|RESOURCE  | The URL of the service that is going to be accessed |
|CLIENTID  | The Azure AD application client ID |
|TOKEN_ENDPOINT | The OAuth2 token endpoint from the Azure AD application |

Run the image with the following command (replacing the environment variables with your own)

    docker run -d -p 5000:5000 -e RESOURCE=https://XXXXXX.crm.dynamics.com -e CLIENTID=XXXXXX -e TOKEN_ENDPOINT=https://login.microsoftonline.com/XXXXXX/oauth2/token --name oauthhelper lucasalexander/azuread-oauth2-helper:latest


#### Optional Environment variables
|Name | Value | Default |
|-----|-------|---------|
|REFRESH_THRESHOLD  | The time remaining (in seconds) before a token's expiration time when it will be refreshed | 600 |

# Usage
Post a JSON object containing a username and password to the microservice's "/requesttoken" endpoint like so:

```
POST /requesttoken HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Cache-Control: no-cache

{
	"username":"lucasalexander@somed365org.onmicrosoft.com",
	"password":"XXXXXXXX"
}
```
Note: "application/json" must sent as the content-type header. 

If an access token is successfully retrieved, the microservice will return a JSON object containing the following attributes:
|Name | Description |
|-----|-------|
|accesstoken  | The token to use when accessing the resource  |
|expires_on  | Epoch time at which the token will expire  |
|action  | A text description of whether the token is newly retrieved, refreshed, cached or expired/re-retrieved  |

# A note on security
Because the microservice is caching usernames, passwords and access tokens in memory, this approach is vulnerable to heap inspection attacks, so you'll want to make sure your environment is appropriately locked down. Also you'll want to make sure all communication between your requesting clients and the microservice is encrypted.