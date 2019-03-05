# Copyright (C) 2019, Nokia

*** Settings ***

Library    crl.interactivesessions.remoterunner.RemoteRunner
...        WITH NAME    RemoteRunner

Library    filehelper.py
Library    SessionBroker.py

Suite Setup    Create Random File
Test Setup    Set RemoteRunner Targets
Suite Teardown    RemoteRunner.Close
Force Tags     remoterunner

*** Variables ***

&{HOST1}=    host=example1.com
...          user=username1
...          password=password1

&{HOST2}=    host=example2.com
...          user=username2
...          password=password2

@{SHELLDICTS1}=    ${HOST1}
@{SHELLDICTS2}=    ${HOST1}    ${HOST2}

${REPEAT}    20

${COMMAND}    echo out;>&2 echo err

*** Keywords ***

Set RemoteRunner Targets
    RemoteRunner.Set Target    shelldicts=${SHELLDICTS1}
    ...                        name=target1

    RemoteRunner.Set Target    shelldicts=${SHELLDICTS2}
    ...                        name=target2

Create Random File
    filehelper.Create Random File    targetlocal    100000


Verify Run
    [Arguments]   ${ret}    ${expected_status}
    Should Be Equal As Integers    ${ret.status}    ${expected_status}
    Should Be Equal   ${ret.stdout}    out
    Should Be Equal   ${ret.stderr}    err

*** Test Cases ***

Test File Copying
    : FOR    ${INDEX}   IN RANGE   ${REPEAT}

    \    RemoteRunner.Copy File To Target    targetlocal    target=target1
    \    RemoteRunner.Copy File Between Targets
         ...     from_target=target1
         ...     source_file=targetlocal
         ...     to_target=target2

    \    RemoteRunner.Copy File From Target
         ...    targetlocal
         ...    remotefile
         ...    target=target2
    \    filehelper.diff files    targetlocal    remotefile

Test Execute Background Commands
    RemoteRunner.Execute Background Command In Target
    ...   ${COMMAND}; sleep 10    target=target1    exec_id=test
    ${ret}=    RemoteRunner.Kill Background Execution   test
    Verify Run   ${ret}    -15
    ${ret_from_wait}=    Remoterunner.Wait Background Execution
    ...    test   t=1
    Should Be Equal    ${ret_from_wait}    ${ret}

Test Execute Command In Target
    ${ret}=    RemoteRunner.Execute Command In Target
    ...    ${COMMAND}    target=target2
    Verify Run    ${ret}    0

Test Execute Command In Target With Sudo
    [Tags]     skip
    ${ret}=    RemoteRunner.Execute Command In Target
    ...    sudo echo out;sudo >2 echo err    target=target2
    Verify Run    ${ret}    0

Test Tty
     ${ret}=    RemoteRunner.Execute Command In Target
    ...    for fd in 0 1 2; do if [ -t $fd ] ;then echo $fd is connected to terminal; fi; done
    ...    target=target2

Test Tty2
     ${ret}=    RemoteRunner.Execute Command In Target
    ...    tty -s
    ...    target=target2

Test Break Sessions Before Execute Command In Target
    RemoteRunner.Set Target Property    target1    prompt_timeout    1
    : FOR    ${INDEX}    IN RANGE    2
    \    SessionBroker.Break Sessions
    \    ${ret}=    RemoteRunner.Execute Command In Target    ${COMMAND}
         ...    target=target1
    \    Verify Run    ${ret}    0

Test Hang Sessions Before Execute Command In Target
    RemoteRunner.Set Target Property    target1    prompt_timeout    1
    : FOR    ${INDEX}    IN RANGE    2
    \    SessionBroker.Hang Sessions
    \    ${ret}=    RemoteRunner.Execute Command In Target    ${COMMAND}
         ...    target=target1
    \    Verify Run    ${ret}    0


Test Get Proxy From Call
    ${term}=    RemoteRunner.Get Terminal    target1
    RemoteRunner.Import Local Path Module In Terminal
    ...    ${term}   ${CURDIR}/proxytest.py
    ${testproxy}=    RemoteRunner.Get Proxy From Call In Terminal  ${term}
    ...    proxytest.ProxyTest   1
    ${ret}=    Call Method    ${testproxy}   test   0
    Should Be Equal   ${ret.testid}    1
    Should Be Equal   ${ret.status}    0


Test Get Proxy Object
    ${term}=    RemoteRunner.Get Terminal    target1
    ${osproxy}=    RemoteRunner.Get Proxy Object In Terminal    ${term}   os
    ${os}=   Get Variable Value   ${osproxy.uname()[0]}
    Should Be Equal   ${os}    Linux
