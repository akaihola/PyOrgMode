
# -*- encoding: utf-8 -*-
##############################################################################
#
#    PyOrgMode, a python module for treating with orgfiles
#    Copyright (C) 2010 Jonathan BISSON (bissonjonathan on the google thing).
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

"""
The PyOrgMode class is able to read,modify and create orgfiles. The internal
representation of the file allows the use of orgfiles easily in your projects.
"""

import re
import string
import copy
import time

class OrgPlugin:
    """
    Generic class for all plugins
    """
    def __init__(self):
        self.treated = True
    def treat(self,current,line):
        self.treated = True
        return self._treat(current,line)
    def _treat(self,current,line):
        self.treated = False
        return current
    def close(self,current):
        self.treated = True
        return self._close(current)
    def _close(self,current):
        self.treated = False
        return current

class OrgElement:
    """
    Generic class for all Elements excepted text and unrecognized ones
    """ 
    def __init__(self):
        self.content=[]
        self.parent=None
        self.level=0
    def append(self,element):
        # TODO Check validity
        self.content.append(element)
        # Check if the element got a parent attribute
        # If so, we can have childrens into this element
        if hasattr(element,"parent"):
            element.parent = self
        return element

class Clock(OrgPlugin):
    """Plugin for Clock elements"""
    def __init__(self):
        OrgPlugin.__init__(self)
        self.regexp = re.compile("(?:\s*)CLOCK:(?:\s*)\[(.*)\]--\[(.*)\].*=>\s*(.*)")
    def _treat(self,current,line):
        clocked = self.regexp.findall(line)
        if clocked:
            current.append(self.Element(clocked[0][0], clocked[0][1],clocked[0][2]))
        else:
            self.treated = False
        return current
   
    class Element(OrgElement):
        """Clock is an element taking into account CLOCK elements"""
        TYPE = "CLOCK_ELEMENT"
        def __init__(self,start="",stop="",duration=""):
            OrgElement.__init__(self)
            self.dateformat = "%Y-%m-%d %a %H:%M"
            self.timeformat = "%H:%M"
            self.start = self.convert_date(start)
            self.stop = self.convert_date(stop)
            self.duration = time.strptime(duration,self.timeformat)
        def convert_date(self,date):
            """Used to convert dates from a different TZ"""
            return time.strptime(re.sub("\s(.*)\s"," ",date),"%Y-%m-%d %H:%M")
        def format_duration(self,duration):
            """Used to format durations identically to org-mode"""
            timestr = time.strftime(self.timeformat,duration)
            if timestr[0] == '0':
                return timestr[1:]
            return timestr
        def __str__(self):
            """Outputs the Clock element in text format (e.g CLOCK: [2010-11-20 Sun 19:42]--[2010-11-20 Sun 20:14] =>  0:32)"""
            return "CLOCK: [" + time.strftime(self.dateformat,self.start) + "]--["+ time.strftime(self.dateformat,self.stop) + "] =>  "+self.format_duration(self.duration)+"\n"

class Schedule(OrgPlugin):
    """Plugin for Schedule elements"""
    def __init__(self):
        OrgPlugin.__init__(self)
        self.regexp = re.compile("(?:\s*)(SCHEDULED|DEADLINE)(?::\s*)(<.*?>)(?:\s.*|$)")
    def _treat(self,current,line):
        scheduled = self.regexp.findall(line)
        if scheduled:
            current.append(self.Element(scheduled[0][0], scheduled[0][1]))
        else:
            self.treated = False
        return current

    class Element(OrgElement):
        """Schedule is an element taking into account DEADLINE and SCHEDULED elements"""
        DEADLINE = 1
        SCHEDULED = 2
        TYPE = "SCHEDULE_ELEMENT"
        def __init__(self,type="",date=""):
            OrgElement.__init__(self)
            self.date = date
            self.type = 0
            if type == "DEADLINE":
                self.type = self.DEADLINE
            elif type == "SCHEDULED":
                self.type = self.SCHEDULED

        def __str__(self):
            """Outputs the Schedule element in text format (e.g SCHEDULED: <2010-10-10 10:10>)"""
            if self.type == self.DEADLINE:
                output = "DEADLINE:"
            elif self.type == self.SCHEDULED:
                output = "SCHEDULED:"
            return output + " " + self.date + "\n"

class Drawer(OrgPlugin):
    """A Plugin for drawers"""
    def __init__(self):
        OrgPlugin.__init__(self)
        self.regexp = re.compile("^(?:\s*?)(?::)(\S.*?)(?::)\s*(.*?)$")
    def _treat(self,current,line):
        drawer = self.regexp.search(line)
        if isinstance(current, Drawer.Element): # We are in a drawer
            if drawer:
                if drawer.group(1) == "END": # Ending drawer
                    current = current.parent
                elif drawer.group(2): # Adding a property
                    current.append(self.Property(drawer.group(1),drawer.group(2)))
            else: # Adding text in drawer
                current.append(line.rstrip("\n"))
        elif drawer: # Creating a drawer
            current = current.append(Drawer.Element(drawer.group(1)))
        else:
            self.treated = False
            return current
        return current # It is a drawer, change the current also (even if not modified)
    
    class Element(OrgElement):
        """A Drawer object, containing properties and text"""
        TYPE = "DRAWER_ELEMENT"
        def __init__(self,name=""):
            OrgElement.__init__(self)
            self.name = name
        def __str__(self):
            output = ":" + self.name + ":\n"
            for element in self.content:
                output = output + str(element) + "\n"
            output = output + ":END:\n"
            return output
    class Property(OrgElement):
        """A Property object, used in drawers."""
        def __init__(self,name="",value=""):
            OrgElement.__init__(self)
            self.name = name
            self.value = value
        def __str__(self):
            """Outputs the property in text format (e.g. :name: value)"""
            return ":" + self.name + ": " + self.value

class Table(OrgPlugin):
    """A plugin for table managment"""
    def __init__(self):
        OrgPlugin.__init__(self)
        self.regexp = re.compile("^\s*\|")
    def _treat(self,current,line):
        table = self.regexp.match(line)
        if table:
            if not isinstance(current,self.Element):
                current = current.append(self.Element())
            current.append(line.rstrip().strip("|").split("|"))
        else:
            if isinstance(current,self.Element):
                current = current.parent
            self.treated = False
        return current

    class Element(OrgElement):
        """
        A Table object
        """
        TYPE = "TABLE_ELEMENT"
        def __init__(self):
            OrgElement.__init__(self)
        def __str__(self):
            output = ""
            for element in self.content:
                output = output + "|"
                for cell in element:
                    output = output + str(cell) + "|"
                output = output + "\n"
            return output

class Closed(OrgPlugin):
    """Plugin for Closed elements"""
    def __init__(self):
        OrgPlugin.__init__(self)
        self.regexp = re.compile("\s*CLOSED:\s*\[(.*?)\]")
    def _treat(self,current,line):
        closed = self.regexp.findall(line)
        if closed:
            current.append(self.Element(closed[0]))
        else:
            self.treated = False
        return current

    class Element(OrgElement):
        """Closed is an element taking into account CLOSED elements"""
        TYPE = "CLOSED_ELEMENT"
        def __init__(self,timestamp=""):
            OrgElement.__init__(self)
            self.dateformat = "%Y-%m-%d %a %H:%M"
            self.timestamp = self.convert_date(timestamp)
        def convert_date(self,date):
            """Used to convert dates from a different TZ"""
            return time.strptime(re.sub("\s(.*)\s"," ",date),"%Y-%m-%d %H:%M")
        def __str__(self):
            """Outputs the Closed element in text format

            Example output:
            CLOSED: [2010-11-20 Sun 19:42]
            """
            timestamp = time.strftime(self.dateformat, self.timestamp)
            return "CLOSED: [%s]\n" % timestamp

class Node(OrgPlugin):
    def __init__(self):
        OrgPlugin.__init__(self)
        self.regexp = re.compile("^(\*+)\s*(\[.*\])?\s*(.*)$")
    def _treat(self,current,line):
        heading = self.regexp.findall(line)
        if heading: # We have a heading

            if current.parent :
                current.parent.append(current)
  
                  # Is that a new level ?
            if (len(heading[0][0]) > current.level): # Yes
                parent = current # Parent is now the current node
            else:
                parent = current.parent # If not, the parent of the current node is the parent
                # If we are going back one or more levels, walk through parents
                while len(heading[0][0]) < current.level:
                    current = current.parent
                    parent = current.parent
  
            # Creating a new node and assigning parameters
            current = Node.Element() 
            current.level = len(heading[0][0])
            current.heading = re.sub(":([\w]+):","",heading[0][2]) # Remove tags
            current.priority = heading[0][1]
            current.parent = parent
                  
                  # Looking for tags
            heading_without_links = re.sub(" \[(.+)\]","",heading[0][2])
            current.tags = re.findall(":([\w]+):",heading_without_links)
        else:
            self.treated = False
        return current
    def _close(self,current):
        # Add the last node
        if current.level>0:
            current.parent.append(current)

    class Element(OrgElement):
        # Defines an OrgMode Node in a structure
        # The ID is auto-generated using uuid.
        # The level 0 is the document itself
        TYPE = "NODE_ELEMENT"    
        def __init__(self):
            OrgElement.__init__(self)
            self.content = []       
            self.level = 0
            self.heading = ""
            self.priority = ""
            self.tags = []
          # TODO  Scheduling structure
  
        def __str__(self):
            output = ""
            
            if hasattr(self,"level"):
                output = output + "*"*self.level
  
            if self.parent is not None:
                output = output + " "
                if self.priority:
                    output = output + self.priority + " "
                output = output + self.heading
  
                for tag in self.tags:
                    output= output + ":" + tag + ":"
  
                output = output + "\n"
    
            for element in self.content:
                output = output + element.__str__()
  
            return output
        def append_clean(self,element):
            if isinstance(element,list):
                self.content.extend(element)
            else:
                self.content.append(element)
            self.reparent_cleanlevels(self)
        def reparent_cleanlevels(self,element=None,level=None):
            """
            Reparent the childs elements of 'element' and make levels simpler.
            Useful after moving one tree to another place or another file.
            """
            if element == None:
                element = self.root
            if hasattr(element,"level"):
                if level == None:
                    level = element.level
                else:
                    element.level = level

            if hasattr(element,"content"):
                for child in element.content:
                    if hasattr(child,"heading"):
                        print(child.heading)
                    print("Level: "+str(level)+" Id: "+hex(id(child))+" Type: "+child.TYPE)
                    if hasattr(child,"parent"):
                        child.parent = element
                        self.reparent_cleanlevels(child,level+1)

class DataStructure(OrgElement):
    """
    Data structure containing all the nodes
    The root property contains a reference to the level 0 node
    """
    root = None
    TYPE = "DATASTRUCTURE_ELEMENT"
    def __init__(self):
        OrgElement.__init__(self)
        self.plugins = []
        self.load_plugins(Table(),Drawer(),Node(),Schedule(),Clock(),Closed())
        # Add a root element
        # The root node is a special node (no parent) used as a container for the file
        self.root = Node.Element()
        self.root.parent = None
        self.level = 0

    def load_plugins(self,*arguments,**keywords):
        for plugin in arguments:
            self.plugins.append(plugin)
    def load_from_file(self,name):
        current = self.root
        file = open(name,'r')

        for line in file:
            
            for plugin in self.plugins:
                current = plugin.treat(current,line)
                if plugin.treated: # Plugin found something
                    treated = True
                    break;
                else:
                    treated = False
            if not treated and line is not None: # Nothing special, just content
                current.append(line)

        for plugin in self.plugins:
            current = plugin.close(current)
        file.close()

    def save_to_file(self,name,node=None):
        output = open(name,'w')
        if node == None:
            node = self.root
        output.write(str(node))
        output.close()
