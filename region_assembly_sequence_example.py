from script.const import AssemblyType

region_assembly_sequence_ex = {
    "sequence_1": [
        {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group":[
                    {
                        "id": 1,
                        "part_instance":{
                            "part_name": "ikea_stefan_long",
                            "instance_id": 0,
                        },
                        "region": None,
                    },
                ],
                "connector": 1,
                "assembly_number": 2
            }
        },
        {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group":[
                    {
                        "id": 3,
                        "part_instance":{
                            "part_name": "ikea_stefan_short",
                            "instance_id": 0,
                        },
                        "region": None,
                    },
                ],
                "connector": 1,
                "assembly_number": 2
            }
        },
    ],
    "sequence_2": [
        {
            "assembly_type": AssemblyType.group_connector_group,
            "component": {
                "group":[
                    {
                        "id": 3,
                        "part_instance":{
                            "part_name": "ikea_stefan_short",
                            "instance_id": 0,
                        },
                        "region": 1,
                    },
                    {
                        "id": 4,
                        "part_instance":{
                            "part_name": "ikea_stefan_side_left",
                            "instance_id": 0,
                        },
                        "region": 2,
                    },
                ],
                "connector": 2,
                "assembly_number": 2
            }
        },
        {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group":[
                    {
                        "id": 3,
                        "part_instance":{
                            "part_name": "ikea_stefan_short",
                            "instance_id": 0,
                        },
                        "region": 0,
                    },
                ],
                "connector": 2,
                "assembly_number": 2
            }
        },
    ],
    "sequence_3": [
        {
            "assembly_type": AssemblyType.group_connector_group,
            "component": {
                "group":[
                    {
                        "id": 1,
                        "part_instance":{
                            "part_name": "ikea_stefan_long",
                            "instance_id": 0,
                        },
                        "region": 0,
                    },
                    {
                        "id": 6,
                        "part_instance":{
                            "part_name": "ikea_stefan_side_left",
                            "instance_id": 0,
                        },
                        "region": 0,
                    },
                ],
                "connector": 2,
                "assembly_number": 2
            }
        },
        {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group":[
                    {
                        "id": 1,
                        "part_instance":{
                            "part_name": "ikea_stefan_long",
                            "instance_id": 0,
                        },
                        "region": 1,
                    },
                ],
                "connector": 2,
                "assembly_number": 2
            }
        },
    ],
    "sequence_4": [
        {
            "assembly_type": AssemblyType.group_connector_group,
            "component": {
                "group":[
                    {
                        "id": 2,
                        "part_instance":{
                            "part_name": "ikea_stefan_middle",
                            "instance_id": 0,
                        },
                        "region": 0,
                    },
                    {
                        "id": 7,
                        "part_instance":{
                            "part_name": "ikea_stefan_side_left",
                            "instance_id": 0,
                        },
                        "region": 1,
                    },
                ],
                "connector": 2,
                "assembly_number": 2
            }
        },
        {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group":[
                    {
                        "id": 2,
                        "part_instance":{
                            "part_name": "ikea_stefan_middle",
                            "instance_id": 0,
                        },
                        "region": 1,
                    },
                ],
                "connector": 2,
                "assembly_number": 2
            }
        },
        {
            "assembly_type": AssemblyType.group_connector_group,
            "component": {
                "group":[
                    {
                        "id": 2,
                        "part_instance":{
                            "part_name": "ikea_stefan_middle",
                            "instance_id": 0,
                        },
                        "region": 2,
                    },
                    {
                        "id": 7,
                        "part_instance":{
                            "part_name": "ikea_stefan_side_left",
                            "instance_id": 0,
                        },
                        "region": 3,
                    },
                ],
                "connector": 2,
                "assembly_number": 1
            }
        },
        {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group":[
                    {
                        "id": 2,
                        "part_instance":{
                            "part_name": "ikea_stefan_middle",
                            "instance_id": 0,
                        },
                        "region": 3,
                    },
                ],
                "connector": 2,
                "assembly_number": 1
            }
        },
    ],
}
