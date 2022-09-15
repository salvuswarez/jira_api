# -*- coding: utf-8 -*-
# Name: iJira.py 
# Created by Cody Hughes 
# created date: 08/11/2021
# current version: 1
# 
# Description:
#   This interface is intended to offer access to all data stored within
#   Jira. It requires no manual login as it uses a 
#   preset authentication. 
#
#

    
from jira import JIRA

from ast import literal_eval as le
from datetime import datetime, timedelta
import logging
import pandas as pd
import re
from typing import Optional
import configparser

# module's logger
_log = logging.getLogger(__name__)


class iJira():
    """Interface for working with Jira API. It allows you to choose a 
    Project and query content from it. 
    """
    DATE_FORMAT = "%Y/%m/%d %H:%M"
    
    __cert_file: str
    __cert_data: object
    __personal_access_token: str
    __active_project_key: str
    __config_parser: configparser.ConfigParser
    __jira: JIRA
    __is_logged_in: bool
    __issues: list = []
    __issue_links: dict = {}
    __comments: dict = {}
    __components: dict = {}
    __labels: dict = {}
    __histories: dict = {}
    __watchers: dict = {}
    __time_in_status: dict = {}
    __status_issue_count_time_series: dict
    
    def __init__(self, config_file_path:str)->None:
        """Initializes a JIRA object allowing access to begin querying 
        content from a given Project

        Args:
            config_file_path (str): UNC path to the config file to be 
            used
        """
        
        self.__config_parser = self.__load_config(config_file_path)
        self.__active_project_key = self.__config_parser['authentication']['default_project_key']
        self.__personal_access_token = self.__config_parser['authentication']['personal_access_token']
        #self.__cert_file = self.__config_parser['authentication']['cert_file_path']
        
        self.__is_logged_in = False
        self.__status_issue_count_time_series = {}
        self.__load_interface()


    def __load_config(self,config_file_path:str)->configparser.ConfigParser:
        # load in the config file here
        """Loads in config details from default location

        Args:
            config_file_path (str, optional): Path to config file.

        """
        _log.debug('loading config info...')
        config = configparser.ConfigParser()
        config.read(config_file_path)
        self.__config_parser = config
        
        return self.__config_parser
        
    def __load_interface(self)->None:
        """Performs API login from interface initialization"""
        
        # try:
        #     # load private key data into var
        #     with open(self.__cert_file, 'r') as key_cert_file:
        #         self.__cert_data = key_cert_file.read()
        #     #print(f'cert file: {self.__cert_data}')
            
        # except FileNotFoundError:
        #     # if no file found push error
        #     _log.error(f'No PEM file found in given location: {self.__cert_file}',exc_info=True)
        #     raise FileNotFoundError("No .PEM file found!")

        # # get auth dict from txt file
        # oauth = self.__read_in_auth_dict()

        # # add in cert data file
        # oauth['key_cert'] = self.__cert_data
        #TODO: refactor this function to accept other methods of auth
        try: # to login here, if so set flag __is_logged_in
            #self.__jira = JIRA('https://maestro-api.dhs.gov/jira',oauth=oauth)
            # try to login with PAT instead of oauth
            headers = JIRA.DEFAULT_OPTIONS["headers"].copy()
            headers['Authorization'] = f"Bearer {self.__personal_access_token}"
            self.__jira = JIRA('https://maestro-api.dhs.gov/jira/',options={"headers":headers})
            self.__is_logged_in = True
            _log.info("Successfull Login | Project: " \
                f"{self.__config_parser['authentication']['default_project_key']}")
        except Exception:
            #TODO: replace exception with proper faild login exception
            _log.error('Failed to login',exc_info=True)
            self.__is_logged_in = False


    @property
    def active_project_key(self)->str:
        """The currently selected Jira Project

        Returns:
            str: Project name / Key
        """
        return self.__active_project_key

    @active_project_key.setter
    def active_project_key(self,key:str)->None:
        """Change / set the currently selected Jira Project to be used

        Args:
            key (str): Project Key / Name
        """
        # TODO: may need to force a content reset if project is changed
        self.__active_project_key = key
        
        return self.active_project_key
    
    
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

   
    def get_issues(self,limit:Optional[int]=None,project_key:Optional[str]=None,return_df:bool=False,force_refresh:bool=False):
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
        if not project_key:
            project_key = self.active_project_key
            
            
        # reuse a previous pull of issues if it's not empty
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
            self.__issues = [Jira_Issue(self.__jira,i.key) 
                                for i in self.__jira.search_issues(
                                    f'project = {project_key}',maxResults=limit)]
            
            _log.info(f'{len(self.__issues)} Issues retreived.')
            
        if return_df:
            df = pd.DataFrame([i.record for i in self.__issues])
            df.insert(0, 'refresh_date', pd.to_datetime('now').replace(microsecond=0))
            return df
        else:
            return self.__issues


    def get_issue_links(self,limit:Optional[int]=None,project_key:Optional[str]=None,return_df:bool=False,force_refresh:bool=False):
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
        if not project_key:
            project_key = self.active_project_key
            
            
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
                        inward_key = l.inward_issue
                    if l.outward_issue:
                        outward_key = l.outward_issue
                    
                    results[f'{rownum}']={'issue_key':issue.key,
                                            'link_id':l.link_id,
                                            'link_type':l.link_type,
                                            'link_inward_desc':l.inward_descr,
                                            'link_outward_desc':l.outward_descr,
                                            'inward_issue_key':inward_key,
                                            'outward_issue_key':outward_key,
                                            'refresh_date':pd.to_datetime('now').replace(microsecond=0)}
            
            # set var to hold previous pull of links
            self.__issue_links = results
            _log.info(f'{len(self.__issue_links)} Issue links retrieved')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__issue_links,orient='index')
            return df
        else:
            return self.__issue_links


    def get_histories(self,limit:Optional[int]=None,project_key:Optional[str]=None,return_df:bool=False,force_refresh:bool=False):
        """Get Historic records for all Issues

        Parameters:
        -----
            limit (Optional[int], optional): Number of issues to return can be limited. Default is to return All.
            project_key (Optional[str], optional): Specifiy a Project Key to pull issues from. Defaults to `'FRD'`.
            return_df (bool, optional): Option to return as Pandas Dataframe instead of dict. Defaults to `False`.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            dict: By default it returns a dictionary of Historic Records
        """
        if not project_key:
            project_key = self.active_project_key  
            
                  
        if force_refresh or len(self.__histories) == 0:
            _log.info('Refreshing Histories...')
            
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
                for rec in issue.change_history:
                    # filter for last 3 months only
                    #if abs(pd.to_datetime(rec.updated_date)-pd.to_datetime(datetime.now().date())).days <=90: 
                    # set row number for indexing
                    rownum += 1
                    
                    # build out dict of each record
                    results[f'{rownum}']={'issue_key':issue.key,
                                            'updated_by':rec.updated_by,                                              
                                            'date_of_change':rec.updated_date,
                                            'field':rec.field_name,
                                            'new_value':rec.new_value,
                                            'old_value':rec.old_value,
                                            'refresh_date':pd.to_datetime('now').replace(microsecond=0)}
            
            # set var to hold previous pull of links
            self.__histories = results
            _log.info(f'{len(self.__histories)} Historic Changes retrieved')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__histories,orient='index')
            return df
        else:
            return self.__histories


    def get_comments(self,limit:Optional[int]=None,project_key:Optional[str]=None,return_df:bool=False,force_refresh:bool=False):
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
        if not project_key:
            project_key = self.active_project_key
            
            
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
                                            'comment_body':c.body,
                                            'refresh_date':pd.to_datetime('now').replace(microsecond=0)}
            
            # set var to hold commments
            self.__comments = results
            _log.info(f'{len(self.__comments)} Comments retrieved')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__comments,orient='index')
            return df
        else:
            return self.__comments    


    def get_components(self,limit:Optional[int]=None,project_key:Optional[str]=None,return_df:bool=False,force_refresh:bool=False):
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
        if not project_key:
            project_key = self.active_project_key
            
            
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
                                            'component_name':c.name,
                                            'refresh_date':pd.to_datetime('now').replace(microsecond=0)}
            
            # set var for component storage
            self.__components = results
            _log.info(f'{len(self.__components)} Components retrieved')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__components,orient='index')
            return df
        else:
            return self.__components


    def get_labels(self,limit:Optional[int]=None,project_key:Optional[str]=None,return_df:bool=False,force_refresh:bool=False):
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
        if not project_key:
            project_key = self.active_project_key
            
            
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
                                            'label_name':l,
                                            'refresh_date':pd.to_datetime('now').replace(microsecond=0)}
                    
            # set var for storage
            self.__labels = results
            _log.info(f'{len(self.__labels)} Labels retrieved')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__labels,orient='index')
            return df
        else:
            return self.__labels


    def get_time_in_status(self,limit:Optional[int]=None,project_key:Optional[str]=None,return_df:bool=False,force_refresh:bool=False):
        """Get the time an issue is in each status and return a dictionary of those results

        Parameters:
        -----
            limit (Optional[int], optional): Number of issues to return can be limited. Default is to return All.
            project_key (Optional[str], optional): Specifiy a Project Key to pull issues from. Defaults to `'FRD'`.
            return_df (bool, optional): Option to return as Pandas Dataframe instead of dict. Defaults to `False`.
            force_refresh (bool, optional): Default is `False` - if the issues have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            dict: By default it returns a dictionary of issue keys with status dictionaries
        """
        if not project_key:
            project_key = self.active_project_key
            
            
        if force_refresh or len(self.__time_in_status) == 0:
            _log.info('Refreshing Time In Status Report...')
        
            if limit is None:

                limit = int(self.__jira.search_issues(
                            f'project = {project_key}',
                                maxResults=1,startAt=0,json_result=True)['total'])

            issues = self.get_issues(limit=limit,project_key=project_key,force_refresh=force_refresh)

            results = {}
            
            # row num is used for indexing in the result dictionary
            rownum = 0

            for issue in issues:
                for status,val in issue.time_in_status.items():
                    rownum += 1
                    results[f'{rownum}']={'issue_key':issue.key,
                                            'status':status,
                                            'days':val['days'],
                                            'hours':val['hours'],
                                            'minutes':val['minutes']}
                    
            # save to global var for reuse
            self.__time_in_status = results
            _log.info(f'{len(self.__time_in_status)} time in status records retrieved')
            
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__time_in_status,orient='index')
            return df
        else:
            return self.__time_in_status


    def get_watchers(self,limit:Optional[int]=None,project_key:Optional[str]=None,return_df:bool=False,force_refresh:bool=False):
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
        if not project_key:
            project_key = self.active_project_key
            
            
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
                                            'watcher_active':w.active,
                                            'refresh_date':pd.to_datetime('now').replace(microsecond=0)}
            
            self.__watchers = results
            _log.info(f'{len(self.__watchers)} Watchers retrieved')
        
        # determine how to return results; either dataframe | dict
        if return_df:
            df = pd.DataFrame.from_dict(self.__watchers,orient='index')
            return df
        else:
            return self.__watchers


    def export_issues_report(self,f_name:str='Issues',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
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
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        #TODO: add project key to file name as well
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        self.get_issues(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc,index=False)

        return save_loc


    def export_issue_links_report(self,f_name:str='IssueLinks',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
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
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        self.get_issue_links(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_change_history_report(self,f_name:str='ChangeHistory',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
        """Saves historic report out to excel xlsx file

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
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        self.get_histories(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_comments_report(self,f_name:str='Comments',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
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
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        self.get_comments(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_components_report(self,f_name:str='Components',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
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
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        self.get_components(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_label_report(self,f_name:str='Labels',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
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
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        self.get_labels(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_issue_count_time_series_report(self,f_name:str='IssueCountTimeSeries',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
        """[summary]

        PARAMETERS
        -----
            f_name (str, optional): File name (NO EXTENSION). Defaults to `'IssueCountTimeSeries'`.
            f_path (str, optional): File Path . Defaults to r`'.\data'`.
            limit (Optional[int], optional): Number of issues to search through, if none searches all found. Default is to return All.
            force_refresh (bool, optional): Default is `False` - if the issue counts have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.                   
        Returns:
        -----
            str: The path to where the file was saved. 
        """
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        _log.info('Refreshing Issue Count by Status Report...')
        issues = self.get_issues(limit=limit,force_refresh=force_refresh)
        status_change_records = [r for hl in [i.change_history for i in issues] for r in hl if r.field_name == 'status']
        status_set = {s:0 for s in list(set([str(c.new_value).lower() for c in status_change_records]))}
        update_dates = [datetime.strptime(c.updated_date, self.DATE_FORMAT).strftime("%Y/%m/%d") for c in status_change_records]
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        expanded_dates = pd.date_range(start=min(update_dates),end=max(update_dates),freq='D',normalize=True,closed=None)
        
        # preload dictionary in order to update the counts
        for d in expanded_dates:
            d = d.strftime("%Y/%m/%d")
            self.__status_issue_count_time_series[str(d)] = status_set.copy()

        for d in expanded_dates:
            idx_date = datetime.date(d).strftime("%Y/%m/%d")
            _log.debug(f'record - {idx_date} ')
            tmp_status = {}
            for status in status_set:
                total = sum([1 for s in status_change_records 
                             if idx_date >= s.start_date.strftime("%Y/%m/%d") 
                             and idx_date <=s.end_date.strftime("%Y/%m/%d") 
                             and s.new_value.lower() == status])
                _log.debug(f'date: {idx_date} | status: "{status}" | ttl: {total}')
                tmp_status[status] = total
                
            # after status loop set statuss to date in results dict
            self.__status_issue_count_time_series[str(idx_date)] = tmp_status
            _log.debug(f'UPDATED RECORD - {idx_date} | {self.__status_issue_count_time_series[str(idx_date)]}')
                
        _log.debug(f'Dict Time series: {self.__status_issue_count_time_series}')
                
        temp_dict = {}
        idx = 0
        
        _log.debug(f'Flattening Issue count time series')
        for d,s in self.__status_issue_count_time_series.items():
            _log.debug(f'Date: {d} | statuses: {s}')
            for k,v in s.items():
                temp_dict[idx] = {'date':d,'status':k,'total':v,'refresh_date':datetime.now()}
                idx +=1

        pd.DataFrame.from_dict(temp_dict,orient='index').to_excel(save_loc)
        return save_loc

    def export_time_in_status_report(self,f_name:str='TimeInStatus',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
        """Saves time in status report out to excel xlsx file

        Parameters:
        -----
            f_name (str, optional): File name (NO EXTENSION). Defaults to `'TimeInStatus'`.
            f_path (str, optional): File Path . Defaults to r`'.\data'`.
            limit (Optional[int], optional): Number of issues to search through, if none searches all found. Default is to return All.
            force_refresh (bool, optional): Default is `False` - if the time in status's have already been pulled, dont pull again. 
                                            If `True` - run a fresh pull.
                                            
        Returns:
        -----
            str: The path to where the file was saved. 
        """
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        self.get_time_in_status(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    def export_watchers_report(self,f_name:str='Watchers',f_path:Optional[str]=None,limit:Optional[int]=None,force_refresh:bool=False)->str:
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
        if not f_path:
            f_path = self.__config_parser['data']['report_save_location']
            
        save_loc = rf'{f_path}\{self.active_project_key + "_" + f_name}.xlsx'
        self.get_watchers(force_refresh=force_refresh,limit=limit,return_df=True).to_excel(save_loc)

        return save_loc


    # @classmethod
    # def __read_in_auth_dict(cls,path:Optional[str] = r'.\auth\auth_dict.txt')->dict:
    #     """Reads in a text file in dictionary format

    #     Parameters:
    #     -----
    #         path (Optional[str], optional): Path to auth file. Defaults to `.\\auth\\auth_dict.txt`.

    #     Raises:
    #     -----
    #         FileNotFoundError: if no auth file found in default location and no location provided

    #     Returns:
    #     -----
    #         dict: Dictionary object for use in authentication
    #     """
    #     try:
    #         f = open(path,'r')
    #         d = {}
    #         d = le(f.read())
    #     except FileNotFoundError as e:
    #         _log.error(f'Could not find Auth File in : {path}',exec_info=True)
    #         raise FileNotFoundError('No Auth file found!')
    #     finally:
    #         return d


class Jira_Issue():
    """Contains all details and functionality for a single issue

    """
    DATE_FORMAT = "%Y/%m/%d %H:%M"
    
    __authorized_jira: JIRA
    __agg_progress: int
    __agg_progress_total: int
    __assignee_name: str
    __assignee_key: str
    __comments: dict
    __comments_count: int
    __components: dict
    __created_dt: str
    __creator_key: str
    __creator_name: str
    __cur_status: str
    __epic_key: str
    __historic_records: list
    __histories: list
    __is_subtask:bool
    __issue_age_txt: str
    __issue_key: str
    __issue_links: list
    __issue_record: dict
    __issue_type: str
    __labels: dict
    __label_count: int
    __latest_comment: str
    __latest_comment_dt: str
    __open_days: int
    __priority_type:str
    __priority_descr:str
    __progress: int
    __project_key: str
    __project_name: str
    __progress_total: int
    __reporter_key: str
    __reporter_name: str
    __summary: str
    __time_in_status: dict
    __vote_count: int
    __watchers: dict
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
        self.__agg_progress = None
        self.__agg_progress_total = None
        self.__assignee_name = None
        self.__assignee_key = None
        self.__comments = {}
        self.__comments_count = None
        self.__components = {}
        self.__created_dt = None
        self.__creator_key = None
        self.__creator_name = None
        self.__cur_status = None
        self.__epic_key = None
        self.__historic_records = []
        self.__histories = []
        self.__is_subtask = False
        self.__issue_age_txt = None
        self.__issue_links = []
        self.__issue_record = {}
        self.__issue_type = None
        self.__labels = {}
        self.__label_count = None
        self.__latest_comment = None
        self.__latest_comment_dt = None
        self.__open_days = 0
        self.__priority_type = None
        self.__priority_descr = None
        self.__progress = None
        self.__project_key = None
        self.__project_name = None
        self.__progress_total = None
        self.__reporter_key = None
        self.__reporter_name = None
        self.__summary = None
        self.__time_in_status = {}
        self.__vote_count = None
        self.__watchers = {}
        self.__watcher_count = None
        self.__load_issue()


    def __load_issue(self):
        """initial load up of issue object without lists"""
        _log.debug(f'Loading Issue : {self.__issue_key}')
        
        jira = self.__authorized_jira
        issue = jira.issue(self.__issue_key,expand='changelog')
            
        try:
            self.__watchers = jira.watchers(issue).watchers
        except AttributeError:
            # Error is thrown when a field is empty.
            # Just ignore and move on, as Pandas turns it into None
            _log.debug(f'No Watchers for issue: {self.__issue_key}',exc_info=True)
        
        try:
            self.__comments = jira.comments(issue)
        except AttributeError:
            # Error is thrown when a field is empty.
            _log.debug(f'No Comments for issue: {self.__issue_key}',exc_info=True)
        
        try:
            self.__components = issue.fields.components
        except AttributeError:
            # Error is thrown when a field is empty.
            _log.debug(f'No Components for issue: {self.__issue_key}',exc_info=True)   
        
        try:
            self.__histories = issue.changelog.histories
            #_log.debug(f'issue: {self.key} | history: {self.__histories}')
        except AttributeError:
            # Error is thrown when a field is empty.
            _log.debug(f'No Changelog for issue: {self.__issue_key}',exc_info=True)
            
        try:
            _log.debug(f'Getting Issue Links for : {self.key}')
            self.__issue_links = [Issue_Link(l) for l in issue.fields.issuelinks]
        except AttributeError:
            # Error is thrown when a field is empty.
            _log.debug(f'No Issue Links for issue: {self.__issue_key}',exc_info=True)
            
        try:
            self.__labels = issue.fields.labels
        except AttributeError:
            # Error is thrown when a field is empty.
            _log.debug(f'No Labels for issue: {self.__issue_key}',exc_info=True)
            
        # start building record
        self.__issue_record['issue_key'] = self.__issue_key
        self.__issue_record['created_date'] = self.__created_dt = datetime.strptime(issue.fields.created,'%Y-%m-%dT%H:%M:%S.%f%z').date()
        self.__issue_record['agg_progress'] = self.__agg_progress = issue.fields.aggregateprogress.progress
        self.__issue_record['agg_progress_total'] = self.__agg_progress_total = issue.fields.aggregateprogress.total
        self.__issue_record['latest_comment'] = self.__latest_comment = self.clean_html(str(issue.fields.customfield_18501))

        try:
            self.__issue_record['latest_comment_date'] = self.__latest_comment_dt = datetime.strptime(issue.fields.customfield_18502,'%Y-%m-%dT%H:%M:%S.%f%z').date()
        except TypeError:
            # Error is thrown when a field is empty. So set to None
            self.__issue_record['latest_comment_date'] = self.__latest_comment_dt = None
            _log.debug(f'No Comments for issue: {self.__issue_key}',exc_info=True)
            
        self.__issue_record['epic_key'] = self.__epic_key = issue.fields.customfield_10801
        self.__issue_record['summary'] = self.__summary = issue.fields.summary
        self.__issue_record['priority_type'] = self.__priority_type = issue.fields.priority.name
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
        
        try:
            self.__issue_record['assignee_key'] = self.__assignee_key = issue.fields.assignee.key
            self.__issue_record['assignee_name'] = self.__assignee_name = issue.fields.assignee.displayName
        except AttributeError:
            # Error is thrown when a field is empty.
            _log.debug(f'No Assignee for issue: {self.__issue_key}',exc_info=True)
            
        self.__issue_record['issue_type'] = self.__issue_type = issue.fields.issuetype.name
        self.__issue_record['is_subtask'] = self.__is_subtask = issue.fields.issuetype.subtask
        self.__issue_record['watcher_count'] = self.__watcher_count = len(self.__watchers)
        self.__issue_record['comment_count'] = self.__comments_count = len(self.__comments)
        self.__issue_record['linked_issue_count'] = self.__linked_issue_count = len(self.__issue_links)
        self.__issue_record['label_count'] = self.__label_count = len(self.__labels)
        self.__issue_record['vote_count'] = self.__vote_count = issue.fields.votes.votes
        
        # set the open and close dates for open age calculation
        self.__calc_time_open()
        self.__calc_time_in_status()
    
    
    def __set_time_in_status_record(self,status:str,current_date:datetime,previous_date:datetime):
        """Sets an individual record of time in status

        PARAMETERS:
        -----
            status (str): Status value 
            current_date (datetime): The end date for date calc
            previous_date (datetime): the Start date for the date calc
        """
        # check here to build out date range for status
        time_delta = (current_date - previous_date)
        days = time_delta.days
        seconds = time_delta.seconds
        hours = seconds//3600
        minutes = (seconds//60)%60
        
        self.__time_in_status[status]['days'] += days
        self.__time_in_status[status]['hours'] += hours
        self.__time_in_status[status]['minutes'] += minutes
        
        
    def __calc_time_in_status(self):
        """Used to calculate the time spent in each status for an issue.
        """
        status_change_records = [r for r in self.change_history if r.field_name == 'status']
        status_set = {s:0 for s in list(set([str(c.new_value).lower() for c in status_change_records]))}
        prev_status = None
        prev_date = None
        status_list = []
        
        # need to get all distinct status types from History
        # to pre-fill dictionary
        #[status_list.append(x.new_value.lower()) for x in self.change_history if x.field_name.lower() == 'status' and x.new_value.lower() not in status_list]
        _log.debug(f'issue : {self.key} | status list: {status_list}')
        
        # prefill dictionary to be able to loop through and update items
        for status in status_set:
            self.__time_in_status[status] = {'days':0,
                                            'hours':0,
                                            'minutes':0,
                                            'seconds':0}
        
        #record_history = [x for x in self.change_history 
         #              if x.field_name.lower() == 'status']
        _log.debug(f'issue: {self.key} | historic rec count: {len(status_change_records)}')
        
        rec_hist_count = len(status_change_records)
        
        # use loop to calc time diff between prev and current record
        for rec in status_change_records:
            
            cur_date = datetime.strptime(rec.updated_date, self.DATE_FORMAT)
            
            if rec_hist_count == 1:
                cur_date = datetime.now()
                prev_date = datetime.strptime(rec.updated_date, self.DATE_FORMAT)
                prev_status = rec.new_value.lower()
                #self.__time_in_status[prev_status] = rec.new_value
                
            if prev_status is None:
                prev_status = rec.new_value.lower()
                prev_date = datetime.strptime(rec.updated_date, self.DATE_FORMAT)
                continue
            
            self.__set_time_in_status_record(prev_status,cur_date,prev_date)
            
            # finally put current val into prev val vars
            prev_status = rec.new_value.lower()
            prev_date = cur_date
                
        # calc last record
        if rec_hist_count >1:
            self.__set_time_in_status_record(prev_status,datetime.now(),prev_date)
        
        _log.debug(f'issue: {self.key} | status report: {self.__time_in_status}')
        
        
    def __calc_time_open(self):
        """Used to calculate the time an issue is in the "Open" status.
            Open = 'in progress','in review','needs follow up','scheduled'
        """

        # these are the status's that are considered open
        open_status = ['in progress','in review','needs follow up','scheduled']

        # holds total days in open status 
        days_open = 0
        
        # place holders for date diff calc
        start_date = None
        end_date = None
        today = datetime.today()
        
        # check to see if any closed records exist
        closed_recs = len([x.updated_date for x in self.change_history 
                       if x.field_name.lower() == 'status' 
                       and x.new_value.lower() not in open_status])
        
        # check to see if any open records exist
        open_recs = len([x.updated_date for x in self.change_history 
                     if x.field_name.lower() == 'status' 
                     and x.new_value.lower() in open_status])
        
        _log.debug(f'issue: {self.key} | open recs: {open_recs} | closed recs: {closed_recs}')
        
        # get list of dates for status changes only
        historic_records = [x for x in self.change_history 
                       if x.field_name.lower() == 'status']
        
        # need to know what the last record index of the list would be
        total_recs = closed_recs + open_recs - 1 
        
        # var to count what index the loop is on
        idx = 0
        
        # loop through the list of dates to evaluate open time segments
        for status in historic_records:
            if status.new_value.lower() in open_status:
                # it's an open status
                if start_date is None:
                    # if a start date has not been set, set it
                    start_date = datetime.strptime(status.updated_date, self.DATE_FORMAT) - timedelta(hours=4)
                    _log.debug(f'IDX: {idx} | start date: {start_date}')
                    
            else:
                # if it's not a start date then it is an end date, so set the end date
                if start_date is not None:
                    end_date = datetime.strptime(status.updated_date, self.DATE_FORMAT) - timedelta(hours=4)
                    _log.debug(f'IDX: {idx} | end date: {end_date}')
            
            # if there are both open and closed dates, then run a full date calc
            if open_recs >0 and closed_recs>0:
                # verify both dates are available to calc diff
                if end_date is not None and start_date is not None:
                    days_open += round((end_date - start_date).days)
                    _log.debug(f'IDX: {idx} | end date: {end_date} - {start_date} = {days_open}')
                    
                    # now that we have one segment calculated 
                    # we reset the dates to prep for the next segment
                    start_date = None
                    end_date = None
                    
                # if it's the last record and there is no end date yet
                elif idx == total_recs and start_date is not None:
                    
                    # calc start against todays date since the record was reopened
                    days_open += round((today - start_date).days)
                    _log.debug(f'IDX: {idx} | end date: {today} - start date: {start_date} = {days_open}')
            
            # if there are no open recs, and only a closed rec we defult it to one day
            elif open_recs == 0 and closed_recs >0:
                days_open += 1
                
                # exit loop
                break
            
            # if there are open recs but no closed recs we compare to todays date
            elif open_recs > 0 and closed_recs == 0:
                days_open += round((today - start_date).days)
                _log.debug(f'end date: {today} - start date: {start_date} = {days_open}')
                
                # exit loop since all we need is the first open date
                break
            
            # increment the index to keep up with the loop
            idx +=1 
            
        _log.debug(f'days open: {days_open}')
        self.__issue_record['open_days'] = self.__open_days = days_open
         
    
    def __update_historic_status_records(self):
        """Updates all status records in the change history with their respective
        date ranges
        """
        
        prev_date = None
        cur_date = None
        prev_status = None
        status_changes = [r for r in self.__historic_records if r.field_name == 'status']
        rec_count = len(status_changes)
        
        for r in status_changes:
            cur_date = datetime.strptime(r.updated_date, self.DATE_FORMAT)
            
            if rec_count == 1:
                cur_date = datetime.now()
                prev_date = datetime.strptime(r.updated_date, self.DATE_FORMAT)
                prev_status = r
                
            if prev_status is None:
                prev_status = r
                prev_date = datetime.strptime(r.updated_date, self.DATE_FORMAT)
                continue
        
            prev_status.set_date_range(prev_date,cur_date)
            prev_status = r
            prev_date = cur_date
        
        if rec_count > 1:
            prev_status.set_date_range(prev_date,datetime.now())
            
            
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
    def open_days(self)->int:
        return self.__open_days
    
    @property
    def change_history(self)->list:
        """List of historic changes to this issue
        Returns:
            list: Returns a list of Historic Record items
        """

        if not self.__historic_records:
            _log.debug(f'Issue: {self.key} | Change History first load')
            for rec in self.__histories:
                if hasattr(rec,'author'):
                    for item in rec.items:
                        self.__historic_records.append(Historic_Record(
                            rec.created,rec.author,item.field,item.toString,item.fromString))
            _log.debug(f'Historic record count: {len(self.__historic_records)}')
            _log.debug(f'Issue: {self.key} | Historic Records: {[x.updated_date for x in self.__historic_records]}')
            
            # get date ranges for status records
            self.__update_historic_status_records()
            
        return self.__historic_records
    
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

    @property
    def time_in_status(self)->dict:
        return self.__time_in_status
    
    
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


class Historic_Record():
    """Contains a past updated field and it's past value"""

    __update_date: datetime
    __field_name: str
    __new_value: str
    __old_value: str
    __author: str
    __issue_key: str
    __start_date: str
    __end_date: str
    
    def __init__(self,date_change:str,author:str,field_name:str,new_value:str,old_value:str):
        self.__update_date = datetime.strptime(date_change, "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y/%m/%d %H:%M")
        self.__field_name = field_name
        self.__author = author
        self.__new_value = new_value
        self.__old_value = old_value
        self.__start_date = None
        self.__end_date = None
        self.__format_values()
        
        
    def __format_values(self):
        # check the before and after values to see if they are dates;
        # if so, convert them to dates
        if 'date' in self.__field_name:
            if self.__new_value is not None:
                #self.__new_value = datetime.strptime(self.__new_value, "%Y-%m-%d %H:%M:%S.%f").strftime("%Y/%m/%d %H:%M:%S")
                self.__new_value = pd.to_datetime(self.__new_value)
            if self.__old_value is not None:
                #self.__old_value = datetime.strptime(self.__old_value, "%Y-%m-%d %H:%M:%S.%f").strftime("%Y/%m/%d %H:%M:%S")
                self.__old_value = pd.to_datetime(self.__old_value)
            
    def set_date_range(self,start:str,end:str):
        self.__start_date = start
        self.__end_date = end

        
    @property
    def issue_key(self):
        return self.__issue_key
    
    @property
    def updated_date(self)->datetime:
        return self.__update_date
    
    @property
    def start_date(self)->datetime:
        return self.__start_date
    
    @property
    def end_date(self)->datetime:
        return self.__end_date
    
    @property
    def field_name(self)->str:
        return self.__field_name
    
    @property
    def new_value(self)->str:
        return self.__new_value
    
    @property
    def old_value(self)->str:
        return self.__old_value
    
    @property
    def updated_by(self)->str:
        return self.__author
    
    
class Issue_Link():
    """contains Issue link details, like a list of issue objects, issue link type"""
    
    __id: str
    __type: str
    __inward_desc: str
    __outward_desc: str
    __inward_issue: str
    __outward_issue: str
    #__jira: JIRA
    __link_obj: dict

    def __init__(self,link_obj):
        self.__link_obj = link_obj
        self.__id = self.__link_obj.id
        self.__type = self.__link_obj.type.name
        self.__inward_desc = self.__link_obj.type.inward
        self.__outward_desc = self.__link_obj.type.outward
        
        _log.debug(f'loading issue link ID : {self.__id}')
        #have to check if there is an issue or not. if not, this attr wont exist.
        try:
            if hasattr(self.__link_obj,'inwardIssue'):
                _log.debug(f'Has Inward issue: {self.__link_obj.inwardIssue}')
                self.__inward_issue = self.__link_obj.inwardIssue
            else: self.__inward_issue = None
            
        except AttributeError:
            # Error is thrown when a field is empty.
            _log.debug(f'No inward issue for Issue: {self.__issue_key}',exc_info=True)
            
        try:    
            if hasattr(self.__link_obj,'outwardIssue'):
                _log.debug(f'Has Outward issue: {self.__link_obj.outwardIssue}')
                self.__outward_issue = self.__link_obj.outwardIssue
            else: self.__outward_issue = None
            
        except AttributeError:
            # Error is thrown when a field is empty.
            _log.debug(f'No outward issue for Issue: {self.__issue_key}',exc_info=True)
            
            
    @property
    def link_id(self)->str:
        """Issue Link id"""
        return self.__id

    @property
    def link_type(self)->str:
        """Type of Link"""
        return self.__type

    @property
    def inward_issue(self)->str:
        """Issue that is 'Parent'"""
        return self.__inward_issue

    @property
    def outward_issue(self)->str:
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