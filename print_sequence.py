from script.fileApi import get_file_list
import yaml

def load_yaml_to_dic(yaml_path):
    with open(yaml_path, 'r') as y_file:
        dic = yaml.load(y_file, Loader=yaml.FullLoader)
    return dic

def print_sequence(assembly_info):
    # assembly_info = load_yaml_to_dic("test_sequence.yaml")
    used_part = assembly_info["part"]
    used_assembly = assembly_info["assembly"]
    whole_sequence = assembly_info["sequence"]

    for sequence_idx in whole_sequence:
        assembly = used_assembly[sequence_idx]
        part_id_0 = assembly[0]["part_id"]
        part_id_1 = assembly[1]["part_id"]
        part_name_0 = used_part[part_id_0]["part_name"]
        part_instance_0 = used_part[part_id_0]["instance_id"]
        part_name_1 = used_part[part_id_1]["part_name"]
        part_instance_1 = used_part[part_id_1]["instance_id"]
        

        print("""
        =======> {}_{} and {}_{}
        """.format(part_name_0, part_instance_0, part_name_1, part_instance_1))

assembly_info = load_yaml_to_dic("final_result_5_to_9.yaml")
print_sequence(assembly_info)
# root = "./assembly/STEFAN/SNU_result"
# info_files = get_file_list(root)
# info_files.sort()
# for info_file in info_files:
#     assembly_info = load_yaml_to_dic(info_file)
#     print_sequence(assembly_info)