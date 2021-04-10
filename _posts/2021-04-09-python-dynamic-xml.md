---
title: "Dynamic XML Library with Python"
categories:
  - Python
tags:
  - python
  - xml

last_modified_at: 2021-04-09T14:25:52-05:00
---

Here is a high-level overview of a pattern I see at work all too often:
- A new XML type is conceived and a schema definition document (.xsd) is introduced
- XML files are created based on the new .xsd
- Code files are written to abstract away the low-level details of reading/writing XML data and give an easy to use API
for accessing data.

Lets look at very simple example

```xml
<!-- ConfigFile.xml -->
<ConfigFile>
    <Parameters
        timeout="1000"
        runtimeDataPath="/path/to/data" />

</ConfigFile>
```

```xml
<!-- ConfigFile.xsd -->
```

```python
# ConfigFile.py

from xml.etree import etree

class ConfigFile:
    def __init__(self, pathToFile):
        self.parameters = {}

        try:
            self.from_xml(etree.parse(pathToFile).getroot())
        except BaseException as e:
            print(f"Error Parsing {pathToFile}:{e}")

    def from_xml(self, node):
        parameters_node = node.find('Parameters')[0]
        self.parameters = dict(parameters_node.attrib)

    @property
    def timeout(self):
        return self.parameters.get('timeout', 2000)

    @timeout.setter
    def timeout(self, value):
        self.parameters['timeout'] = value

    @property
    def runtime_data_path(self):
        return self.parameters.get(
            'runtimeDataPath',
            '/path/to/runtime/data'
        )

    @runtime_data_path.setter
    def runtime_data_path(self, value):
        return self.parameters['runtimeDataPath'] = value
```

```python
# main.py

from Config import ConfigFile

config = ConfigFile('/path/to/config')

# do import things using data from config
initialize_from_data(config.path_to_data)
initialize_server(config.timeout)
```

Lets breakdown what's going on
- There exists "ConfigFile.xml" which describes parameters to control our script
- There exists "ConfigFile.xsd" which describes the allowed format of the configuration file
- There exists "ConfigFile.py" which has a class that gives the rest of our code easy access to config file data

Here's what I hate about this pattern
- If a property of the .xsd needs to be changed for any reason, changes to the source code are almost always needed
- It may not be obvious, but we are defining the definition of the "ConfigFile.xml" in two locations: "ConfigFile.xsd" and
"ConfigFile.py".  They are tightly coupled because the both reflect the actual definition of "ConfigFile.xml", just in
a different file format.

You can imagine how tedious this becomes on codebases that have hundreds of different XML file types and the coding standards
state we must (MUST) create API's to read/write data from/to our configuration files.  Thankfully, there are some tools
out there to help with this problem.  Here are some of the favorites:
- generateDS
    - http://www.davekuhlman.org/generateDS.html
    - Autogenerates code from schema definition files
- PyXB
    - http://pyxb.sourceforge.net/
    - Autogenerates code from schema definition files

These two tools are outstanding and may be enough for the majority use case.  But there's still a problem, a change to
the schema file produces a change to the python source code.  It's true, you are no longer writing the source code and it
takes a mere second to regenerate the new python code.  But... it's still duplication no matter what way you look at it.
And this post would be boring if we stopped here.  So, lets take a look at a way to eliminate the middle man.  And by
middle man I mean unnecessary boilerplate python code.

The trick we are going to employ is overloading (overriding?) two class level attributes: \_\_get\_\_ and \_\_setitem\_\_.
If you aren't familiar with these, here's a brief overview:
- \_\_get\_\_ is called whenever a member lookup of a class instance fails.  For example, if I call obj.foo and foo is not a member
 of obj, then a ValueError is raised.  This is the default behaviour of \_\_get\_\_
- \_\_setitem\_\_ is called whenever a member of a class instance is being set to a value.  There is a slight subtlty here in that
this is ALWAYS called, where as \_\_get\_\_ is only called when a member lookup fails.  We'll have to keep this in mind
when we write the code.

Let's look at a very basic example of this concept

```python
class LookupDict:
    def __init__(self):
        self.data = {
            'a': 1,
            'b': 2,
            'c': 3,
        }

    # This only gets called when member lookup fails.
    def __get__(self, key):
        # Before raising, see if key is in data.
        if key not in self.data:
            raise ValueError(key)

        # it's a valid key, return the data
        return self.data[key]

    # this always gets called when a member is beign set, whether it exists or not.
    def __setitem__(self, key, value):
        # we can fall into a recursive trap here.
        # defer to our super if it's in __all__
        # it's existence in all implies it's a valid member of the class
        # we have to check for 'data' specifically for the case the first time data is set,
        # as it won't be in all.  In general, this extra list contains all hand-defined
        # members of a class
        if key in self.__all__ or key in ['data']:
            super().__setitem__(key, value)

        # The user gave us an invalid key, just raise
        if key not in self.data:
            raise ValueError(key)

        self.data[key] = value

lookup = LookupDict()

# This won't raise, even though we don't define any of these members!
print(lookup.a)
print(lookup.b)
print(lookup.c)
lookup.c = 10
print(lookup.c)

# this will raise
print (lookup.d)
```

This is a pretty neat trick (in my opinion) and we can use it to our advantage when parsing xml data.

To Be Continued...