# -*- coding: utf-8 -*-

class Entity:    
    def __init__(self,tid,typing,start,end,text):
        self.id = tid
        self.type = typing
        self.start = start
        self.end = end
        self.text = text
        self.tmpl = u'{}_{}_{}_{}_{}'

    def __unicode__(self):
        return self.tmpl.format(self.id,
                                self.type,
                                self.start,
                                self.end,
                                self.text)

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

class Event:
    def __init__(self,tid,typing,triggerId,args):
        self.id = tid
        self.type = typing
        self.triggerId = triggerId
        self.args = args
        self.tmpl = u'{}_{}_{}_{}'

    def __unicode__(self):
        return self.tmpl.format(self.id,self.type,
                                self.triggerId,self.args)

    def __repr__(self):
        return self.__unicode__()

        
class Relation:
    def __init__(self,rid,typing,arg1,arg2):
        self.id = rid
        self.type = typing
        self.arg1 = arg1
        self.arg2 = arg2
        self.tmpl = u'{}_{}_{}_{}'

    def __unicode__(self):
        return self.tmpl.format(self.id,self.type,
                                self.arg1,self.arg2)

    def __repr__(self):
        return self.__unicode__()
