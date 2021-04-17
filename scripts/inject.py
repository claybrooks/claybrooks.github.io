data = {
    "beams": {
       "BEAM_ID_1": {
            "getAngle": 50,
            "getRate": 10,
            "getRotationalVelocity": 5,
        },
       "BEAM_ID_2": {
            "getAngle": 51,
            "getRate": 10,
            "getRotationalVelocity": 5,
        },
       "BEAM_ID_3": {
            "getAngle": 52,
            "getRate": 10,
            "getRotationalVelocity": 5,
        },
    },
    "antennas": {
        "ANTENNA_ID_1": {
            "getBeams": [
                "BEAM_ID_1", "BEAM_ID_3"
            ],
            "getType": "ANTENNA_TYPE_1",
        }
    }
}

class Injectable:
    def __init__(self):
        pass

class Environment:
    def __init__(self, file_path):

        # create Injectable items and put them here
        self.injected_data = {}

        # open the data
        #with open(file_path, 'r') as f:
        #    self.data = json.load(f)
        self.data = data
        # _type is the high-level object names: beams, antennas, etc...
        for _type in self.data:
            self.inject_environment_object(_type)

            # add direct access to the map of injectable types
            # _type is "beams", "antennas", etc...
            # eg. env.beams["BEAM_ID_1"], env.antennas["ANTENNA_ID_1"]
            setattr(self, _type, self.injected_data[_type])

    def inject_environment_object(self, obj_type):

        # create the sub-map of injectable items if it doesn't exist yet
        if obj_type not in self.injected_data:
            self.injected_data[obj_type] = {}

        # obj_id is the id of a high-level environment object, like
        # BEAM_ID_1, ANTENNA_ID_1
        for obj_id in self.data[obj_type]:
            self.inject_object(obj_type, obj_id)

    def inject_object(self, obj_type, obj_id):
        # create the injectable object for things like "BEAM_ID_1",
        # "ANTENNA_ID_1"
        self.injected_data[obj_type][obj_id] = Injectable()

        # Set 'BEAM_ID_1', 'ANTENNA_ID_1' to return the injectable object
        setattr(self, obj_id, self.injected_data[obj_type][obj_id])

        # Iterate through each "function" key in the json data and add
        # it as a callable to the injected object
        obj = self.injected_data[obj_type][obj_id]
        for func in self.data[obj_type][obj_id]:
            setattr(obj, func,
                lambda _type=obj_type, id=obj_id, f=func:\
                    self.data[_type][id][f]
            )

env = Environment("hey")

print (env.BEAM_ID_1.getAngle())
print (env.ANTENNA_ID_1.getBeams())
print (env.ANTENNA_ID_1.getType())

for beam_id in env.ANTENNA_ID_1.getBeams():
    print (env.beams[beam_id].getAngle())