# Copyright (C) 2019, Nokia

*** Settings ***

Library    FileCopier.py
Library    filehelper.py

Suite Teardown    filehelper.Remove Files    ${filenames}

*** Variables ***

@{filenames}    localfile   remotefile   localfilecopy

*** Test Cases ***

Verify Random File Copy
    [Tags]    skip
    filehelper.Create Random File    localfile   1024
    FileCopier.Copy File To Remote   localfile   remotefile
    FileCopier.Copy File From Remote    remotefile    localfilecopy
    filehelper.diff files    localfile    localfilecopy
