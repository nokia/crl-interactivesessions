# Copyright (C) 2019, Nokia

*** Settings ***
Library    crl.interactivesessions.remoterunner.RemoteRunner
...        WITH NAME    RemoteRunner
Suite Teardown    RemoteRunner.Close
Test Setup    Set RemoteRunner Targets

*** Variables ***
@{TARGET}=    ${HOST1}
@{SUDOTARGET}=    ${HOST1}    ${SUDOSHELL}

*** Keywords ***

Set RemoteRunner Targets
    RemoteRunner.Set Target    shelldicts=${TARGET}
    RemoteRunner.Set Target    shelldicts=${SUDOTARGET}    name=sudo
    RemoteRunner.Execute Command In Target    echo hello

*** Test Cases ***

Test Broadcast Messages
    [Teardown]     RemoteRunner.Kill Background Execution    background
    RemoteRunner.Execute Background Command In Target
    ...     for ((i=0; ;i++)) do for f in /dev/pts/*; do echo -n message.$f.$i > $f;sleep 0.01; done; done
    ...     target=sudo
    FOR    ${i}    IN RANGE    10
        ${result}=    RemoteRunner.Execute Command In Target    echo hello
        Should Be Equal    ${result.stdout}    hello  ${result.stdout}
    END
