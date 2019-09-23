# Copyright (C) 2019, Nokia

*** Settings ***

Library    Process
Library    crl.interactivesessions.remoterunner.RemoteRunner
...        WITH NAME    RemoteRunner
Library    crl.interactivesessions._terminalpools._TerminalPools
...        WITH NAME    Pools

Library    filehelper.py
Library    SessionBroker.py
Library    Collections


Suite Setup    Create Random File
Test Setup    Set RemoteRunner Targets
Suite Teardown    RemoteRunner.Close
Force Tags     remoterunner

*** Variables ***

&{DEFAULT_PROPERTIES}=  default_executable=/bin/bash
...                     max_processes_in_target=${100}
...                     prompt_timeout=${30}
...                     termination_timeout=${10}
...                     update_env_dict=&{EMPTY}


@{SHELLDICTS1}=    ${HOST1}
@{SHELLDICTS2}=    ${GW}    ${HOST2_VIA_GW}

${REPEAT}    20

${COMMAND}    echo out;>&2 echo err

${TEST_VALUE}=  ${None}
@{TARGETS}=  target1  target2

*** Keywords ***

Get Pools Maxsize
    ${pool_obj}=     Get Library Instance  Pools
    [Return]    ${pool_obj.maxsize}

Remove Filepath In Target
    [Arguments]  ${target}  ${path}
    RemoteRunner.Execute Command In Target    rm ${path}  target=${target}

Remove Files Locally And In Target
    Run Process  rm  targetlocal  remotescriptfile
    Remove Filepath In Target  target1  ./targetlocal
    Remove Filepath In Target  target2  ./targetlocal

Remove Directory In Target
    [Arguments]     ${target}   ${dir}
    RemoteRunner.Execute Command In Target  rm -rf ${dir}   target=${target}

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

Test Execute Nohup Background In Target
    [Arguments]  ${target}
    ${pid}=         Execute Nohup Background In Target
    ...             command=echo foo;echo bar >&2;sleep 4
    ...             target=${target}
    ${ret}=         Execute Command In Target
    ...             command=kill ${pid}
    ...             target=${target}
    Should Be Equal As Integers     ${ret.status}   0   ${ret}

Test Execute Command In Target
    [Arguments]  ${target}
    ${ret}=    RemoteRunner.Execute Command In Target
    ...    ${COMMAND}    target=${target}
    Verify Run    ${ret}    0

Test Execute Background Commands
    [Arguments]  ${target}
    RemoteRunner.Execute Background Command In Target
    ...   ${COMMAND}; sleep 10    target=${target}    exec_id=${target}
    ${ret}=    RemoteRunner.Kill Background Execution   ${target}
    Verify Run   ${ret}    -15
    ${ret_from_wait}=    Remoterunner.Wait Background Execution
    ...    ${target}   t=1
    Should Be Equal    ${ret_from_wait}    ${ret}

Test File Copying
    [Arguments]  ${target1}  ${target2}
    Create Random File
    FOR    ${INDEX}   IN RANGE   ${REPEAT}
        RemoteRunner.Copy File To Target    targetlocal    target=${target1}
        RemoteRunner.Copy File Between Targets
         ...     from_target=${target1}
         ...     source_file=targetlocal
         ...     to_target=${target2}
        RemoteRunner.Copy File From Target
         ...    targetlocal
         ...    remotefile
         ...    target=${target2}
        filehelper.diff files    targetlocal    remotefile
   END
   [Teardown]  Remove Files Locally And In Target

Test Break Sessions Before Execute Command In Target
    [Arguments]  ${target}
    RemoteRunner.Set Target Property    ${target}    prompt_timeout    1
     FOR    ${INDEX}    IN RANGE    2
        SessionBroker.Break Sessions
        ${ret}=    RemoteRunner.Execute Command In Target    ${COMMAND}
        ...    target=${target}
        Verify Run    ${ret}    0
     END

Test Hang Sessions Before Execute Command In Target
    [Arguments]  ${target}
    RemoteRunner.Set Target Property    ${target}    prompt_timeout    1
     FOR    ${INDEX}    IN RANGE    2
        SessionBroker.Hang Sessions
        ${ret}=    RemoteRunner.Execute Command In Target    ${COMMAND}
        ...    target=${target}
        Verify Run    ${ret}    0
     END

Test Get Proxy From Call
    [Arguments]  ${target}
    ${term}=    RemoteRunner.Get Terminal    ${target}
    RemoteRunner.Import Local Path Module In Terminal
    ...    ${term}   ${CURDIR}/proxytest.py
    ${testproxy}=    RemoteRunner.Get Proxy From Call In Terminal  ${term}
    ...    proxytest.ProxyTest   1
    ${ret}=    Call Method    ${testproxy}   test   0
    Should Be Equal   ${ret.testid}    1
    Should Be Equal   ${ret.status}    0

Test Get Proxy Object
    [Arguments]  ${target}  ${username}
    ${term}=    RemoteRunner.Get Terminal    ${target}
    ${osproxy}=    RemoteRunner.Get Proxy Object In Terminal    ${term}   os
    Log  ${osproxy}
    ${os}=   Get Variable Value   ${osproxy.getlogin()}
    Should Be Equal   ${os}    ${username}   ${os}


Check That Targets Have Original Values
    RemoteRunner.Set Target    shelldicts=${SHELLDICTS1}
    ...                        name=target1
    RemoteRunner.Set Target    shelldicts=${SHELLDICTS2}
    ...                        name=target2
    FOR     ${i}   IN  target1  target2
        ${check_default_properties}=  Get Target Properties  target=${i}
        Check Property Equalities
        ...     orig_properties=${DEFAULT_PROPERTIES}
        ...     properties=${check_default_properties}
    END


Check Value Equals All List Values
    [Arguments]  ${value}  ${value_list}
    FOR     ${value_in_list}  IN  @{value_list}
        Should Be Equal     ${value_in_list}    ${value}   ${value_in_list}
    END


Set All Default Target Properties
    [Arguments]  ${new_value}  ${keys}
    FOR  ${key}    IN    @{keys}
        RemoteRunner.Set Default Target Property
        ...     property_name=${key}
        ...     property_value=${new_value}
    END


Reset All Default Target Properties
    [Arguments]  ${default_keys}
    FOR  ${key}  IN  @{default_keys}
        ${value}=   Get From Dictionary
        ...         dictionary=${DEFAULT_PROPERTIES}
        ...         key=${key}
        RemoteRunner.Set Default Target Property
        ...     property_name=${key}
        ...     property_value=${value}
    END


Check Property Equalities
    [Arguments]  ${orig_properties}  ${properties}
    Dictionary Should Contain Sub Dictionary
    ...     dict1=${properties}
    ...     dict2=${orig_properties}


Set All Target Properties
    [Arguments]  ${target}  ${new_value}  ${keys}
    FOR  ${key}    IN    @{keys}
        RemoteRunner.Set Target Property
        ...     target_name=${target}
        ...     property_name=${key}
        ...     property_value=${new_value}
    END


Test Set Target Property
    [Arguments]  ${target}
    ${default_keys}=    Get Dictionary Keys  dictionary=${DEFAULT_PROPERTIES}
    ${old_properties}=  RemoteRunner.Get Target Properties  target=${target}
    Set All Target Properties
    ...     target=${target}
    ...     new_value=${TEST_VALUE}
    ...     keys=${default_keys}
    ${new_properties}=  RemoteRunner.Get Target Properties  target=${target}
    ${new_values}=  Get Dictionary Values  dictionary=${new_properties}
    Check Value Equals All List Values
    ...    value=${TEST_VALUE}
    ...    value_list=${new_values}


Run Background Command In Both Targets
    FOR  ${target}  IN  @{TARGETS}
        RemoteRunner.Execute Background Command In Target
        ...     command=${COMMAND}
        ...     target=${target}
        ...     exec_id=${target}
    END

Set Terminalpools Maxsize And Kill Background Commands
    [Arguments]     ${old_maxsize}
    RemoteRunner.Set Terminalpools Maxsize  maxsize=${old_maxsize}
    FOR  ${target}   IN  @{TARGETS}
        Run Keyword And Ignore Error
        ...   Wait Background Execution  exec_id=${target}
    END
    RemoteRunner.Close
    Set Remoterunner Targets

Test Set Terminalpools Maxsize And Expect Failure
    [Arguments]     ${new_maxsize}
    ${POOL_MAXSIZE}=  Get Pools Maxsize
    RemoteRunner.Close
    Set Remoterunner Targets
    RemoteRunner.Set Terminalpools Maxsize  maxsize=${new_maxsize}
    Run Keyword And Expect Error
    ...     TerminalPoolsBusy*
    ...     Run Background Command In Both Targets
    [Teardown]  Set Terminalpools Maxsize And Kill Background Commands
    ...         old_maxsize=${POOL_MAXSIZE}

Test Execute Command In Target Progress Log True
    [Arguments]  ${target}
    Execute Command In Target
    ...     command=echo hello;echo world!>&2
    ...     target=${target}
    ...     timeout=3
    ...     progress_log=${True}

*** Test Cases ***
Template Test Set Terminalpools Maxsize And Expect Failure
    [Template]  Test Set Terminalpools Maxsize And Expect Failure
    0
    1

Test Set Default Target Property
    ${default_keys}=    Get Dictionary Keys  dictionary=${DEFAULT_PROPERTIES}
    Set All Default Target Properties
    ...     new_value=${TEST_VALUE}
    ...     keys=${default_keys}
    FOR  ${target}   IN  @{Targets}
        Set Target  shelldicts=${SHELLDICTS1}
        ...                 name=${target}
        ${properties}=   RemoteRunner.Get Target Properties  target=${target}
        ${prop_values}=     Get Dictionary Values  dictionary=${properties}
        Check Value Equals All List Values
        ...     value=${TEST_VALUE}
        ...     value_list=${prop_values}
    END
    Reset All Default Target Properties
    ...     default_keys=${default_keys}
    [Teardown]  Check That Targets Have Original Values

Template Test Execute Command In Target Progress Log True
    [Template]  Test Execute Command In Target Progress Log True
    target1
    target2

Template Test Execute Command In Target
    [Template]  Test Execute Command In Target
    target1
    target2

Template Test Execute Background Commands
    [Template]  Test Execute Background Commands
    target1
    target2

Template Test File Copying
    [Template]  Test File Copying
    target1  target2
    target2  target1

Template Test Break Sessions Before Execute Command In Target
    [Template]  Test Break Sessions Before Execute Command In Target
    target1
    target2

Template Test Hang Sessions Before Execute Command In Target
    [Template]  Test Hang Sessions Before Execute Command In Target
    target1
    target2

Template Test Get Proxy From Call
    [Template]  Test Get Proxy From Call
    target1
    target2

Template Test Get Proxy Object
    [Template]  Test Get Proxy Object
    target1  ${HOST1.user}
    target2  ${HOST2.user}
   [Teardown]  RemoteRunner.Close

Template Test Execute Nohup Background In Target
    [Template]  Test Execute Nohup Background In Target
    target1
    target2

Templated Test Set Target Property
    [Template]  Test Set Target Property
    target1
    target2
