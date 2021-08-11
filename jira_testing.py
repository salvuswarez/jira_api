#from os import path
# import re
#from typing import Optional
# from jira import JIRA
# import datetime
# import pandas as pd
from iJira import iJira

# #---------------------------------------------------------------------------
# # Authenticate JIRA API
# #---------------------------------------------------------------------------
# # find private key
# key_cert = r'C:\Users\chughes7\.oauthconfig\oauth.pem'
# key_cert_data = None

# # load private key data into var
# with open(key_cert, 'r') as key_cert_file:
#     key_cert_data = key_cert_file.read()

# # build auth dict
# oauth_dict = {
#     'access_token_secret': 'IZt12OXrU13MUAUtFrRgAaXbdhkMuRHr',
#     'consumer_key': 'FEMAFRDOAuthKey',
#     'access_token':'elcfe4HorZnjoHhCLXK9vLoXbMZyLNu7',
#     'key_cert':key_cert_data
# }

# # login and activate jira connection
# jira = JIRA('https://maestro-api.dhs.gov/jira',oauth=oauth_dict)

#----------------------------------------------------------------------------


# test case
japi = iJira(r'.\auth\oauth.pem')
japi.get_issues().to_excel(r'./data/test.xlsx')





# #----------------------------------------------------------------------------

# jira = iJira(r'')
# issues = jira.getIssues('FRD')


#----------------------------------------------------------------------------
# building out first data set of just issue details
#----------------------------------------------------------------------------
# get total issue count
#total = int(jira.search_issues('project= FRD',maxResults=1,startAt=0,json_result=True)['total'])

# build list of dictionaries for each issue
#issues = iJira.Jira_Issue(jira,'FRD-861').record
issue = jira.issue('FRD-861')
# push list into dataframe
#d = pd.DataFrame(issues)

print(jira.watchers(issue).watchCount)
for w in jira.watchers(issue).watchers:
    print(w)
#d.to_excel('test.xlsx',header=True,engine='openpyxl')
#-------------------------------------------------------------------------------
