#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  4 18:51:07 2018

This is a script to test Normalize_DWI WF.

See Normalize_DWI.ipynb for test input data info.

@author: tsuchida
"""

import os.path as op
from nipype_SLURM.workflows.Normalize_DWI import genNormalizeDwiWF

test_dir = "/data/extra/tsuchida/MRiShare/DWI_pipe/Normalize_test/"
test_input = op.join(test_dir, "input_dir")
test_subs = ["SHARE0001", "SHARE0002", "SHARE0003"]

spm_standalone = '/srv/shares/softs/spm12/run_spm12.sh'
mcr = '/srv/shares/softs/MCR/v713'
wf = genNormalizeDwiWF(name='NormalizeDwi',
                       base_dir=test_dir,
                       input_dir=test_input,
                       spm_standalone=spm_standalone,
                       mcr=mcr)


wf.config['logging'] = {'workflow_level': 'DEBUG',
                        'interface_lavel': 'DEBUG'}

wf.run(plugin='SLURM', plugin_args={'sbatch_args': '--time=23:59:00'})