---
title: "Runtime Injected Python API"
categories:
  - Python
tags:
  - python
  - dynamic
  - xml

last_modified_at: 2021-04-16
---

This is going to be a journey through a very niche problem centered around access to a static database.  Here's the
situation at a high level:

- There exists a database containing data having to do with environmental properties
- The database is rather large, in the gigabyte range
- The data in this database is updated quarterly (more like semi-annually) based on field research
- The database is read-only via the provided Java API
- My team relies heavily on third-party environmental data and our consumption scripts are written only in python

The reasoning behind taking on this new source of data:

- The decision was made to consume this third-party database because there were enormous gaps in our current data source
- In order to obtain a higher level of accredidation from our governing agency, a higher fidelity data source was
needed.
- This new source of data is well known within our community and it was only a matter of time before we were forced to
switch to it

The main problems of taking on this new data source:

- The API was staggering to say the least.  The spin up time to get this integrated into our systems was non-negligible.
- The lack of support for other languages besides Java was dissapointing.  On top of that, management didn't want to pay
to write java programs to process data nor did they want to go through the headache of bridging the gap between our
absolutely enormous library of python code to the absolutely enormous Java API that we now had access to.

So what were we to do?  After a while, the phrase "bite the bullet" was slowly becoming the only option.  That is, until
I noticed something rather peculiar about the GUI application that came packaged with the api: It took almost zero-time
to display environmental information.  Recall that this database is in the gigabyte range, loading gigabytes of data is
not an immediately finishable task (atleast on my hardware at the time), especially when heavy processingo of that data
is involved (the format of their database did not translate 1:1 to how it was laid out in physical memory).  During my
initial efforts to go through their "Hello World" example, I noticed how slow the API took to load, usually around a
full minute.  So, how in the world can their API take nearly a minute to initialize yet their UI is displaying data
instantly?  At first I thought I was missing an async portion of their API, but I was not.  Everything about their API
was synchronous.  This made me even more confused.  After digging through the folder structure, I stumbled upon a
rather sizeable .json file, a few hundred megabytes, and it looked something like this:

```json
{
    "beams": {
       "BEAM_ID_1": {
            "getAngle": 50,
            "getRate": 10,
            "getRotationalVelocity": 5,
        },
    },
    "antenna": {
        "ANTENNA_ID_1": {
            "getBeams": [
                "BEAM_ID_1"
            ],
            "getType": "ANTENNA_TYPE_1",
        }
    }
}
```

This is a watered down version of what I saw, but the main takeaway is they dumped function call names and the
associated return values, almost like one big sweep of some nasty java reflection.  So, it hit me: they aren't using
their API at all to display information in the GUI.  They pre-processed to a smaller form and are consuming the .json
file to populate the display.  For them to disregard their own API spoke volumes about it's (un)useability.

So, I eventually thought back on the work I had done with [DynamicXml](https://claybrooks.github.io/python/2021/04/09/python-dynamic-xml.html),
and wondered if something similar could be done here.  Let's look at a toy example.

```python
#main.py
class Injectable:
    def __init__(self):
        pass

def inject(obj, func):
    setattr(obj, func,
        lambda f=func: print (f"{f} was injected as a function!")
    )

obj = Injectable()
inject(obj, "new_function0")
inject(obj, "new_function1")
inject(obj, "new_function2")
obj.new_function2()
obj.new_function1()
obj.new_function0()
```

The output from above:

```
new_function2 was injected as a function!
new_function1 was injected as a function!
new_function0 was injected as a function!
```

Nice!  Some attributes were injected in the form of a lambda and they can be called like any regular function.  But what
if we wanted to call with arguments?  Here's the adjusted code:

```python
# main.py
class Injectable:
    def __init__(self):
        pass

def inject(obj, func):
    setattr(obj, func,
        lambda arg, f=func: print (
            f"{f} was injected as a function!  Called with {arg}!")
        )

obj = Injectable()
inject(obj, "new_function0")
inject(obj, "new_function1")
inject(obj, "new_function2")
obj.new_function2(0)
obj.new_function1(1)
obj.new_function0(2)
```

And the output is:

```
new_function2 was injected as a function! Called with 0!
new_function1 was injected as a function! Called with 1!
new_function0 was injected as a function! Called with 2!
```

Excellent!  Taking this toy example, we can meld it with what exists in the .json file to create the API on the
fly.  It's import to re-iterate that no boiler plate code will be created to match the data in the .json file.  As the
.json file is updated over time, possibly with new or changed API calls, the python code will not need to change in any
way.  Of course, the usage of the API functions will need to change if the names of the functions change.

Here's the full working example:

```json
{
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
    "antenna": {
        "ANTENNA_ID_1": {
            "getBeams": [
                "BEAM_ID_1",
                "BEAM_ID_3"
            ],
            "getType": "ANTENNA_TYPE_1",
        }
    }
}
```

```python
#main.py

class Injectable:
    def __init__(self):
        pass

class Environment:
    def __init__(self, file_path):

        # create Injectable items and put them here, this will match
        # the structure of the input .json file
        self.injected_data = {}

        # read in the data
        with open(file_path, 'r') as f:
            self.data = json.load(f)

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

env = Environment("/path/to/data.json")

print (env.BEAM_ID_1.getAngle())
print (env.ANTENNA_ID_1.getBeams())
print (env.ANTENNA_ID_1.getType())

for beam_id in env.ANTENNA_ID_1.getBeams():
    print (env.beams[beam_id].getAngle())
```

And the output is:

```
50
['BEAM_ID_1', 'BEAM_ID_3']
ANTENNA_TYPE_1
50
52
```

First there is the ```Injectable``` class that is nothing but a placeholder to store the injected attributes and
functions.  Next, ```Environment``` is created and the input .json file is loaded.  A map of object types to objects are
created.  Each object is nothing more than a set of injected function attributes that return the value from the original
.json data.  One thing to note about our dataset is the id's for each type of object are unique across the entire set of
objects, meaning a beam cannot have the same id as an antenna.  These id's are regulated by a governing agency and they
ensure the uniqueness of the data.

Considering what has been done, here are the pros:

- Autogenerated API
- No need to change python code when the Java API changes, only potential updates to call sites
- Ignore's very slow Java API to get access to the data
- No need to re-document the non-existent python code, just follow the java documentation to figure out how to access
the data

And the cons:

- No intellisense support in the IDE since the functions can't be statically analyzed
- Slightly tied to the API author providing the .json data

Well, there you have it.  A minimum working example of a runtime injectable python API!

{% if page.comments == true %}
  {% include comments.html %}
{% endif %}
