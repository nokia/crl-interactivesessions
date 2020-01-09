# Copyright (C) 2019, Nokia

*** Settings ***
Library    ClusterExec.py

Test Setup    Initialize Library
Test Teardown    ClusterExec.Close
Force Tags     selfrepairingsession

*** Keywords ***
Initialize Library
    ClusterExec.Set Host    ${GW}
    ClusterExec.Add Node    ${HOST1_VIA_GW}
    ClusterExec.Add Node    ${HOST2_VIA_GW}
    ClusterExec.Initialize Executor

*** Test Cases ***
Command execution in python 2 node
    ${status}  ${stdout}  ${stderr}=    ClusterExec.Run Cmd In Node
    ...   ${HOST1_VIA_GW.host}    whoami
    Should Be Equal As Strings   ${status}    0
    Should Be Equal   ${stdout}    root

Command execution in python 3 node
    ${status}  ${stdout}  ${stderr}=    ClusterExec.Run Cmd In Node
    ...   ${HOST2_VIA_GW.host}    whoami
    Should Be Equal As Strings   ${status}    0
    Should Be Equal   ${stdout}    root
