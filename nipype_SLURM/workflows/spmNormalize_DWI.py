#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 19 13:54:18 2018

WF to normalize DTI/Noddi to standard space using spm Coregister Normalize12. 
We use this for now since we already use Normalize12 for T1 data, but we may change
this eventually to other algo...

Unzip input files before using the WF to avoid having to gunzip each time 
for different "apply_to" files...

@author: tsuchida
"""

from nipype.pipeline.engine import Workflow, Node
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces import spm
from nipype.interfaces.spm.preprocess import Coregister, Normalize12


def genSpmNormalizeDwiWF(name='spmNormalizeDwi',
                         spm_standalone=None,
                         mcr=None):
    
    # Setup for SPM standalone
    matlab_cmd = ' '.join([spm_standalone, mcr, 'batch', 'script'])
    spm.SPMCommand.set_mlab_paths(matlab_cmd=matlab_cmd, use_mcr=True)
    
    # Generate WF
    wf = Workflow(name=name)

    # InputNode
    inputNode=Node(IdentityInterface(fields=['ref_T1',
                                             'forward_deformation_field',
                                             'ref_dwi',
                                             'apply_to']),
                                     name='inputNode')

    # spm Coregister
    coreg = Node(Coregister(), name='coreg')
    coreg.inputs.use_mcr = True
    coreg.inputs.mfile = False
    coreg.inputs.cost_function = 'nmi'
    coreg.inputs.jobtype = 'estimate'
    wf.connect(inputNode, "ref_T1", coreg, "target")
    wf.connect(inputNode, "ref_dwi", coreg, "source")
    wf.connect(inputNode, "apply_to", coreg, "apply_to_files")
    
    # spm Normalize12
    # Node: spmWarpDtiMetricsToStandard
    spmWarpToStd111 = Node(Normalize12(),
                           name="spmWarpToStd111")
    spmWarpToStd111.inputs.ignore_exception = False
    spmWarpToStd111.inputs.jobtype = 'write'
    spmWarpToStd111.inputs.use_v8struct = True
    spmWarpToStd111.inputs.write_bounding_box = [[-90.0, -126.0, -72.0], [90.0, 90.0, 108.0]]
    spmWarpToStd111.inputs.write_interp = 3
    spmWarpToStd111.inputs.use_mcr = True
    spmWarpToStd111.inputs.mfile = False
    spmWarpToStd111.inputs.write_voxel_sizes = [1.0, 1.0, 1.0]
    wf.connect(inputNode, "forward_deformation_field", spmWarpToStd111, "deformation_file")
    wf.connect(coreg, "coregistered_files", spmWarpToStd111, "apply_to_files")
    
    # Node: spmWarpB0ToStandard
    spmWarpb0ToStd111 = Node(Normalize12(),
                             name="spmWarpb0ToStd111")
    spmWarpb0ToStd111.inputs.ignore_exception = False
    spmWarpb0ToStd111.inputs.jobtype = 'write'
    spmWarpb0ToStd111.inputs.use_v8struct = True
    spmWarpb0ToStd111.inputs.write_bounding_box = [[-90.0, -126.0, -72.0], [90.0, 90.0, 108.0]]
    spmWarpb0ToStd111.inputs.write_interp = 3
    spmWarpb0ToStd111.inputs.use_mcr = True
    spmWarpb0ToStd111.inputs.mfile = False
    spmWarpb0ToStd111.inputs.write_voxel_sizes = [1.0, 1.0, 1.0]
    wf.connect(inputNode, "forward_deformation_field", spmWarpb0ToStd111, "deformation_file")
    wf.connect(coreg, "coregistered_source", spmWarpb0ToStd111, "apply_to_files")
    
    # OutputNode
    outputNode = Node(IdentityInterface(fields=["normalized_files",
                                                "normalized_b0"]), name="outputNode")                  
    wf.connect(spmWarpToStd111, "normalized_files", outputNode, "normalized_files")
    wf.connect(spmWarpb0ToStd111, "normalized_files", outputNode, "normalized_b0")
    
    return wf
    