---
title: "Dynamic XML Library with Python"
categories:
  - Python
tags:
  - python
  - xml

last_modified_at: 2021-04-10
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

        '''
        ...
        ... xml parsing code
        ...
        '''

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
- There exists "ConfigFile.xsd" which describes the allowed format of the "ConfigFile.xml"
- There exists "ConfigFile.py" which has a class that gives the rest of our code easy access to config file data

Here's what I hate about this pattern
- If a property of the .xsd needs to be changed for any reason, changes to the source code are almost always needed
- It may not be obvious, but we are defining the definition of the "ConfigFile.xml" in two locations: "ConfigFile.xsd"
and "ConfigFile.py".  They are tightly coupled because they both reflect the actual definition of "ConfigFile.xml"
albeit in different file formats.

You can imagine how tedious this becomes on codebases that have hundreds of different XML file types.  Our coding
standards at work state we must (MUST) create API's to read/write data from/to our configuration files.  Thankfully,
there are some tools out there to help with this problem.  Here are a few:
- generateDS
    - http://www.davekuhlman.org/generateDS.html
    - Autogenerates code from schema definition files
- PyXB
    - http://pyxb.sourceforge.net/
    - Autogenerates code from schema definition files

These two tools are outstanding and may be enough for the majority use case.  But there's still a problem: a change to
the schema file produces a change to the source code.  It's true, you are no longer writing the source code and
it takes a mere second to regenerate,  but... it's still duplication no matter what way you look at it.  This post would
be boring if we stopped here, so lets take a look at a way to eliminate the unnecessary boilerplate python code.

The trick we are going to employ is overriding two class level attributes: \__get__ and \__setitem__.  If you
aren't familiar with these, here's a brief overview:
- \__get__ is called whenever a member lookup of a class instance fails.  For example, if I call obj.foo and foo is
not a member of obj, then a ValueError is raised.  This is the default behaviour of \__get__
- \__setitem__ is called whenever a member of a class instance is being set to a value.
- There is a slight subtlty here in \__setitem__ is ALWAYS called, where as \__get__ is only called when a member
lookup fails.  We'll have to keep this in mind when we write the code.

Let's look at a very basic example of this concept

```python
class XmlNode:
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

    # this always gets called when a member is beign set, whether it
    # exists or not.
    def __setitem__(self, key, value):
        # We can fall into a recursive trap here.
        # Defer to our super if it's in __all__ as it's existence in
        # __all__ implies it's a valid member of the class.
        # We have to check for 'data' specifically for the edge case that
        # this is the first time data is set as it won't be in __all__.
        # In general, this extra list contains all hand-defined members
        # of a class
        if key in self.__all__ or key in ['data']:
            super().__setitem__(key, value)

        # The user gave us an invalid key, just raise
        if key not in self.data:
            raise ValueError(key)

        self.data[key] = value

root = XmlNode()

# This won't raise, even though we don't define any of these members!
print(root.a)
print(root.b)
print(root.c)
root.c = 10
print(root.c)

# this will raise
print (xmlDrootata.d)
```

Let's break this down:
- There exists a dictionary within the class instance that contains some data
- We override \__get__ and \__setitem__ to catch "bad" invocations of non-existent member of the XmlData class
- When root.a is invoked, the interpreter makes a call into \__get__ because member a does not exist
- Before deciding to raise an exception, we see if member a is in our data dictionary.  If it is, we return the data
pointed to by a.  If it's not, we raise a ValueError just like what would be raised if we had not overridden \__get__
in the first place.
- Same goes with \__setitem__.  Only here, we have to take some care not to trigger a recursive loop.  If the member
being set is an actual defined member of the class, then we need to call super().\__setitem__().  The only thing we are
trying to override is access of the data dictionary member, all other member invocations we can pass along to the super.
And, as a little exercise, you can see what happens if you do try to set pre-defined data members within \__setitem__.
It ends up being a recursive loop that eventually blows the callstack.


So, lets change the XmlNode class slightly and make the point of the post obvious.  There are some  deficiencies in the
code below which will be fixed later in the post.  Ignore them for now.

```python
# xmlnode.py

class XmlNode:
    def __init__(self, path_to_xml_file, attr_prefix='attr_'):
        # child nodes
        self.nodes = dict(list())

        # attributes of the node
        self.attributes = {}

        # text of the node
        self.text = None

    def __get__(self, key):
        # caller is trying to get an attribute
        if key.startswith(attr_prefix):
            # trim the prefix
            key = key.replace(attr_prefix, '')

            # invalid key
            if key not in attributes:
                raise ValueError(key)

             return self.attributes[key]

        # caller is trying to get a node
        else:
            # invalid key
            if key not in self.nodes:
                raise ValueError(key)

            return self.nodes[key]

    def __setitem__(self, key, value):
        # catch valid members here and defer to super
        if key in self.__all__ or key in ['nodes', 'attributes', 'text']:
            return super().__setitem__(key, value)

        # caller is trying to set attributes
        if key.startswith(attr_prefix):
            # trim the prefix
            key = key.replace(attr_prefix, '')

            # invalid key
            if key not in attributes:
                raise ValueError(key)

            self.attributes[key] = value

        # this block here is the deficiency,  we'll fix it later.  In
        # short, based on the data present in the class, it doesn't make
        # sense to set nodes directly.  It would be a little hard to
        # maintain on the callers end as we expect the node key to point
        # to a list of nodes.
        else:
            # invalid key
            if key not in self.nodes:
                raise ValueError(key)

            self.nodes[key] = value
```
```python
# main.py
from xmlnode import XmlNode

root = XmlNode('/path/to/ConfigFile.xml')
# Node acces returns a list, and .xsd file guarantees there must be one
# and only one, so safe to access index 0.
parameterNode = root.Parameters[0]

# direct attribute access
print (parameterNode.attr_timeout)
print (parameterNode.attr_runtimeDataPath)

parameterNode.attr_timeout = "2000"
print (parameterNode.attr_timeout)
```