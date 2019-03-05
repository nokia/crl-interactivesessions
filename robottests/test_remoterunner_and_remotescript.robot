# Copyright (C) 2019, Nokia

*** Settings ***

Library    Process
Library    crl.interactivesessions.remoterunner.RemoteRunner
...        WITH NAME    RemoteRunner
Library    cloudtaf.remotescript.RemoteScript    WITH NAME    RemoteScript

Library    filehelper.py

Suite Setup    Create Random File
Suite Teardown    RemoteRunner.Close
Test Setup    Remote Test Setup
Force Tags     remotecompare

*** Variables ***

@{SHELLDICTS1}=    ${HOST1}
@{SHELLDICTS2}=    ${HOST2}

${TESTFILESIZE}=    1000000

*** Keywords ***
Remote Test Setup
    Set Targets
    Remove Tmp Directories

Remove Tmp Directories
    :FOR    ${target}     IN    target1    target2
    \    RemoteRunner.Execute Command In Target    rm -rf /tmp/runner /tmp/script
    \    ...    target=${target}

Create Random File
    filehelper.Create Random File    targetlocal    ${TESTFILESIZE}

Set Targets
    Set RemoteScript Targets
    Set RemoteRunner Targets

Set RemoteRunner Targets
    RemoteRunner.Set Target    shelldicts=${SHELLDICTS1}
    ...                        name=target1

    RemoteRunner.Set Target    shelldicts=${SHELLDICTS2}
    ...                        name=target2

Set RemoteScript Targets
    RemoteScript.Set Target    host=${HOST1['host']}
    ...                        username=${HOST1['user']}
    ...                        password=${HOST1['password']}
    ...                        name=target1

    RemoteScript.Set Target    host=${HOST2['host']}
    ...                        username=${HOST2['user']}
    ...                        password=${HOST2['password']}
    ...                        name=target2



*** Keywords ***

Compare Results
    [Arguments]    ${result1}    ${result2}
    Should Be True
        ...    '${result1.status}' == '${result2.status}' or '${result2.status}' == 'unknown'
        Should Be Equal    ${result1.stdout}    ${result2.stdout}
        Should Be Equal    ${result1.stderr}    ${result2.stderr}


*** Test Cases ***

Compare File Copying
    ${runner1}=    RemoteRunner.Copy File To Target
    ...    targetlocal
    ...    .
    ...    0755
    ...    target1
    ${runner2}=    RemoteRunner.Copy File Between Targets
    ...     target1
    ...     targetlocal
    ...     target2
    ...     .
    ...     0755

    ${runner3}=    RemoteRunner.Copy File From Target
    ...    targetlocal
    ...    remoterunnerfile
    ...    target=target2
    filehelper.diff files    targetlocal    remoterunnerfile

    ${script1}=    RemoteScript.Copy File To Target
    ...    targetlocal
    ...    .
    ...    0755
    ...    target1

    ${script2}=    RemoteScript.Copy File Between Targets
    ...     target1
    ...     targetlocal
    ...     target2
    ...     .
    ...     0755

    ${script3}=    RemoteScript.Copy File From Target
    ...    targetlocal
    ...    remotescriptfile
    ...    target=target2
    filehelper.diff files    targetlocal    remotescriptfile
    Compare Results    ${runner1}    ${script1}
    Compare Results    ${runner2}    ${script2}
    Compare Results    ${runner3}    ${script3}

Compare Execute Command In Target
    ${runner}=    RemoteRunner.Execute Command In Target    echo out;>&2 echo err
    ...    target1    1
    ${script}=    RemoteScript.Execute Command In Target    echo out;>&2 echo err
    ...    target1    1
    Compare Results    ${runner}    ${script}


Compare Copy Directory To Target
    Run Process    mkdir -p tmp && cp * tmp/    shell=${True}
    ${runner}=     RemoteRunner.Copy Directory To Target
    ...    tmp/
    ...    /tmp/runner/
    ...    0744
    ...    target1
    # Exact feature parity with RemoteScript with this setup cannot be tested

Compare Create Directory In Target
    ${runner}=    RemoteRunner.Create Directory In Target
    ...    /tmp/runnercreate/
    ...    0444
    ...   target1

    ${script}=    RemoteScript.Create Directory In Target
    ...    /tmp/scriptcreate
    ...    0444
    ...   target1
    ${diff}=    RemoteRunner.Execute Command In Target
    ...    diff -r /tmp/runnercreate/ /tmp/scriptcreate/    target1
    Should Be Equal    ${diff.status}    0
    Compare Results    ${runner}    ${script}


Compare Execute Background Command In Target
    :FOR    ${i}    IN RANGE    2
    \    RemoteRunner.Execute Background Command In Target
    	 ...    echo out;>&2 echo err;sleep 10
    	 ...    target1
    	 ...    test
    \    Sleep    1
    \	 RemoteRunner.Kill Background Execution    test
    \	 ${runner}=    RemoteRunner.Wait Background Execution    test

    # No comparison with the RemoteScript can be done because there is a bugs
    # in the RemotScript background execution functionality Using instead
    # comparison with results which RemoteScript should ideally return

    Should Be Equal    ${runner.status}    -15
    Should Be Equal    ${runner.stdout}    out
    Should Be Equal    ${runner.stderr}    err
