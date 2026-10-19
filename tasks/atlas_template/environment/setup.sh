#!/bin/bash
# Copyright (C) 2002-2020 CERN for the benefit of the ATLAS collaboration
#
# Environment configuration file setting up the installed project.
#

# used as an entrypoint script

# Set up the compiler for the environment.
source /opt/lcg/gcc/14.2.0*/x86_64-*/setup.sh

# Set up the {{cookiecutter.project_name}} installation:
source /usr/StatAnalysis/*/InstallArea/*/setup.sh
echo "Configured StatAnalysis from: ${StatAnalysis_DIR}"

# preserve aliases that have been set up, in case the CMD that is run below is a subshell (which doesnt automatically inherit aliases)
echo "$(alias)" >> ~/.bashrc

# Set up the prompt:
export PS1='\[\033[01;35m\][bash]\[\033[01;31m\][\u StatAnalysis-$StatAnalysis_VERSION]\[\033[01;34m\]:\W >\[\033[00m\] ';

# execute whatever cmds required
exec "$@"
