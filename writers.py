# -*- coding: utf-8 -*-
import os
import codecs
from annotation import Entity,Event

class AnnWriter:
    def __init__(self):
        self.entityFormat = u'{0}\t{1} {2} {3}\t{4}\n'
        self.eventFormat = u'{0}\t{1}:{2} {3}\n'

    def write(self,path,filename,annotation):
        line = u''
        filepath = os.path.join(path,filename)
        f = codecs.open(filepath,'w+','utf-8')

        for k,t in annotation['T'].iteritems():
            line = self.entityFormat.format(t.id,t.type,t.start,t.end,t.text)
            f.write(line)

        for k,e in annotation['E'].iteritems():
            args = [a[0]+':'+a[1].id for a in e.args]
            if len(args) == 0:
                continue
            args = ' '.join(args)                        
            line = self.eventFormat.format(e.id,e.type,e.triggerId,args)
            f.write(line)

        f.close()

            


