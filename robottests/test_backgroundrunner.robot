# Copyright (C) 2019, Nokia

*** Settings ***

Library    BackgroundRunner.py

*** Keywords ***

Verify ${expected_out} From ${handle} With Exit Code ${expected_ret}
    ${response}    BackgroundRunner.Terminate And Get Response    ${handle}
    Should Be Equal As Strings    ${response.out}    ${expected_out}
    ...    Expected stdout is ${expected_out} got ${response.out}
    Should Be Equal As Integers    ${response.ret}    ${expected_ret}
    ...    Expected returncode is ${expected_ret} got ${response.ret}


*** Test Cases ***

Test In Background Echo Hello World
    ${handle}    BackgroundRunner.Run In Background    echo Hello World!
    Verify Hello World!\n From ${handle} With Exit Code 0

Test In Background Echo Hello World With Sleep
    ${handle}    BackgroundRunner.Run In Background
    ...    echo Hello World!;sleep 100
    Verify Hello World!\n From ${handle} With Exit Code -15

Test Two Simultaneous Background Runs
    ${handle1}    BackgroundRunner.Run In Background    echo Run1;sleep 100
    ${handle2}    BackgroundRunner.Run In Background    echo Run2;sleep 100
    Verify Run1\n From ${handle1} With Exit Code -15
    Verify Run2\n From ${handle2} With Exit Code -15
