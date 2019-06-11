# Copyright (C) 2019, Nokia

*** Settings ***
Library    crl.interactivesessions.remoterunner.RemoteRunner    WITH NAME    RemoteRunner
Test Setup   Set RemoteRunner Targets
*** Variables ***

&{HOST1}=    host=example1.com
...          user=username1
...          password=password1

@{SHELLDICTS1}=     ${HOST1}

*** Keywords ***
Set RemoteRunner Targets

    RemoteRunner.Set Target    shelldicts=${SHELLDICTS1}
    ...                        name=target1

*** Test Cases ***
Test Create Directory In Target
    ${script}=    RemoteRunner.Create Directory In Target
    ...    /tmp/scriptcreate
    ...    0444
    ...   target1
    ${result}=    RemoteRunner.Execute Command In Target
    ...    ls /tmp/scriptcreate/    target1
    Should Be Equal    ${result.status}    0  ${result.stderr}
