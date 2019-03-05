# Copyright (C) 2019, Nokia

*** Settings ***

Library    crl.interactivesessions.runnerterminal.RunnerTerminal
...   WITH NAME    terminal

Library    crl.interactivesessions.autorunnerterminal.AutoRunnerTerminal
...   WITH NAME    autoterminal


Library    crl.interactivesessions.autorecoveringterminal.AutoRecoveringTerminal
...   WITH NAME    AutoRecoveringTerminal

Library    crl.interactivesessions.InteractiveSession.BashShell
...   WITH NAME    BashShell

Library    TestSession.py

Test Teardown    Close Terminal

*** Keywords ***

Close Terminal
    terminal.Close

Setup TestSession terminal
    ${session}=    Get Library Instance    TestSession
    terminal.initialize    session=${session}

Setup AutoRecoveringTerminal terminal
    ${terminal}=    Get Library Instance    terminal
    ${bashshell}    Get Library Instance    BashShell
    AutoRecoveringTerminal.initialize
    ...    shells=${bashshell}
    ...    prepare=${terminal.setup_session}
    ...    finalize=${terminal.close}
    AutoRecoveringTerminal.initialize_terminal

    ${session}=    Get Library Instance    AutoRecoveringTerminal

    terminal.initialize    session=${session}

Setup AutoRecoveringTerminal autoterminal
    ${bashshell}=    Get Library Instance    BashShell
    autoterminal.initialize_with_shells    shells=${bashshell}
    autoterminal.initialize_if_needed

Verify Get Proxy Object In Terminal
    terminal.run_python    handle = 0
    ${termobj}=    Get Library Instance    terminal
    Verify Handle Value    ${termobj}

Verify Get Proxy Object In AutoTerminal
    autoterminal.run_python    handle = 0
    ${termobj}=    Get Library Instance    autoterminal
    Verify Handle Value    ${termobj}

Verify Handle Value
    [Arguments]    ${termobj}
    ${handle_value}=    Get Variable Value
    ...    ${termobj.get_proxy_object('handle', int).as_local_value()}
    Should Be Equal As Integers    ${handle_value}     0

*** Test Cases ***

Test Get Proxy Object With TestSession
    [Setup]     Setup TestSession Terminal
    Verify Get Proxy Object In Terminal

Test Get Proxy Object With AutorecoveringTerminal
    [Setup]    Setup AutoRecoveringTerminal terminal
    Verify Get Proxy Object In Terminal

Test Get Proxy Object With AutoRunnerTerminal
    [Setup]    Setup AutoRecoveringTerminal autoterminal
    Verify Get Proxy Object in autoterminal
