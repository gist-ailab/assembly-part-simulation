#!/usr/bin/env python
"""
State Machine Compiler

author: KIM-HC, psh117
date: 2020-11-09-

"""
from __future__ import print_function

import sys
import copy
import yaml
import numpy as np
from enum import Enum

"""
SM
PinSM
BracketSM

DropSM
GraspSM
HandOverSM

DualPegSM
TriplePegSM

"""

"""
part_id         :   given part id (YAML['part'][part_id]) -> 1 or 2 or 3, ...
part_name       :   ikea_stefan_long
instance_name   :   ikea_stefan_long_0

model           :   dict(), including ['part_id'], ['assembly_point']

pin             :   connector model
assembled       :   model of previous step (not a connector)
assembling      :   model of current step (not a connector)

assembly_id     :   given assembly id (YAML['assembly'][assembly_id]) -> 1 or 2 or 3, ...

"""

class AssemblyType(Enum):
    PIN = 1
    DUAL_PEG = 2
    TRIPLE_PEG = 3
    BRACKET = 4

class StateMachineCompiler():

    def __init__(self, yaml_name = 'test'):
        self.test_print = False
        with open(yaml_name, 'r') as stream:
            self.yaml_reader = yaml.safe_load(stream)
        self.model_part = {} # part info for a sequence
        self.model_assembly ={} # assembly info
        self.model_sequence = {}
        self.sequence_info = []
        self.total_step = 0
        self.peg_counter = 0
        self.peg_list = []
        self.arm_grasp = {'panda_left':'free', 'panda_right':'free', 'panda_top':'free'}

        self.model_part = self.yaml_reader['part']
        self.model_assembly = self.yaml_reader['assembly']
        self.model_sequence = self.yaml_reader['assembly_sequence']
        
        print (self.model_sequence)
        self.grasp_ignore_list = ['ikea_stefan_bolt', 'ikea_stefan_side_right', 'ikea_stefan_side_left', 'ikea_stefan_pin', 'ikea_stefan_bracket']
        self.arm_grasp_priorities = {'ikea_stefan_long_0':'panda_right', 'ikea_stefan_short_0':'panda_right', 'ikea_stefan_middle_0':'panda_top'}

    def get_part_name(self, part_id):
        return self.model_part[part_id]['part_name']

    def get_instance_name(self, part_id):
        return self.model_part[part_id]['part_name'] + '_' + str(self.model_part[part_id]['instance_id'])

    def get_assembly_data(self, assembly_id):        
        out = []
        for assemble in self.model_assembly[assembly_id]:
            instance_name = self.get_instance_name(assemble['part_id'])
            assembly_point = assemble['assembly_point']
            out.append((instance_name, assembly_point)) # tuple

        return out

    def find_model_and_the_other(self, assembly_id, model_name):
        pin_index = 0
        obj_index = 1
        found = False
        for i in range(2):
            i_bar = 1 - i
            assemble = self.model_assembly[assembly_id][i]
            # instance_name = self.get_instance_name(assemble['part_id'])
            part_name = self.get_part_name(assemble['part_id'])
            # print(part_name, model_name)
            if part_name == model_name:
                pin_index = i
                obj_index = i_bar
                found = True
                # print('found')
        if found:
            return (self.model_assembly[assembly_id][pin_index], self.model_assembly[assembly_id][obj_index])
        else:
            return None

    def find_part_id_and_the_other(self, assembly_id, id):
        pin_index = 0
        obj_index = 1
        found = False
        for i in range(2):
            i_bar = 1 - i
            assemble = self.model_assembly[assembly_id][i]
            if assemble['part_id'] == id:
                pin_index = i
                obj_index = i_bar
                found = True
                # print('found')
        if found:
            return (self.model_assembly[assembly_id][pin_index], self.model_assembly[assembly_id][obj_index])
        else:
            return None

    def calc_grasped_status(self, assembly_id):
        for assemble in self.model_assembly[assembly_id]:
            each_assemble = self.model_assembly[assembly_id][assemble]
            part_name = self.get_part_name(each_assemble['part_id'])
            instance_name = self.get_instance_name(each_assemble['part_id'])

            # print('calc_grasped_status' , instance_name)
            # print('calc_grasped_status' , part_name)
            if (part_name in self.grasp_ignore_list) == False:
                # print('not grasped')
                not_grasped = True
                for arm in self.arm_grasp:
                    if instance_name == self.arm_grasp[arm]:
                        not_grasped = False
                if not_grasped:
                    target_arm = self.arm_grasp_priorities[instance_name]
                    if self.arm_grasp[target_arm] == 'free':
                        print (target_arm, 'will grasp', instance_name)
                        self.arm_grasp[target_arm] = instance_name
                        self.total_step += 1
                        self.sequence_info.append({'sm_type':'GraspSM',
                                                   'object_id':instance_name,
                                                   'arm_name':target_arm})
                    else:
                        print ('not supported')
                        pass
#                         print('panda_right will hand',self.arm_grasp['panda_right'],'to panda_top')
#                         self.add_hand_over('panda_right','panda_top',self.arm_grasp['panda_right'])
#                         print('panda_right will grasp',part[0])
#                         self.arm_grasp['panda_right'] = part[0]
#                         self.total_step += 1
#                         self.sequence_info.append({'sm_type':'GraspSM'})
#                         self.sequence_info[-1]['object_id'] = part[0]
#                         self.sequence_info[-1]['arm_name'] = 'panda_right'


    def decode_sequence(self, sequence, step):
        """
        sequence: List(), array of assembly ids (ex: [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24])
        step: current step of the input sequence
        """

        assembly_type = AssemblyType.PIN

        assembled_model = {}
        assembly_id = sequence[step]
        assembled_part_name = ''
        assembling_part_name = ''
        assembled_instance_name = ''
        assembling_instance_name = ''
        r = self.find_model_and_the_other(assembly_id, 'ikea_stefan_pin')
        if r is not None:
            pin_model, assembling_model = r
            self.calc_grasped_status(assembly_id)
            assembly_type = AssemblyType.PIN
            for prev_step in range(step):
                r = self.find_part_id_and_the_other(sequence[prev_step], pin_model['part_id'])
                if r is None:
                    continue
                # pin_prev_model, 
                _, assembled_model = r
                assembled_part_id = assembled_model['part_id']
                assembled_instance_name = self.get_instance_name(assembled_part_id)
                print('this pin is already assembled with', assembled_instance_name)

                assembling_part_name = self.get_part_name(assembling_model['part_id'])
                assembled_part_name = self.get_part_name(assembled_model['part_id'])
                assembling_instance_name = self.get_instance_name(assembling_model['part_id'])
                assembled_instance_name = self.get_instance_name(assembled_model['part_id'])
                print(assembled_part_name,assembling_part_name)
                if assembled_part_name == 'ikea_stefan_middle':
                    if assembling_part_name in ['ikea_stefan_side_left', 'ikea_stefan_side_right']:
                        assembly_type = AssemblyType.TRIPLE_PEG
                else:
                    assembly_type = AssemblyType.DUAL_PEG
                break

        r = self.find_model_and_the_other(assembly_id, 'ikea_stefan_bracket')
        if r is not None:
            assembly_type = AssemblyType.BRACKET
            # print('bracket')
            # _, assembling_model = r
        # print (self.get_instance_name(self.model_assembly[assembly_id][0]['part_id']))
        # print (self.get_instance_name(self.model_assembly[assembly_id][1]['part_id']))
        # print (self.get_part_name(self.model_assembly[assembly_id][0]['part_id']))
        # print (self.get_part_name(self.model_assembly[assembly_id][1]['part_id']))
        if assembly_type is AssemblyType.PIN:
            pin_model, obj_model = self.find_model_and_the_other(assembly_id, 'ikea_stefan_pin')

            self.sequence_info.append({'sm_type':'PinSM',
                                       'pin_id': self.get_instance_name(pin_model['part_id']),
                                       'object_id': self.get_instance_name(obj_model['part_id']),
                                       'assembly_index':obj_model['assembly_point']})
            for arm in self.arm_grasp:
                if self.sequence_info[-1]['object_id'] == self.arm_grasp[arm]:
                    self.sequence_info[-1]['grasp_arm'] = arm
            self.total_step += 1

        elif assembly_type is AssemblyType.DUAL_PEG:
            self.peg_counter += 1
            if self.peg_counter == 1: 
                self.sequence_info.append({'sm_type':'DualPegSM',
                                           'object_id': assembled_instance_name,
                                           'assembly_index':[assembled_model['assembly_point']],
                                           'target_object_id':assembling_instance_name,
                                           'target_assembly_index': [assembling_model['assembly_point']]})
                # print ('arm_grasp',self.arm_grasp)
                for arm in self.arm_grasp:
                    if self.arm_grasp[arm] == assembled_instance_name:
                        # print('find', arm)
                        self.sequence_info[-1]['arm_name'] = arm
                self.total_step += 1

            elif self.peg_counter == 2:
                self.sequence_info[-1]['assembly_index'].append(assembled_model['assembly_point'])
                self.sequence_info[-1]['target_assembly_index'].append(assembling_model['assembly_point'])
                print('finished dual peg')
                for arm in self.arm_grasp:
                    if self.arm_grasp[arm] == assembled_instance_name:
                        self.arm_grasp[arm] = 'free'
                self.peg_counter = 0

        elif assembly_type is AssemblyType.TRIPLE_PEG:
            self.peg_counter += 1
            if self.peg_counter == 1:
                self.sequence_info.append({'sm_type':'TriplePegSM',
                                           'object_id': assembled_instance_name,
                                           'assembly_index':[assembled_model['assembly_point']],
                                           'target_object_id':assembling_instance_name,
                                           'target_assembly_index':[assembling_model['assembly_point']]})
                for arm in self.arm_grasp:
                    if self.arm_grasp[arm] == assembled_instance_name:
                        self.sequence_info[-1]['arm_name'] = arm
                self.total_step += 1

            elif self.peg_counter == 2:
                pin_model, obj_model = self.find_model_and_the_other(assembly_id, 'ikea_stefan_pin')
                self.sequence_info[-1]['assembly_index'].append(assembled_model['assembly_point'])
                self.sequence_info[-1]['target_assembly_index'].append(assembling_model['assembly_point'])
            elif self.peg_counter == 3:
                print('finished triple peg')
                self.sequence_info[-1]['assembly_index'].append(assembled_model['assembly_point'])
                self.sequence_info[-1]['target_assembly_index'].append(assembling_model['assembly_point'])
                for arm in self.arm_grasp:
                    if self.arm_grasp[arm] == assembled_instance_name:
                        self.arm_grasp[arm] = 'free'
                self.peg_counter = 0

        elif assembly_type is AssemblyType.BRACKET:
            if self.arm_grasp['panda_right'] is not 'free':
                self.add_hand_over('panda_right','panda_top',self.arm_grasp['panda_right'])
            bracket_model, obj_model = r
            self.sequence_info.append({'sm_type':'BracketSM',
                                       'object_id':self.get_instance_name(obj_model['part_id']),
                                       'bracket_id':self.get_instance_name(bracket_model['part_id']),
                                       'assembly_index':obj_model['assembly_point']})
            self.total_step += 1

    def drop_object(self, arm):
        self.total_step += 1
        self.sequence_info.append({'sm_type':'DropSM'})
        self.arm_grasp[arm] = 'free'

    def add_hand_over(self,giver,getter,object_id):
        self.total_step += 1
        self.sequence_info.append({'sm_type':'HandOverSM'})
        self.sequence_info[-1]['arm_name_from'] = giver
        self.sequence_info[-1]['arm_name_to'] = getter
        self.sequence_info[-1]['object_id'] = object_id
        self.arm_grasp[giver] = 'free'
        if self.arm_grasp[getter] is not 'free':
            print('dropped',self.arm_grasp[getter],'that',getter,'was holding')
            self.drop_object(getter)
        self.arm_grasp[getter] = object_id

    def compile(self):
        print('making sequence ...')
        print('sequence will be:')
        seq_step = 0
        for assemble in self.model_sequence[0]:
            print('assemble:',assemble)
            self.decode_sequence(self.model_sequence[0],seq_step)
            seq_step += 1

        print('\n-------------------------\nwill go through',self.total_step,'steps\n-------------------------')
        def pretty(d, indent=0):
            for key, value in d.items():
                print(key + ': ' + str(value))
        for i in range(self.total_step):
            print('step',i,'will use',self.sequence_info[i]['sm_type'])
            pretty(self.sequence_info[i])
            print()

if __name__ == '__main__':
    StateMachineCompiler('test.yaml').compile()