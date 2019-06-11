# Copyright (C) 2019, Nokia

*** Settings ***
Library    crl.remotescript.RemoteScript    WITH NAME    RemoteScript
Test Setup   Set RemoteScript Targets 

*** Keywords ***
Set RemoteScript Targets
    
    RemoteScript.Set Target    host=localhost
    ...                        username=python2user
    ...                        password=python2testing
    ...                        name=target1
    
*** Test Cases ***
Test Create Directory In Target
    ${script}=    RemoteScript.Create Directory In Target
    ...    /tmp/scriptcreate
    ...    0444
    ...   target1
    ${result}=    RemoteScript.Execute Command In Target
    ...    ls /tmp/scriptcreate/    target1
    Should Be Equal    ${result.status}    0  ${result.stderr}
