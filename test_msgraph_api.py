#!/usr/bin/env python3
import requests
import json
import base64
from msal import PublicClientApplication, ConfidentialClientApplication


def print_verbose(*args):
    # TODO: add -v flag and only print if it is set
    print(*args)


site_url = "https://icfveenendaal.sharepoint.com/sites/Opnames"
file_name = "/Users/adriaan/Downloads/R_20230409-110402.mp3"

user_emails = ["adriaanzonn@gmail.com"]
role = "write"
client_id = "6ea23538-cef7-441a-b435-49022ae4e936"
tenant_id = "7a0f3af3-97d5-486f-90a5-762b6f27d213"
client_secret = "0I88Q~2-m-J8TUb39yX6Aor3qeY5NlVN3nFbnbkP"
authority = f"https://login.microsoftonline.com/{tenant_id}"
scope = ["https://graph.microsoft.com/.default"]

app = ConfidentialClientApplication(client_id=client_id, client_credential=client_secret, authority=authority)

print_verbose("trying to acquire token from memory")
result = app.acquire_token_silent(scope, account=None)

if not result:
    print_verbose("acquiring new token")
    result = app.acquire_token_for_client(scope)

if "access_token" in result:
    pass  # upload...
else:
    print("Error trying to authenticate")
    print_verbose(result)
    exit(1)

print_verbose(result)

access_token = result["access_token"]

# Create the SharePoint file endpoint
file_endpoint = f"{site_url}/_api/web/getfolderbyserverrelativeurl('/Gedeelde%20documenten')/files/add(url='R_20230409-110402.mp3',overwrite=true)"

print_verbose("reading file")
# Read the file contents and encode them as base64
with open(file_name, "rb") as file:
    file_contents = file.read()

print_verbose("encoding file")
file_contents_b64 = base64.b64encode(file_contents).decode("utf-8")

print_verbose("uploading encoded file")

# TODO: zelf de microsoft graph api documentatie lezen en op basis daarvan de
# upload doen. Ik heb nu blindelings vertrouwd op chatgpt en dan is het niet
# heel gek dat ik het niet aan de praat krijg.


response = requests.get(
    url=f"{site_url}/_api/web/lists/getbytitle('/')/items?$select=FileLeafRef",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
)


print(response)
print_verbose(response.text)



# Upload the file to SharePoint.
#response = requests.post(
#    url=file_endpoint,
#    headers={
#        "Authorization": f"Bearer {access_token}",
#        "Content-Type": "application/json"
#    },
#    data=json.dumps({"content": file_contents_b64})
#)
#
#if response.ok:
#    # Get the file ID from the response
#    file_id = response.json()["d"]["UniqueId"]
#
#    # Share the file with the specified users
#    for email in user_emails:
#        share_endpoint = f"https://graph.microsoft.com/v1.0/drives/{file_id}/invite"
#        share_data = {
#            "requireSignIn": True,
#            "sendInvitation": True,
#            "roles": [role],
#            "recipients": [{"email": email}]
#        }
#
#        share_response = requests.post(
#            url=share_endpoint,
#            headers={
#                "Authorization": f"Bearer {access_token}",
#                "Content-Type": "application/json"
#            },
#            data=json.dumps(share_data)
#        )
#
#        print(f"Shared file with {email} ({role} access)")
#else:
#    print("Failed to share file")
#    print_verbose(response.status_code)
#    print_verbose(response.headers)
#    print_verbose(response.text)
