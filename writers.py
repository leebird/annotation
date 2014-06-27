# -*- coding: utf-8 -*-
import os
import codecs
from annotation import Entity,Event

class BionlpWriter(object):
    def __init__(self):
        self.entityFormat = u'{0}\t{1} {2} {3}\t{4}\n'
        self.eventFormat = u'{0}\t{1}:{2} {3}\n'    

    def entity_line(self,t):
        return self.entityFormat.format(t.id,t.type,t.start,t.end,t.text)

    def event_line(self,e):
        args = [a[0]+':'+a[1].id for a in e.args]
        args = ' '.join(args).strip()
        if len(args) > 0:
            return self.eventFormat.format(e.id,e.type,e.triggerId,args)
        else:
            return None

class AnnWriter(BionlpWriter):
    def __init__(self):
        super(AnnWriter,self).__init__()

    def write(self,path,filename,annotation):
        filepath = os.path.join(path,filename)
        f = codecs.open(filepath,'w+','utf-8')

        for k,t in annotation['T'].iteritems():
            line = self.entity_line(t)
            f.write(line)

        for k,e in annotation['E'].iteritems():
            line = self.event_line(e)
            f.write(line)

        f.close()

class A1A2Writer:
    def __init__(self):
        super(A1A2Writer,self).__init__()

    def write(self,a1path,a1file,a2path,a2file,annotation):
        triggerId = []
        
        entities = annotation['T']
        events = annotation['E']

        filepath = os.path.join(a2path,a2file)
        f = codecs.open(filepath,'w+','utf-8')
        
        for k,e in events.iteritems():
            if e.triggerId not in triggerId:
                triggerId.append(e.triggerId)
                trigger = entities[e.triggerId]
                line = self.entity_line(trigger)
                f.write(line)

            line = self.event_line(e)
            if line is not None:
                f.write(line)
            
        f.close()

        filepath = os.path.join(a1path,a1file)
        f = codecs.open(filepath,'w+','utf-8')

        for k,t in entities.iteritems():
            if t.id not in triggerId:
                line = self.entity_line(t)
                f.write(line)
        f.close()

class HtmlWriter:
    def __init(self):
        pass
