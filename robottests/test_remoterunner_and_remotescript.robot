# Copyright (C) 2019, Nokia

*** Settings ***

Library    Process
Library    crl.interactivesessions.remoterunner.RemoteRunner
...        WITH NAME    RemoteRunner
Library    crl.remotescript.RemoteScript    WITH NAME    RemoteScript

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
    FOR    ${target}     IN    target1    target2
        RemoteRunner.Execute Command In Target    rm -rf /tmp/runner /tmp/script
        ...    target=${target}
    END

Remove Files In Target
    [Arguments]  ${target}  ${file}  ${dir}
    RemoteRunner.Execute Command In Target    rm ${file} ${dir}  target=${target}

Remove Files Locally And In Target
    Run Process  rm  targetlocal  remoterunnerfile  remotescriptfile
    Remove Files In Target  target1  targetlocal  .
    Remove Files In Target  target2  targetlocal  .


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
    Run Keyword If   'port' in ${HOST1}
    ...    RemoteScript.Set Target Property    target1    port    ${HOST1['port']}
    RemoteScript.Set Target    host=${HOST2['host']}
    ...                        username=${HOST2['user']}
    ...                        password=${HOST2['password']}
    ...                        name=target2
    Run Keyword If   'port' in ${HOST2}
    ...    RemoteScript.Set Target Property    target2    port    ${HOST2['port']}


Compare Results
    [Arguments]    ${result1}    ${result2}
    Should Be True
        ...    '${result1.status}' == '${result2.status}' or '${result2.status}' == 'unknown'
        Should Be Equal    ${result1.stdout}    ${result2.stdout}
        Should Be Equal    ${result1.stderr}    ${result2.stderr}


Compare Execute Command In Target
    [Arguments]    ${target}
    ${runner}=    RemoteRunner.Execute Command In Target    echo out;>&2 echo err
    ...    ${target}    1
    ${script}=    RemoteScript.Execute Command In Target    echo out;>&2 echo err
    ...    ${target}    1
    Compare Results    ${runner}    ${script}

Compare Copy Directory To Target
    [Arguments]    ${target}
    Run Process    mkdir -p tmp && cp * tmp/    shell=${True}
    ${runner}=     RemoteRunner.Copy Directory To Target
    ...    tmp/
    ...    /tmp/runner/
    ...    0744
    ...    ${target}
    ${res}=     RemoteScript.Execute Command In Target  ls /tmp/runner/
    ...     ${target}   1
    Should Be Equal     ${res.status}    0   ${res}
    # Exact feature parity with RemoteScript with this setup cannot be tested
    [Teardown]    RemoteRunner.Execute Command In Target
    ...           target=${target}
    ...           command=rm -rf /tmp/runner

Compare Create Directory In Target
    [Arguments]    ${target}
    ${runner}=    RemoteRunner.Create Directory In Target
    ...    /tmp/runnercreate/
    ...    0444
    ...   ${target}

    ${script}=    RemoteScript.Create Directory In Target
    ...    /tmp/scriptcreate
    ...    0444
    ...   ${target}
    #   ${diff}=    RemoteRunner.Execute Command In Target
    #   ...    diff -r /tmp/runnercreate/ /tmp/scriptcreate/    ${target}
    #   Should Be Equal    ${diff.status}    0
    ${result}=    RemoteRunner.Execute Command In Target
    ...  ls /tmp/runnercreate/    target=${target}
    Should Be Equal    ${result.status}    0  ${result.stderr}
    #TODO: https://github.com/nokia/crl-remotescript/issues/8
    # Compare Results    ${runner}    ${script}
    [Teardown]    RemoteRunner.Execute Command In Target
    ...    rm -rf /tmp/runnercreate /tmp/scriptcreate   target=${target}

Compare Execute Background Command In Target
    [Arguments]    ${target}
    FOR    ${i}    IN RANGE    2
        RemoteRunner.Execute Background Command In Target
         ...    echo out;>&2 echo err;sleep 10
         ...    ${target}
         ...    test
         Sleep    1
         RemoteRunner.Kill Background Execution    test
         ${runner}=    RemoteRunner.Wait Background Execution    test
         Should Be Equal    ${runner.status}    -15
         Should Be Equal    ${runner.stdout}    out
         Should Be Equal    ${runner.stderr}    err
        #RemoteScript.Execute Background Command In Target
        # ...    echo out;>&2 echo err;sleep 10
        # ...    ${target}
        # ...    test
        # Sleep    1
        # RemoteScript.Kill Background Execution    test
        # ${script}=    RemoteScript.Wait Background Execution    test
        # #Should Be Equal    ${runner.status}    -15
        # #Should Be Equal    ${runner.stdout}    out
        # #Should Be Equal    ${runner.stderr}    err
        # Log  ${script.status}
        # Log  ${script.stdout}
        # Log  ${script.stderr}
    END
    # No comparison with the RemoteScript can be done because there is a bugs
    # in the RemotScript background execution functionality Using instead
    # comparison with results which RemoteScript should ideally return
    # See https://github.com/nokia/crl-remotescript/issues/11

Compare File Copying
    Create Random File
    [Arguments]  ${target1}  ${target2}
    ${runner1}=    RemoteRunner.Copy File To Target
    ...    targetlocal
    ...    .
    ...    0755
    ...    ${target1}
    ${runner2}=    RemoteRunner.Copy File Between Targets
    ...     ${target1}
    ...     targetlocal
    ...     ${target2}
    ...     .
    ...     0755

    ${runner3}=    RemoteRunner.Copy File From Target
    ...    targetlocal
    ...    remoterunnerfile
    ...    target=${target2}
    filehelper.diff files    targetlocal    remoterunnerfile

    ${script1}=    RemoteScript.Copy File To Target
    ...    targetlocal
    ...    .
    ...    0755
    ...    ${target1}

    ${script2}=    RemoteScript.Copy File Between Targets
    ...     ${target1}
    ...     targetlocal
    ...     ${target2}
    ...     .
    ...     0755

    ${script3}=    RemoteScript.Copy File From Target
    ...    targetlocal
    ...    remotescriptfile
    ...    target=${target2}
    filehelper.diff files    targetlocal    remotescriptfile
    Compare Results    ${runner1}    ${script1}
    Compare Results    ${runner2}    ${script2}
    Compare Results    ${runner3}    ${script3}
    [Teardown]  Remove Files Locally And In Target

*** Test Cases ***
Template Compare File Copying
    [Template]  Compare File Copying
    target1  target2
    target2  target1

Template Compare Execute Command In Target
    [Template]  Compare Execute Command In Target
    target1
    target2

Template Compare Copy Directory To Target
    [Template]  Compare Copy Directory To Target
    target1
    target2

Template Compare Create Directory In Target
    [Template]  Compare Create Directory In Target
    target1
    target2

Template Compare Execute Background Command In Target
    [Template]  Compare Execute Background Command In Target
    target1
    target2
