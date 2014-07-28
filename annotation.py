# -*- coding: utf-8 -*-

class Base(object):
    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)    

class Entity(Base):

    linestart = u'T'

    def __init__(self,tid,typing,start,end,text):
        self.id = tid
        self.type = typing
        self.start = start
        self.end = end
        self.text = text
        self.tmpl = u'{0}_{1}_{2}_{3}_{4}'

    def __unicode__(self):
        return self.tmpl.format(self.id,self.type,self.start,self.end,self.text)

    '''
    only compare type, start, end and text
    '''
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.type == other.type and 
                    self.start == other.start and 
                    self.end == other.end and 
                    self.text == other.text)
        else:
            return False

class Event(Base):

    linestart = u'E'

    def __init__(self,tid,typing,triggerId,args):
        self.id = tid
        self.type = typing
        self.trigger = trigger
        self.args = args
        self.tmpl = u'{0}_{1}_{2}_{3}'

    def __unicode__(self):
        return self.tmpl.format(self.id,self.type,self.trigger,self.args)

    '''
    only compare type, trigger and args
    '''
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.type == other.type and 
                    self.trigger == other.trigger and 
                    set(self.args) == set(other.args))
        else:
            return False

class Relation(Base):

    linestart = u'R'

    def __init__(self,rid,typing,arg1,arg2):
        self.id = rid
        self.type = typing
        self.arg1 = arg1
        self.arg2 = arg2
        self.tmpl = u'{0}_{1}_{2}_{3}'

    def __unicode__(self):
        return self.tmpl.format(self.id,self.type,self.arg1,self.arg2)

    '''
    only compare type, arg1 and arg2
    '''
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.type == other.type and 
                    self.arg1 == other.arg1 and 
                    self.arg2 == other.arg2)
        else:
            return False

class Annotation(Base):
    def __init__(self):
        self.entities = {}
        self.events = {}
        self.relations = {}
        self.tid = 1
        self.eid = 1
        self.rid = 1
        self.tidtmpl = u'T{}'
        self.eidtmpl = u'E{}'
        self.ridtmpl = u'R{}'
        self.tmpl = u'Annotation: {} entities, {} events, {} relations'

    def __unicode__(self):
        return self.tmpl.format(len(self.entities),len(self.events),len(self.relations))

    def get_entities(self):
        return self.entities

    def get_events(self):
        return self.events

    def get_relations(self):
        return self.relations

    def get_entity(self,tid):
        if self.entities.has_key(tid):
            return self.entities.tid

    def get_event(self,eid):
        if self.events.has_key(eid):
            return self.events[eid]

    def get_relation(self,rid):
        if self.relations.has_key(rid):
            return self.relations[rid]

    def add_entity(self,typing,start,end,text):
        tid = self.tidtmpl(self.tid)
        entity = Entity(tid,typing,start,end,text)
        self.entities[tid] = entity
        self.tid += 1
        return entity
        
    def add_event(self,typing,trigger,args):
        for arg in args:
            arg[1] = self.get_entity(arg[1])
        eid = self.eidtmpl.format(self.eid)
        event = Event(eid,typing,trigger,args)
        self.events[eid] = event
        self.eid += 1
        return event

    def add_relation(self,typing,arg1,arg2):
        rid = self.ridtmpl(self.rid)
        relation = Relation(rid,typing,arg1,arg2)
        self.relations[rid] = relation
        self.rid += 1
        return relation

    def add_exist_entity(self,tid,typing,start,end,text):
        entity = Entity(tid,typing,start,end,text)
        self.entities[tid] = entity
        return entity

    def add_exist_event(self,eid,typing,trigger,args):
        event = Event(eid,typing,trigger,args)
        self.events[eid] = event
        return event

    def add_exist_relation(self,rid,typing,arg1,arg2):
        relation = Relation(rid,typing,arg1,arg2)
        self.relations[rid] = relation
        return relation

    def has_entity(self,entity):
        if entity in self.entities.value():
            return True
        return False

    def has_entity_prop(self,typing,start,end,text):
        entity = Entity(None,typing,start,end,text)
        if entity in self.entities.values():
            return True
        return False

    def has_event(self,event):
        if event in self.events.value():
            return True
        return False

    def has_event_prop(self,typing,trigger,args):
        for arg in args:
            arg[1] = self.get_entity(arg[1])
        event = Event(None,typing,trigger,args)
        if event in self.events.value():
            return True
        return False

    def has_relation(self,relation):
        if relation in self.relations.value():
            return True
        return False

    def has_relation_prop(self,typing,arg1,arg2):
        relation = Relation(None,typing,arg1,arg2)
        if relation in self.relations.value():
            return True
        return False

    
