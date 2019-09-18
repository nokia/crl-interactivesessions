# Copyright (C) 2019, Nokia

*** Settings ***
Library    ClusterExec.py


Test Setup    Initialize Library
Test Teardown    ClusterExec.Close
Force Tags     selfrepairingsession

*** Variables ***
&{HOST1}=    host=example1.com
...          user=username1
...          password=password1

&{HOST2}=    host=example2.com
...          user=username2
...          password=password2

*** Keywords ***
Initialize Library
    ClusterExec.Set Host    ${HOST1}
    ClusterExec.Add Node    python2host  ${HOST1}
    ClusterExec.Add Node    python3host  ${HOST2}
    ClusterExec.Initialize Executor

*** Test Cases ***
Command execution in python 2 node
    ${status}  ${stdout}  ${stderr}=    ClusterExec.Run Cmd In Node    python2host    whoami
    Should Be Equal As Strings   ${status}    0
    Should Be Equal   ${stdout}    python2user

Command execution in python 3 node
    ${status}  ${stdout}  ${stderr}=    ClusterExec.Run Cmd In Node    python3host    whoami
    Should Be Equal As Strings   ${status}    0
    Should Be Equal   ${stdout}    python3user

