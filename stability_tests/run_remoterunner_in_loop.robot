# Copyright (C) 2019, Nokia

*** Settings ***

Library   crl.interactivesessions.remoterunner.RemoteRunner   WITH NAME    RemoteRunner

Test Setup   Setup RemoteRunner
Suite TearDown    RemoteRunner.Close

*** Variables ***

&{BASHSHELL}=   shellname=BashShell
@{SHELLDICTS}=   ${BASHSHELL}
${ITERATIONS}=  100000

*** Keywords ***

Setup RemoteRunner
    RemoteRunner.Set Target    ${SHELLDICTS}

*** Test Cases ***

Run RemoteRunner In Loop
    :FOR    ${index}    IN RANGE    ${ITERATIONS}
    \    RemoteRunner.Execute Command In Target    echo hello
