# -*- coding: utf-8 -*-
# Name: jira_data_pull.py
# Create by: Cody Hughes
# created date: 08/11/2021
# Description:
#   This is a starting point for using the iJira interface. Currently this is more of a test area until a more formal 
# and detailed solution is developed.

from iJira import iJira
import logging
import sys


#setup logger
def run():
    """ Sets up logger app.

    """
    # set up logger here then use throughout modules
    format_str = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s: %(lineno)s - %(message)s'
    formatter = logging.Formatter(format_str)
    file_handler = logging.FileHandler(filename=r'./logs/logfile.log',mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    handlers = [file_handler,console_handler]
    logging.basicConfig(level = logging.DEBUG,
                                    handlers = handlers,
                                    format = format_str)
    
    logging.getLogger(__name__).info('Logger Setup and Ready')
    
    
if __name__ == '__main__':
    run()
    save_loc = r'\\fema.net\hqss\OPPASHARE\Enterprise Analytics Division\DashboardProjects\TableauDataSources\Jira_FRD'
    #save_loc = r'\\hqli2f8\hqshare\Office of Policy and Program Analysis (OPPA)\Enterprise Analytics Division\DashboardProjects\TableauDataSources\Jira_FRD'
    # perform auth to activate connection to api
    japi = iJira(r'.\auth\oauth.pem')
    
    # issues report
    #print(japi.get_issues(limit=20,return_df=True))
    japi.export_issues_report(f_path=save_loc)

    # change history report
    japi.export_change_history_report(f_path=save_loc)
    #print(japi.get_histories(limit=2,return_df=True))
    
    # components report
    japi.export_components_report(f_path=save_loc)

    # labels report
    japi.export_label_report(f_path=save_loc)

    # comments report
    japi.export_comments_report(f_path=save_loc)

    # linked issues / this might also be subtasks
    japi.export_issue_links_report(f_path=save_loc)
    
    # watchers report
    japi.export_watchers_report(f_path=save_loc)

    # time in status report
    #print(japi.get_time_in_status(limit=20))
    japi.export_time_in_status_report(f_path=save_loc)
    
    # status issue count time series report
    japi.export_issue_count_time_series_report(f_path=save_loc)