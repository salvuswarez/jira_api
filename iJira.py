# -*- coding: utf-8 -*-
# Name: iJira.py 
# Created by Cody Hughes 
# created date: 08/11/2021
# current version: 1
# 
# Description:
#   This interface is intended to offer access to all data stored within Jira. It requires no manual login as it uses a 
# preset authentication. 
#
#

    
from jira import JIRA

from ast import literal_eval as le
from datetime import datetime
import logging
import pandas as pd
import re
from typing import Optional

# module's logger
_log = logging.getLogger(__name__)


class iJira:
    """Interface for Jira API commands
    """
    __cert_file: str
    __cert_data: object
    __jira: JIRA
    __is_logged_in: bool
    __issues: list = []
    __issue_links: dict = {}
    __comments: dict = {}
    __components: dict = {}
    __labels: dict = {}
    __watchers: dict = {}


    def __init__(self,cert_file_path:str)->None:
        """Initializes interface object with authentication info"""
        
        self.__cert_file = cert_file_path
        self.__is_logged_in = False
        self.__load_interface()


    def __load_interface(self)->None:
        """Performs API login from interface initialization"""
        
        try:
            # load private key data into var
            with open(self.__cert_file, 'r') as key_cert_file:
                self.__cert_data = key_cert_file.read()
            #print(f'cert file: {self.__cert_data}')
            
        except FileNotFoundError as e:
            # if no file found push error
            _log.error(f'No PEM file found in given location: {self.__cert_file}',exec_info=True)
            raise FileNotFoundError("No .PEM file found!")

        # get auth dict from txt file
        oauth = self.__read_in_auth_dict()

        # add in cert data file
        oauth['key_cert'] = self.__cert_data

        try: # to login here, if so set flag __is_logged_in
            self.__jira = JIRA('https://maestro-api.dhs.gov/jira',oauth=oauth)
            self.__is_logged_in = True
        except Exception as e:
            #TODO: replace exception with proper faild login exception
            _log.error('Failed to login',exec_info=True)
            self.__is_logged_in = False


    @property
    def jira_obj(self):
        """the Jira object is the JIRA python library API object

        Returns:
            [JIRA]: The underlying JIRA api object
        """
        return self.__jira

    @property
    def is_logged_in(self)->bool:
        """Property to let user know of successful login or not

        Returns:
        -----
            bool: True if login was successful, false otherwise
        """
        return self.__is_logged_in

   
    def get_issues(self,limit:Optional[int]=None,project_key:Optional[str]='FRD',return_df:bool=False,force_refresh:bool=False):
        """Get issue objects and return as list of issue objects

        Parameters:
        -----
            limit (Optional[int], optional): Number of Issues to return. Default is to return All.
            project_key (Optional[str], optional): [description]. Defaults to `'FRD'`.
            return_df (bool, optional): If you need a pandas dataframe instead of list of Issue objects set to `True`. Defaults to `False`.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            Defaults to list, but able to return pandas dataframe if needed
        """
        
        # reuse a previous pull of issues it it's not empty
        if force_refresh or len(self.__issues) == 0:
            _log.info('Refreshing Issues...')
            
            # check for limit
            if limit is None:
                # get total issue count
                limit = int(self.__jira.search_issues(
                            f'project = {project_key}',
                                maxResults=1,startAt=0,json_result=True)['total'])
                _log.info(f'Issue Count: {limit} issue(s) found.',exc_info=True)

            # get issues list of dict
            self.__issues = [Jira_Issue(self.__jira,i) 
                                for i in self.__jira.search_issues(
                                    f'project = {project_key}',maxResults=limit)]
            
            _log.info(f'{len(self.__issues)} found.')
            
        if return_df:
            return pd.DataFrame([i.record for i in self.__issues])
        else:
            return self.__issues


    def get_issue_links(self,limit:Optional[int]=None,project_key:Optional[str]='FRD',return_df:bool=False,force_refresh:bool=False):
        """Get Issue Links and return a list of Issue Links

        Parameters:
        -----
            limit (Optional[int], optional): Number of issues to return can be limited. Default is to return All.
            project_key (Optional[str], optional): Specifiy a Project Key to pull issues from. Defaults to `'FRD'`.
            return_df (bool, optional): Option to return as Pandas Dataframe instead of dict. Defaults to `False`.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            dict: By default it returns a dictionary of issue keys with issue link dictionaries of {id:name}
        """
        
        if force_refresh or len(self.__issue_links) == 0:
            _log.info('Refreshing Issue Links...')
            
            # check for limit
            if limit is None:
                # get total issue count
                limit = int(self.__jira.search_issues(
                            f'project = {project_key}',
                                maxResults=1,startAt=0,json_result=True)['total'])

            # get issues
            issues = self.get_issues(limit=limit,project_key=project_key,force_refresh=force_refresh)

            # setup empty dict for results
            results = {}
            
            #add rownum for indexing
            rownum = 0
            
            # temp issue keys
            inward_key = ''
            outward_key = ''

            # loop through all issues and build dict of all components
            for issue in issues:
                for l in issue.issue_links:
                    rownum += 1
                    
                    if l.inward_issue:
                        inward_key = l.inward_issue.key
                    if l.outward_issue:
                        outward_key = l.outward_issue.key
                    
                    results[f'{rownum}']={'issue_key':issue.key,
                                            'link_id':l.link_id,
                                            'link_type':l.link_type,
                                            'link_inward_desc':l.inward_descr,
                                            'link_outward_desc':l.outward_descr,
                                            'inward_issue_key':inward_key,
                                            'outward_issue_key':outward_key}
            
            # set var to hold previous pull of links
            self.__issue_links = results
            _log.info(f'{len(self.__issue_links)} found')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__issue_links,orient='index')
            #df.index.name = 'Issue_Key'
            return df
        else:
            return self.__issue_links


    def get_comments(self,limit:Optional[int]=None,project_key:Optional[str]='FRD',return_df:bool=False,force_refresh:bool=False):
        """Get Comments and return a dictionary of comments

        Parameters:
        -----
            limit (Optional[int], optional): Number of issues to return can be limited. Default is to return All..
            project_key (Optional[str], optional): Specifiy a Project Key to pull issues from. Defaults to `'FRD'`.
            return_df (bool, optional): Option to return as Pandas Dataframe instead of dict. Defaults to `False`.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            dict: By default it returns a dictionary of issue keys with comment dictionaries of {id:name}
        """
        
        if force_refresh or len(self.__comments) == 0:
            _log.info('Refreshing Comments...')
            
            # check for limit
            if limit is None:
                # get total issue count
                limit = int(self.__jira.search_issues(
                            f'project = {project_key}',
                                maxResults=1,startAt=0,json_result=True)['total'])

            # get issues
            issues = self.get_issues(limit=limit,project_key=project_key,force_refresh=force_refresh)

            # setup empty dict for results
            results = {}
            
            #add rownum for indexing
            rownum = 0
            
            # loop through all issues and build dict of all components
            for issue in issues:
                for c in issue.comments:
                    rownum += 1
                    results[f'{rownum}']={'issue_key':issue.key,
                                            'comment_id':c.id,
                                            'comment_body':c.body}
            
            # set var to hold commments
            self.__comments = results
            _log.info(f'{len(self.__comments)} found.')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__comments,orient='index')
            #df.index.name = 'Issue_Key'
            return df
        else:
            return self.__comments    


    def get_components(self,limit:Optional[int]=None,project_key:Optional[str]='FRD',return_df:bool=False,force_refresh:bool=False):
        """Get Components and return a dictionary of components

        Parameters:
        -----
            limit (Optional[int], optional): Number of issues to return can be limited. Default is to return All.
            project_key (Optional[str], optional): Specifiy a Project Key to pull issues from. Defaults to `'FRD'`.
            return_df (bool, optional): Option to return as Pandas Dataframe instead of dict. Defaults to `False`.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            dict: By default it returns a dictionary of issue keys with component dictionaries of {id:name}
        """
        
        if force_refresh or len(self.__components) == 0:
            _log.info('Refreshing Components...')
            
            # check for limit
            if limit is None:
                # get total issue count
                limit = int(self.__jira.search_issues(
                            f'project = {project_key}',
                                maxResults=1,startAt=0,json_result=True)['total'])

            # get issues
            issues = self.get_issues(limit=limit,project_key=project_key,force_refresh=force_refresh)

            # setup empty dict for results
            results = {}
            
            #add row num for indexing
            rownum = 0
            
            # loop through all issues and build dict of all components
            for issue in issues:
                for c in issue.components:
                    rownum += 1
                    results[f'{rownum}']={'issue_key':issue.key,
                                            'component_id': c.id,
                                            'component_name':c.name}
            
            # set var for component storage
            self.__components = results
            _log.info(f'{len(self.__components)} found.')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__components,orient='index')
            #df.index.name = 'Issue_Key'
            return df
        else:
            return self.__components


    def get_labels(self,limit:Optional[int]=None,project_key:Optional[str]='FRD',return_df:bool=False,force_refresh:bool=False):
        """Get Labels and return a dictionary of labels

        Parameters:
        -----
            limit (Optional[int], optional): Number of issues to return can be limited. Default is to return All.
            project_key (Optional[str], optional): Specifiy a Project Key to pull issues from. Defaults to `'FRD'`.
            return_df (bool, optional): Option to return as Pandas Dataframe instead of dict. Defaults to `False`.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            dict: By default it returns a dictionary of issue keys with label dictionaries of {id:name}
        """
        
        if force_refresh or len(self.__labels) == 0:
            _log.info('Refreshing Labels...')
            
            # check for limit
            if limit is None:
                # get total issue count
                limit = int(self.__jira.search_issues(
                            f'project = {project_key}',
                                maxResults=1,startAt=0,json_result=True)['total'])

            # get issues
            issues = self.get_issues(limit=limit,project_key=project_key,force_refresh=force_refresh)

            # setup empty dict for results
            results = {}
            
            #add row num for indexing
            rownum = 0
            # loop through all issues and build dict of all components
            for issue in issues:
                for l in issue.labels:
                    rownum += 1
                    results[f'{rownum}']={'issue_key':issue.key,
                                            'label_name':l}
                    
            # set var for storage
            self.__labels = results
            _log.info(f'{len(self.__labels)} found.')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__labels,orient='index')
            #df.index.name = 'Issue_Key'
            return df
        else:
            return self.__labels


    def get_watchers(self,limit:Optional[int]=None,project_key:Optional[str]='FRD',return_df:bool=False,force_refresh:bool=False):
        """Get Watchers and return a dictionary of watchers

        Parameters:
        -----
            limit (Optional[int], optional): Number of issues to return can be limited. Default is to return All.
            project_key (Optional[str], optional): Specifiy a Project Key to pull issues from. Defaults to `'FRD'`.
            return_df (bool, optional): Option to return as Pandas Dataframe instead of dict. Defaults to `False`.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            dict: By default it returns a dictionary of issue keys with watcher dictionaries of {id:name}
        """

        if force_refresh or len(self.__watchers) == 0:
            _log.info('Refreshing Watchers...')
            
            # check for limit
            if limit is None:
                # get total issue count
                limit = int(self.__jira.search_issues(
                            f'project = {project_key}',
                                maxResults=1,startAt=0,json_result=True)['total'])

            # get issues
            issues = self.get_issues(limit=limit,project_key=project_key,force_refresh=force_refresh)

            # setup empty dict for results
            results = {}
            
            #add row num for indexing
            rownum = 0 
            
            # loop through all issues and build dict of all components
            for issue in issues:
                for w in issue.watchers:
                    rownum +=1
                    results[f'{rownum}']={'issue_key':issue.key,
                                            'watcher_key':w.key,
                                            'watcher_name':w.name,
                                            'watcher_email':w.emailAddress,
                                            'watcher_display_name':w.displayName,
                                            'watcher_active':w.active}
            
            self.__watchers = results
            _log.info(f'{len(self.__watchers)} found.')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__watchers,orient='index')
            #df.index.name = 'Issue_Key'
            return df
        else:
            return self.__watchers


    def export_issues_report(self,f_name:str='Issues',f_path:str=r'.\data',limit:Optional[int]=None,force_refresh:bool=False)->str:
        """Saves issues report out to excel xlsx file

        Parameters:
        -----
            f_name (str, optional): File name (NO EXTENSION). Defaults to `'Issues'`.
            f_path (str, optional): File Path . Defaults to r`'.\data'`.
            limit (Optional[int], optional): Number of records to return, if none returns all found. Default is to return All.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.    
                                                
        Returns:
        -----
            str: The path to where the file was saved. 
        """
        
        now = datetime.now()
        save_loc = rf'{f_path}\{f_name}_{now.strftime("%Y_%m_%d_%H_%M")}.xlsx'
        self.get_issues(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc,index=False)

        return save_loc


    def export_issue_links_report(self,f_name:str='IssueLinks',f_path:str=r'.\data',limit:Optional[int]=None,force_refresh:bool=False)->str:
        """Saves issue links report out to excel xlsx file

        Parameters:
        -----
            f_name (str, optional): File name (NO EXTENSION). Defaults to `'IssueLinks'`.
            f_path (str, optional): File Path . Defaults to r`'.\data'`.
            limit (Optional[int], optional): Number of issues to search through, if none searches all found. Default is to return All.
            force_refresh (bool, optional): Default is `False` - if the issue links have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            str: The path to where the file was saved. 
        """
        
        now = datetime.now()
        save_loc = rf'{f_path}\{f_name}_{now.strftime("%Y_%m_%d_%H_%M")}.xlsx'
        self.get_issue_links(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_comments_report(self,f_name:str='Comments',f_path:str=r'.\data',limit:Optional[int]=None,force_refresh:bool=False)->str:
        """Saves components report out to excel xlsx file

        Parameters:
        -----
            f_name (str, optional): File name (NO EXTENSION). Defaults to `'Comments'`.
            f_path (str, optional): File Path . Defaults to r`'.\data'`.
            limit (Optional[int], optional): Number of issues to search through, if none searches all found. Default is to return All.
            force_refresh (bool, optional): Default is `False` - if the Comments have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            str: The path to where the file was saved. 
        """
        
        now = datetime.now()
        save_loc = rf'{f_path}\{f_name}_{now.strftime("%Y_%m_%d_%H_%M")}.xlsx'
        self.get_comments(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_components_report(self,f_name:str='Components',f_path:str=r'.\data',limit:Optional[int]=None,force_refresh:bool=False)->str:
        """Saves components report out to excel xlsx file

        Parameters:
        -----
            f_name (str, optional): File name (NO EXTENSION). Defaults to `'Components'`.
            f_path (str, optional): File Path . Defaults to r`'.\data'`.
            limit (Optional[int], optional): Number of issues to search through, if none searches all found. Default is to return All.
            force_refresh (bool, optional): Default is `False` - if the Components have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            str: The path to where the file was saved. 
        """
        
        now = datetime.now()
        save_loc = rf'{f_path}\{f_name}_{now.strftime("%Y_%m_%d_%H_%M")}.xlsx'
        self.get_components(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_label_report(self,f_name:str='Labels',f_path:str=r'.\data',limit:Optional[int]=None,force_refresh:bool=False)->str:
        """Saves labels report out to excel xlsx file

        Parameters:
        -----
            f_name (str, optional): File name (NO EXTENSION). Defaults to `'Labels'`.
            f_path (str, optional): File Path . Defaults to r`'.\data'`.
            limit (Optional[int], optional): Number of issues to search through, if none searches all found. Default is to return All.
            force_refresh (bool, optional): Default is `False` - if the Labels have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            str: The path to where the file was saved. 
        """
        
        now = datetime.now()
        save_loc = rf'{f_path}\{f_name}_{now.strftime("%Y_%m_%d_%H_%M")}.xlsx'
        self.get_labels(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_watchers_report(self,f_name:str='Watchers',f_path:str=r'.\data',limit:Optional[int]=None,force_refresh:bool=False)->str:
        """Saves watchers report out to excel xlsx file

        Parameters:
        -----
            f_name (str, optional): File name (NO EXTENSION). Defaults to `'Watchers'`.
            f_path (str, optional): File Path . Defaults to r`'.\data'`.
            limit (Optional[int], optional): Number of issues to search through, if none searches all found. Default is to return All.
            force_refresh (bool, optional): Default is `False` - if the Watchers have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            str: The path to where the file was saved. 
        """
        
        now = datetime.now()
        save_loc = rf'{f_path}\{f_name}_{now.strftime("%Y_%m_%d_%H_%M")}.xlsx'
        self.get_watchers(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    @classmethod
    def __read_in_auth_dict(cls,path:Optional[str] = r'.\auth\auth_dict.txt')->dict:
        """Reads in a text file in dictionary format

        Parameters:
        -----
            path (Optional[str], optional): Path to auth file. Defaults to `.\\auth\\auth_dict.txt`.

        Raises:
        -----
            FileNotFoundError: if no auth file found in default location and no location provided

        Returns:
        -----
            dict: Dictionary object for use in authentication
        """
        try:
            f = open(path,'r')
            d = {}
            d = le(f.read())
        except FileNotFoundError as e:
            _log.error(f'Could not find Auth File in : {path}',exec_info=True)
            raise FileNotFoundError('No Auth file found!')
        finally:
            return d


class Jira_Issue():
    """Contains all details and functionality for a single issue

    """
    __authorized_jira: JIRA
    __agg_progress: int
    __agg_progress_total: int
    __assignee_name: str
    __assignee_key: str
    __comments: dict = {}
    __comments_count: int
    __components: dict = {}
    __created_dt: str
    __creator_key: str
    __creator_name: str
    __cur_status: str
    __epic_key: str
    #__fixed_version: str    # TODO: Not yet implemented
    __is_subtask:bool
    __issue_age_txt: str
    __issue_key: str
    __issue_links: list = []
    __issue_record: dict
    __issue_type: str
    __labels: dict = {}
    __label_count: int
    __latest_comment: str
    __latest_comment_dt: str
    __priority_type:str
    __priority_descr:str
    __progress: int
    __project_key: str
    __project_name: str
    __progress_total: int
    __reporter_key: str
    __reporter_name: str
    __summary: str
    __vote_count: int
    __watchers: dict = {}
    __watcher_count: int
    
    
    def __init__(self,pJira: JIRA,pIssue_Key: str)->None:
        """Initilizer for Issue object.

        Parameters:
        -----
            pJira (`JIRA`): The instantiated / authenticated `JIRA` API object
            pIssue_Key (str): The Issue Key to load
        """

        self.__issue_key = pIssue_Key
        self.__authorized_jira = pJira
        self.__issue_record = {}
        self.__load_issue()


    def __load_issue(self):
        """initial load up of issue object without lists"""
        jira = self.__authorized_jira
        issue = jira.issue(self.__issue_key)

        try:
            # does not get added as field for output since it's a dict / list
            self.__watchers = jira.watchers(issue).watchers
            self.__comments = jira.comments(issue)
            self.__components = issue.fields.components
            self.__issue_links = [Issue_Link(self.__authorized_jira,l) for l in issue.fields.issuelinks]
            self.__labels = issue.fields.labels

            # start building record
            self.__issue_record['issue_key'] = self.__issue_key
            self.__issue_record['created_date'] = self.__created_dt = datetime.strptime(issue.fields.created,'%Y-%m-%dT%H:%M:%S.%f%z').date()
            self.__issue_record['agg_progress'] = self.__agg_progress = issue.fields.aggregateprogress.progress
            self.__issue_record['agg_progress_total'] = self.__agg_progress_total = issue.fields.aggregateprogress.total
            self.__issue_record['latest_comment'] = self.__latest_comment = self.clean_html(str(issue.fields.customfield_18501))

            # if no comment, this field wont exist
            if issue.fields.customfield_18502:
                self.__issue_record['latest_comment_date'] = self.__latest_comment_dt = datetime.strptime(issue.fields.customfield_18502,'%Y-%m-%dT%H:%M:%S.%f%z').date()
            else:
                self.__issue_record['latest_comment_date'] = self.__latest_comment_dt = None

            self.__issue_record['epic_key'] = self.__epic_key = issue.fields.customfield_10801
            self.__issue_record['summary'] = self.__summary = issue.fields.summary
            self.__issue_record['priority_type'] = self.__priority_type = issue.fields.priority.name
            #self.__issue_record['priority_descr'] = self.__priority_descr = issue.fields.priority.description # seems to fail to find any descriptions
            self.__issue_record['project_key'] = self.__project_key = issue.fields.project.key
            self.__issue_record['project_name'] = self.__project_name = issue.fields.project.name
            self.__issue_record['progress'] = self.__progress = issue.fields.progress.progress
            self.__issue_record['progress_total'] = self.__progress_total = issue.fields.progress.total
            self.__issue_record['reporter_key'] = self.__reporter_key = issue.fields.reporter.key
            self.__issue_record['reporter_name'] = self.__reporter_name = issue.fields.reporter.displayName
            self.__issue_record['creator_key'] = self.__creator_key = issue.fields.creator.key
            self.__issue_record['creator_name'] = self.__creator_name = issue.fields.creator.displayName
            self.__issue_record['current_status'] = self.__cur_status = issue.fields.status.name
            self.__issue_record['issue_age_txt'] = self.__issue_age_txt = issue.fields.customfield_22332
            self.__issue_record['assignee_key'] = self.__assignee_key = issue.fields.assignee.key
            self.__issue_record['assignee_name'] = self.__assignee_name = issue.fields.assignee.displayName
            self.__issue_record['issue_type'] = self.__issue_type = issue.fields.issuetype.name
            self.__issue_record['is_subtask'] = self.__is_subtask = issue.fields.issuetype.subtask
            self.__issue_record['watcher_count'] = self.__watcher_count = len(self.__watchers)
            self.__issue_record['comment_count'] = self.__comments_count = len(self.__comments)
            self.__issue_record['linked_issue_count'] = self.__linked_issue_count = len(self.__issue_links)
            self.__issue_record['label_count'] = self.__label_count = len(self.__labels)
            self.__issue_record['vote_count'] = self.__vote_count = issue.fields.votes.votes
            
        except AttributeError as e:
            # Error is thrown when a field is empty.
            # Just ignore and move on, as Pandas turns it into None
            
            pass

        # TODO: build out properties that pull in lists of data listed below. Return as dataframes
        #self.__fixed_version = issue.fields.fixVersions returns a list handle in own method

    @property
    def key(self)->str:
        """Issue Key string from Jira

        Returns:
        -----
            str: Example - `FRD-861`
        """
        return self.__issue_key

    @property
    def created_date(self)->str:
        """Date the Issue was created

        Returns:
        -----
            datetime.date
        """
        return self.__created_dt
    
    @property
    def aggregate_progress(self)->int:
        """Aggregate progress value of Issue

        Returns:
        -----
            int
        """
        return self.__agg_progress
    
    @property
    def aggregate_progress_total(self)->int:
        """Aggregate progress Max / Total value ie the denominator

        Returns:
        -----
            int
        """
        return self.__agg_progress_total

    @property
    def latest_comment(self)->str:
        """Latest comment made on Issue

        Returns:
        -----
            str
        """
        return self.__latest_comment

    @property
    def latest_comment_date(self)->str:
        """Date of latest comment on Issue

        Returns:
        -----
            datetime.date
        """
        return self.__latest_comment_dt

    @property
    def summary(self)->str:
        """Issue Summary

        Returns:
        -----
            str
        """
        return self.__summary

    @property
    def project_key(self)->str:
        """The Project this Issue belongs to

        Returns:
        -----
            str: Example - `FRD`
        """
        return self.__project_key

    @property
    def project_name(self)->str:
        """Name of Project that the Issue belongs to

        Returns:
        -----
            str: Example - `AC Project Name`
        """
        return self.__project_name

    @property
    def progress(self)->int:
        """Issue's Progress amount

        Returns:
        -----
            int
        """
        return self.__progress
    
    @property
    def progress_total(self)->int:
        """Issue's Progress Max / Total value ie the denominator

        Returns:
        -----
            int
        """
        return self.__progress_total

    @property
    def reporter_key(self)->str:
        """Key string for Reporter of Issue

        Returns:
        -----
            str: Example - `'JIRAUSER45364'` or email
        """
        return self.__reporter_key

    @property
    def reporter_name(self)->str:
        """Name of assigned Reporter

        Returns:
        -----
            str: Example - `'Bob Ross'`
        """
        return self.__reporter_name

    @property
    def creator_key(self)->str:
        """Key string for Creator of Issue

        Returns:
        -----
            str: Example - `'JIRAUSER45364'` or email
        """
        return self.__creator_key

    @property
    def creator_name(self)->str:
        """Name of Creator

        Returns:
        -----
            str: Example - `'Bob Ross'`
        """
        return self.__creator_name

    @property
    def current_status(self)->str:
        """Current Status of the Issue

        Returns:
        -----
            str: Example - `'On Hold'`
        """
        return self.__cur_status

    @property
    def age(self)->str:
        """The Age of the Issue in string format

        Returns:
        -----
            str: Example - `'1w 5d 6h'`
        """
        return self.__issue_age_txt

    @property
    def assignee_key(self)->str:
        """Key string for Assignee of Issue

        Returns:
        -----
            str: Example - `'JIRAUSER45364'` or email
        """
        return self.__assignee_key

    @property
    def assignee_name(self)->str:
        """Name of Assignee

        Returns:
        -----
            str: Example - `'Bob Ross'`
        """
        return self.__assignee_name

    @property
    def issue_type(self)->str:
        """The type of Issue

        Returns:
        -----
            str: Example - `'Task'`; `'Bug'`;`'Improvement'` etc.
        """
        return self.__issue_type

    @property
    def is_subtask(self)->bool:
        """Determines whether issue is a subtask or not

        Returns:
        -----
            bool
        """
        return self.__is_subtask

    @property
    def record(self)->dict:
        """All fields and values placed into dictionary
        for a singular 'record' of the Issue

        Returns:
        -----
            dict
        """
        return self.__issue_record

    @property
    def watcher_count(self)->int:
        """Count of watchers for issue"""
        return self.__watcher_count

    @property
    def watchers(self)->dict:
        """All watchers associated with Issue in dictionary form

        Returns:
        -----
            dict: Of all watchers
        """
        return self.__watchers

    @property
    def comments(self)->dict:
        """All comments associated with Issue in dictionary form

        Returns:
        -----
            dict: Of all comments
        """
        return self.__comments

    @property
    def comments_count(self)->int:
        """Count of all the comments

        Returns:
        -----
            int
        """
        return self.__comments_count

    @property
    def components(self)->dict:
        """All components associated with Issue in dictionary form

        Returns:
        -----
            dict: Of all components
        """
        return self.__components

    @property
    def issue_links(self)->list:
        """Issue links are the Link object itself between 2 issues.

        Returns:
        -----
            list: All linked issues
        """
        return self.__issue_links

    @property
    def linked_issue_count(self)->int:
        """Count of linked issues

        Returns:
        -----
            int
        """
        return self.__linked_issue_count

    @property 
    def labels(self)->dict:
        """Labels associated with issue in list form

        Returns:
        -----
            list
        """
        return self.__labels

    @property
    def label_count(self)->int:
        """Count of all labels associated with issue

        Returns:
        -----
            int
        """
        return self.__label_count

    @property
    def priority(self)->str:
        """This is the Type of priority assigned to issue

        Returns:
        -----
            str
        """
        return self.__priority_type

    @property
    def priority_desc(self)->str:
        """This is the description of the priorty type

        Returns:
        -----
            str
        """
        return self.__priority_descr

    @property
    def vote_count(self)->int:
        """Count of all votes for issue

        Returns:
        -----
            int
        """
        return self.__vote_count
    
    @property
    def epic_key(self)->str:
        """Epic Key for epic that is associated with issue

        Returns:
        -----
            str
        """
        return self.__epic_key

    @classmethod
    def clean_html(cls,raw_html:str='')->str:
            """Static method for cleaning out HTML tags from text

            Parameters:
            ----------
                raw_html (str): Text value that needs to be cleaned

            Returns:
            --------
                [str]: Cleaned text without any HTML tags
            """
            if raw_html =='None':
                raw_html = ''
            
            cleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
            cleantext = cleaner.sub('',raw_html)
            return cleantext


class Issue_Link():
    #contains Issue link details, like a list of issue objects, issue link type
    __id: str
    __type: str
    __inward_desc: str
    __outward_desc: str
    __inward_issue: Jira_Issue = None
    __outward_issue: Jira_Issue = None
    __jira: JIRA
    __link_obj: dict

    def __init__(self,pJira:JIRA,link_obj):
        self.__jira = pJira
        self.__link_obj = link_obj
        self.__id = self.__link_obj.id
        self.__type = self.__link_obj.type.name
        self.__inward_desc = self.__link_obj.type.inward
        self.__outward_desc = self.__link_obj.type.outward

        #have to check if there is an issue or not. if not, this attr wont exist.
        if hasattr(self.__link_obj,'inwardIssue'):
            self.__inward_issue = Jira_Issue(self.__jira,self.__link_obj.inwardIssue)
        
        if hasattr(self.__link_obj,'outwardIssue'):
            self.__outward_issue = Jira_Issue(self.__jira,self.__link_obj.outwardIssue)

    @property
    def link_id(self)->str:
        """Issue Link id"""
        return self.__id

    @property
    def link_type(self)->str:
        """Type of Link"""
        return self.__type

    @property
    def inward_issue(self)->Jira_Issue:
        """Issue that is 'Parent'"""
        return self.__inward_issue

    @property
    def outward_issue(self)->Jira_Issue:
        """Issue that is 'Child'"""
        return self.__outward_issue

    @property
    def inward_descr(self)->str:
        """A description of the link type related to the issue itself"""
        return self.__inward_desc

    @property
    def outward_descr(self)->str:
        """A description of the link type related to the issue itself"""
        return self.__outward_desc