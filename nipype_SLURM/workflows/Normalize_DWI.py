#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 19 13:54:18 2018

WF to normalize DTI/Noddi to standard space using spmNormalize_DWI or other WF. 
We use this for now since we already use Normalize12 for T1 data, but we may change
this eventually to other algo, like flirt followed by ANTS.

In the current connectomics pipe outline we don't have a good DWI ref (avg b0 from cropped DWI), 
so we add the node to get it from denoised_dwi, but we shouldn't ned this step after
cleaning up the DWI pipe...

Unzip input files before using the spmNormalize_DWI WF to avoid having to gunzip each time 
for different "apply_to" files...

@author: tsuchida
"""
import os
import os.path as op
from nipype.pipeline.engine import Workflow, Node, MapNode
from nipype.algorithms.misc import Gunzip
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import DataGrabber, DataSink
from nipype.interfaces.mrtrix3.utils import DWIExtract
from nipype.interfaces.fsl.maths import MeanImage
from nipype_SLURM.workflows.subworkflows.spmNormalize_DWI import genSpmNormalizeDwiWF


def genNormalizeDwiWF(name='NormalizeDwi',
                      base_dir=op.abspath('.'),
                      input_dir=None,
                      input_temp='%s/%s/*%s',
                      input_temp_args = {'ref_T1': [['subject_id', 'bias_corrected_images', '_mT1.nii.gz']],
                                         'forward_deformation_field': [['subject_id', 'forward_deformation_field', '_y_T1.nii.gz']],
                                         'denoised_dwi' : [['subject_id', 'denoised_dwi_series', '_dwi_denoised.nii.gz']],
                                         'bval':[['subject_id', 'raw_bvals', '_bval.gz']],
                                         'bvec':[['subject_id', 'processed_bvecs', '_bvecs.gz']],
                                         'apply_to': [['subject_id', 'apply_to_files', ['_ICVF.nii.gz', '_ISOVF.nii.gz', '_OD.nii.gz']]]},
                      subjects=None,
                      spm_standalone=None,
                      mcr=None):
      
    # Generate WF
    wf = Workflow(name=name)
    wf.base_dir = base_dir
      
    #Node: subject List
    subjectList = Node(IdentityInterface(fields=['subject_id'], mandatory_inputs=True), name="subjectList")
    if subjects:
        subjectList.iterables = ('subject_id', subjects)
    else:
        subjectList.iterables = ('subject_id', [pth for pth in os.listdir(input_dir) if os.path.isdir(op.join(input_dir,pth))])
        print subjectList.iterables
        
    scanList = Node(DataGrabber(infields=['subject_id'],
                                outfields=['ref_T1',
                                           'forward_deformation_field',
                                           'denoised_dwi', 
                                           'bval',
                                           'bvec',
                                           'apply_to']), 
                    name="scanList")
    scanList.inputs.base_directory = input_dir
    scanList.inputs.ignore_exception = False
    scanList.inputs.raise_on_empty = True
    scanList.inputs.sort_filelist = False
    scanList.inputs.template = input_temp
    scanList.inputs.template_args =  input_temp_args
    wf.connect(subjectList, "subject_id", scanList, "subject_id")
    
    # Unzip everythin for spm
    gunzipT1 = Node(Gunzip(), name='gunzipT1')
    wf.connect(scanList, "ref_T1", gunzipT1, "in_file")
    
    gunzipDF = Node(Gunzip(), name='gunzipDF')
    wf.connect(scanList, "forward_deformation_field", gunzipDF, "in_file")
    
    gunzipbval = Node(Gunzip(), name='gunzipbval')
    wf.connect(scanList, "bval", gunzipbval, "in_file")
    
    gunzipbvec = Node(Gunzip(), name='gunzipbvec')
    wf.connect(scanList, "bvec", gunzipbvec, "in_file")
    
    gunzipApplyTo = MapNode(Gunzip(), 
                            iterfield=["in_file"],
                            name='gunzipApplyTo')
    wf.connect(scanList, "apply_to", gunzipApplyTo, "in_file")
    
    # Extract b=0 frames from denoised DWI and average them to make a ref_dwi
    dwib0 = Node(DWIExtract(), name="dwib0")
    dwib0.inputs.bzero = True
    dwib0.inputs.out_file = "dwib0.nii.gz"
    wf.connect(scanList, "denoised_dwi", dwib0, "in_file")
    wf.connect(gunzipbval, "out_file", dwib0, "in_bval")
    wf.connect(gunzipbvec, "out_file", dwib0, "in_bvec")
    
    # Make an average image
    avgb0 = Node(MeanImage(), name="avgb0")
    avgb0.inputs.nan2zeros = True
    avgb0.inputs.output_type = "NIFTI"
    avgb0.inputs.out_file = "avg_dwib0.nii"
    avgb0.inputs.dimension = "T"
    wf.connect(dwib0, "out_file", avgb0, "in_file")
    
    # spm Normalize WF
    spmNormProc = genSpmNormalizeDwiWF(name="spmNormProc",
                                       spm_standalone=spm_standalone,
                                       mcr=mcr)
    wf.connect(gunzipT1, "out_file", spmNormProc, "inputNode.ref_T1")
    wf.connect(gunzipDF, "out_file", spmNormProc, "inputNode.forward_deformation_field")
    wf.connect(avgb0, "out_file", spmNormProc, "inputNode.ref_dwi")
    wf.connect(gunzipApplyTo, "out_file", spmNormProc, "inputNode.apply_to")
    
    # Datasink
    datasink = Node(DataSink(base_directory=base_dir,
                             container='%sSink' % name),
                    name='Datasink')
    wf.connect(spmNormProc, "outputNode.normalized_files", datasink,"normalized_files")
    
    return wf
    