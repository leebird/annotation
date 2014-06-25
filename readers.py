# -*- coding: utf-8 -*-
import sys
import re
import os
import codecs
import itertools
from pprint import pprint as pp
from annotation import Entity,Event

class ReaderError(Exception):
    def __init__(self,msg):
        self.msg = msg
    
    def __str__(self):
        return repr(self.msg)

class Reader(object):
    def __init__(self,path,filename):
        self.path = path
        self.filename = filename
        self.filepath = os.path.join(path,filename)
        self.reBracket = re.compile(r'<.*?>')
        self.reBrace = re.compile(r'\{.*?\}')

    def parse(self):
        raise NotImplementedError('Reader')

    def remove_bracket(self,text):
        return re.sub(self.reBracket,'',text)

    def remove_brace(self,text):
        return re.sub(self.reBrace,'',text)

    def remove_tags(self,text):
        return self.remove_bracket(self.remove_brace(text))

class AnnReader(Reader):
    def __init__(self,*args):
        super(AnnReader,self).__init__(*args)
        self.annotation = {}
        
    def parse_entity(self,line):
        fields = line.split('\t')
        info = fields[1].split(' ')            
        tid = fields[0]
        text = fields[2]
        typing = info[0]
        start = int(info[1])
        end = int(info[2])
        return Entity(tid,typing,start,end,text)

    def parse_event(self,line):
        fields = line.split('\t')
        tid = fields[0]
        info = fields[1].split(' ')        
        typing = info[0].split(':')
        typeId = typing[1]
        typeText = typing[0]        
        args = []

        for arg in info[1:]:
            argInfo = arg.split(':')
            argType = argInfo[0]
            argId = argInfo[1]
            args.append((argType,argId))

        return Event(tid,typeText,typeId,args)

        
    def parse(self):
        f = codecs.open(self.filename,'r','utf-8')
        annotation = {'T':{},'E':{}}

        for line in f:
            line = line.strip()
            if line.startswith('T'):
                entity = self.parse_entity(line)
                annotation['T'][entity.id] = entity
            elif line.startswith('E'):
                event = self.parse_event(line)
                annotation['E'][event.id] = event
            else:
                continue
            #raise Exception('can not parse: '+line)
            
        f.close()
        return annotation
    
class RlimsReader(Reader):
    def __init__(self,*args):
        super(RlimsReader,self).__init__(*args)
        self.separator = '{NP_1}PMID'
        self.hdOutput = 'OUTPUT '
        self.hdTrigger = 'PTM ='
        self.hdInducer = 'Inducer ='
        self.hdKinase = 'Kinase ='
        self.hdSubstrate = 'Substrate ='
        self.hdSite = 'Site ='
        self.hdNorm = 'NORM='
        self.hdSynonym = 'SYNONYM='
        self.rePMID = re.compile(r'PMID{/NP_1}.*?{CP_2}([0-9]*?){/CP_2}')
        self.reTrigger = re.compile(r'\(\{(.*?)\};(.*?)\)')
        self.reArg = re.compile(r'\{(.*?)\}(.*?)\{/(.*?)\}')
        
        self.reAmino = re.compile(r'^\(\{(.*?)\}(.*?)\{/(.*?)\};')
        self.reSite = re.compile(r';\{(.*?)\}(.*?)\{/(.*?)\};')
        self.reSiteOther = re.compile(r';\{(.*?)\}(.*?)\{/(.*?)\}\)$')

        self.reTagged = re.compile(r'(\{(.*?)\})(.*?)(\{/.*?\})')

        self.status = 0
        self.mask = {11:'kinase',
                     12:'substrate',
                     13:'site',
                     14:'trigger',
                     15:'inducer'}
        
    def split(self,text):
        blocks = text.split(self.separator)
        blocks = [self.separator+b for b in blocks[1:]]
        return blocks
    
    def init_output(self):
        output = {'trigger':[],
                  'kinase':[],
                  'inducer':[],
                  'substrate':[],
                  'site':[]}                
        return output

    def _parse(self,blocks):
        res = {}
        for b in blocks:
            lines = b.split('\n')
            #empty line is used to seperate outputs & sentences
            if len(lines) == 0:
                continue

            match = self.rePMID.search(lines[0])
            if match:
                self.pmid = match.group(1)
            else:
                self.pmid = 'unknown'
                raise PMIDUnknown(lines[0])

            res[self.pmid] = self.parse_block(lines[1:])
            sens = res[self.pmid]['sentence']
            res[self.pmid]['tag_indices'] = self.index_tag(sens)

        return res

    def parse_block(self,lines):
        res = {'sentence':[],'output':[],'norm':[]}
        for l in lines:
            self.process_line(l,res)
        return res

    def process_line(self,l,res):
        if l.startswith(self.hdOutput):
            self.status = 1
            output = self.init_output()
            res['output'].append(output)
        elif l.startswith(self.hdNorm):
            self.status = 2
            res['norm'].append([l])
        elif l.startswith(self.hdSynonym):
            self.status = 3
            res['norm'][-1].append(l)
        elif l.startswith(self.hdKinase):
            self.status = 11
        elif l.startswith(self.hdSubstrate):
            self.status = 12
        elif l.startswith(self.hdSite):
            self.status = 13
        elif l.startswith(self.hdTrigger):
            self.status = 14
        elif l.startswith(self.hdInducer):
            self.status = 15
        elif len(l.strip()) == 0:
            self.status = 0

        if self.status == 0:
            if len(l.strip()) > 0:
                res['sentence'].append(l)
        elif self.status > 10:
            tokens = self.parse_line(l)
            needle = self.mask[self.status]
            if tokens is not None:
                res['output'][-1][needle].append(tokens)
    
    def parse_line(self,line):
        res = None
        if self.status == 14:
            match = self.reTrigger.search(line)
            if match:
                tag = match.group(1)
                text = match.group(2)
                text = self.remove_bracket(text)
                res = (tag,text)
        elif self.status == 13:
            tag = None
            text = None
            amino = None
            siteOther = None
            match = self.reSite.search(line)
            if match:
                tag = match.group(1)
                text = match.group(2)
                text = self.remove_bracket(text)
            match = self.reAmino.search(line)
            if match:
                amino = match.group(2)
            match = self.reSiteOther.search(line)
            if match:
                if text is None:
                    text = match.group(2)
                if tag is None:
                    tag = match.group(1)
                    
            if tag is not None and text is not None:                
                res = (tag,text,amino)

        elif self.status == 11 or self.status == 12 \
                or self.status == 15:
            match = self.reArg.search(line)
            if match:
                tag = match.group(1)
                text = match.group(2)
                text = self.remove_bracket(text)
                res = (tag,text)
        return res

    def parse(self):
        f = codecs.open(self.filepath,'r','utf-8')
        text = f.read()
        f.close()
        blocks = self.split(text)
        res = self._parse(blocks)
        return res

    def index_tag(self,taggedSens):
        tagIndices = {}
        sens = [self.remove_bracket(s) for s in taggedSens]
        braced = ''.join(sens)
        sens = [self.remove_tags(s) for s in taggedSens]
        text = ''.join(sens)        
        match = self.reTagged.search(braced)
        while(match):            
            match = self.reTagged.search(braced)
            tag = match.group(2)
            openTag = match.group(1)
            closeTag = match.group(4)
            phrase = match.group(3)
            start = match.start(1)
            end = start + len(phrase)
            tagIndices[tag] = (start,end,phrase)
            braced = braced.replace(openTag,'')
            braced = braced.replace(closeTag,'')
            match = self.reTagged.search(braced)
        return tagIndices
        
class RlimsVerboseReader(RlimsReader):
    def __init__(self,*args):
        super(RlimsVerboseReader,self).__init__(*args)        
        self.hdMethod = '\tMethod='
        self.reMethod = re.compile(r'\[(.*?)\]')
        self.isMethod = False
        self.reTag = re.compile(r'\{/(.*?)\}')

    def init_output(self):
        output = {'trigger':[],
                  'kinase':[],
                  'inducer':[],
                  'substrate':[],
                  'site':[],
                  'trigger_med':[],
                  'kinase_med':[],
                  'inducer_med':[],
                  'substrate_med':[],
                  'site_med':[]}
        return output

    def parse_line(self,line):
        if self.isMethod:
            match = self.reMethod.search(line)
            if match:
                med = match.group(1)
            else:
                return None

            tokens = med.split('\r')
            length = len(tokens)
            if length == 0:
                return None

            phrase = self.remove_tags(tokens[0])
            match = self.reTag.search(tokens[0])
            if match:
                tag = match.group(1)
            else:
                raise NPPhraseNotFound(tokens[0])

            res = []
            if length > 1:
                for t in tokens[1:]:
                    subtokens = t.split('|')
                    position = subtokens[0].split('..')
                    variances = subtokens[1:]
                    variances = [self.remove_tags(v) for v in variances]
                    start = int(position[0])
                    end = int(position[1])
                    res.append((tag,phrase,start,end,variances))
            else:
                res.append((tag,phrase,-1,-1,[phrase]))
            return res
        else:
            return super(RlimsVerboseReader,self).parse_line(line)
        
    def process_line(self,l,res):
        if l.startswith(self.hdMethod):
            self.isMethod = True
            tokens = self.parse_line(l)
            needle = self.mask[self.status]+'_med'
            if tokens is not None:
                res['output'][-1][needle] += tokens
        elif l.startswith('\t'):
            pass
        else:
            self.isMethod = False
            super(RlimsVerboseReader,self).process_line(l,res)            

    def toBionlp(self,res):
        ann = {}
        for pmid,v in res.iteritems():
            output = v['output']
            sens = v['sentence']
            tagIdx = v['tag_indices']
            
            sens = [self.remove_tags(s) for s in sens]
            abstract = ''.join(sens)

            self.entities = {}
            self.events = {}
            self.entityIdx = 1
            self.eventIdx = 1

            for o in output:
                o = self.fake_method(o,'trigger')
                o = self.fake_method(o,'kinase')
                o = self.fake_method(o,'substrate')
                o = self.fake_method(o,'site')

                tri = o['trigger']
                triMed = o['trigger_med']
                sub = o['substrate']
                subMed = o['substrate_med']
                site = o['site']
                siteMed = o['site_med']

                
                indicesTri = self.reindex(tri,triMed,tagIdx)
                indicesSub = self.reindex(sub,subMed,tagIdx)
                indicesSite = self.reindex(site,siteMed,tagIdx,isSite=True)
                
                '''
                indicesTri = self.reindex_method(triMed,tagIdx)
                indicesSub = self.reindex_method(subMed,tagIdx)
                indicesSite = self.reindex_method(siteMed,tagIdx)
                '''

                if(len(indicesSub) == 0):
                    continue
                
                triggers = self.add_entities(indicesTri,'Phosphorylation')
                proteins = self.add_entities(indicesSub,'Protein')
                sites = self.add_entities(indicesSite,'Entity')

                args = {'Theme':proteins,'Site':sites}
                self.add_events(triggers[0],args,'Phosphorylation')
            
            self.rehash_entities()
            self.rehash_events()
            ann[pmid] = {'T':self.entities,'E':self.events,'text':abstract}
            
        return ann

    def fake_method(self,output,needle):
        '''
        add method lines if there is none
        '''
        if len(output[needle+'_med']) == 0:
            sites = output[needle]
            fake = []
            for s in sites:
                fake.append((s[0],s[1],-1,-1,[s[1]]))
            output[needle+'_med'] = fake            
        return output

    def add_events(self,trigger,args,eventType):
        done = False

        for t in args['Theme']:
            for s in args['Site']:
                arg = (('Theme',t),('Site',s))
                done = True

                if self.events.has_key((trigger.id,arg)):
                    continue

                eid = 'E' + str(self.eventIdx)
                self.eventIdx += 1
                
                event = Event(eid,eventType,trigger.id,arg)
                self.events[(trigger.id,arg)] = event


        if not done:
            for t in args['Theme']:
                arg = (('Theme',t),)

                if self.events.has_key((trigger.id,arg)):
                    continue

                eid = 'E' + str(self.eventIdx)
                self.eventIdx += 1
                event = Event(eid,eventType,trigger.id,arg)
                self.events[(trigger.id,arg)] = event
                done = True

    def rehash_entities(self):
        '''
        change key from position tuple to entity index, e.g., T1
        '''
        entities = {}
        for t in self.entities.values():
            entities[t.id] = t
        del self.entities
        self.entities = entities

    def rehash_events(self):
        '''
        change key from tuple to event index, e.g., E1
        '''
        events = {}
        for e in self.events.values():
            events[e.id] = e
        del self.events
        self.events = events

    def add_entities(self,indices,entityType):
        '''
        create and add new entities
        indices format:
        [(start,end,text),...]
        '''
        res = []
        for i in indices:
            start = i[0]
            end = i[1]
            text = i[2]
            if not self.entities.has_key((start,end)):
                tid = 'T' + str(self.entityIdx)
                self.entityIdx += 1
                entity = Entity(tid,entityType,start,end,text)
                self.entities[(start,end)] = entity
            res.append(self.entities[(start,end)])

        return res
            
    
    def reindex(self,annos, meds, tagIdx, isSite = False):
        '''
        update position index for various situations
        1. position in method line is present
        2. position is -1
        3. the extracted span not matched with the argument
        '''
        res = []
        for a,m in itertools.product(annos,meds):
            # check the phrase tags, they should be the same
            if a[0] != m[0]:
                continue
            
            # check the annotations, they should be the same
            if not isSite and a[1] != m[-1][-1]:
                continue                

            # get information from annotation line and method line
            tag = a[0]

            '''
            get argument from method line, instead of annotation line
            this can fix the site case
            '''
            # argument = a[1]
            argument = m[-1][0]

            phrase = m[1]
            inStart = m[2]
            inEnd = m[3]+1
            tagStart,tagEnd,phrase = tagIdx[tag]

            if inStart == -1:
                '''
                search argument in phrase if there is no position
                information in the method line
                '''
                inStart = phrase.find(argument)
                start = tagStart + inStart
                end = start + len(argument)
            else:
                '''
                recount position if there is position information
                in the method line
                '''
                inStart,inEnd = self.recount(phrase,inStart,inEnd)
                extracted = phrase[inStart:inEnd]
                if extracted != argument:
                    '''
                    search argument in the phrase if the position
                    is not matched with the argument
                    '''
                    inStart = phrase.find(argument)
                    start = tagStart + inStart
                    end = start + len(argument)
                else:
                    start = tagStart + inStart
                    end = tagStart + inEnd

            res.append((start,end,argument))

        return res


    def reindex_method(self, meds, tagIdx):
        '''
        update position index for various situations
        1. position in method line is present
        2. position is -1
        3. the extracted span not matched with the argument
        '''
        res = []
        for m in meds:

            # get information from the method line
            print m

            tag = m[0]
            argument = m[-1][0]
            phrase = m[1]
            inStart = m[2]
            inEnd = m[3]+1
            tagStart,tagEnd,phrase = tagIdx[tag]

            if inStart == -1:
                '''
                search argument in phrase if there is no position
                information in the method line
                '''
                inStart = phrase.find(argument)
                start = tagStart + inStart
                end = start + len(argument)
            else:
                '''
                recount position if there is position information
                in the method line
                '''
                inStart,inEnd = self.recount(phrase,inStart,inEnd)
                extracted = phrase[inStart:inEnd]
                if extracted != argument:
                    '''
                    search argument in the phrase if the position
                    is not matched with the argument
                    '''
                    inStart = phrase.find(argument)
                    start = tagStart + inStart
                    end = start + len(argument)
                else:
                    start = tagStart + inStart
                    end = tagStart + inEnd
            
            if (start,end,argument) not in res:
                res.append((start,end,argument))

        return res

    def recount(self,text,start,end):
        '''
        update index based on actual string, including space
        RLIMS-P verbose output file's original index excludes
        the space.
        '''
        for i,c in enumerate(list(text)):
            if c == ' ' and i <= start:
                start += 1
            if c == ' ' and i < end:
                end += 1
        return start,end
                

class Rlims2Reader(Reader):
    def __init__(self,*args):
        super(Rlims2Reader,self).__init__(*args)
        self.pmid = None
        self.starter = 'date'
        self.rePMID = re.compile(r'PMID{/NP_1}.*?{CP_2}([0-9]*?){/CP_2}')
        self.startPoints = None

    def parse(self):        
        res = {}
        f = codecs.open(self.filepath,'r','utf-8')
        for l in f:
            self.parse_line(l,res)
        f.close()
        self.toBionlp(res)

    def parse_line(self,l,res):
        if l.startswith('O'):
            idx = int(l[1:4])
            mid = l.find(' ',5)
            hd = l[5:mid]
            if hd == self.starter:
                res[self.pmid]['output'].append({})
            res[self.pmid]['output'][-1][hd] = l[mid:].strip()
        elif l.startswith('S'):
            idx = int(l[1:4])
            sentence = l[4:].strip()
            if idx == 0:
                match = self.rePMID.search(sentence)
                if match:
                    self.pmid = match.group(1)
                    res[self.pmid] = {'output':[],
                                      'sentence':[]}
                    return
                else:
                    raise PMIDNotFoundError(l)
            res[self.pmid]['sentence'].append(sentence)            
        else:
            pass

    def toBionlp(self,res):
        for pmid,v in res.iteritems():
            self.entityIdx = 1
            self.eventIdx = 1
            self.entities = {}
            self.events = {}

            self.sens = [self.remove_tags(s) for s in v['sentence']]
            lens = [len(s) for s in self.sens]
            self.abstract = ' '.join(self.sens)

            self.startPoints = [0]
            for l in lens[:-1]:
                self.startPoints.append(l+1+self.startPoints[-1])

            annotation = v['output']            
            for a in annotation:
                trigger = self.parse_annotation(a['trigger'])
                kinases = self.parse_annotation(a['kinase'])
                substrates = self.parse_annotation(a['substrate'])
                sites = self.parse_annotation(a['site'])

                trigger = self.get_positions(trigger)
                kinases = self.get_positions(kinases)
                substrates = self.get_positions(substrates)
                sites = self.get_positions(sites)

                self.add_entities(trigger,'Phosphorylation')
                self.add_entities(kinases,'Agent')
                self.add_entities(substrates,'Theme')
                self.add_entities(sites,'Entity')
                      
                if len(sites) == 0:
                    combine = [(tri,sub) for tri in trigger 
                               for sub in substrates]
                else:
                    combine = [(tri,sub,site) for tri in trigger 
                               for sub in substrates 
                               for site in sites]

                if len(combine) == 0:
                    continue

                self.add_events(combine,'Phosphorylation')
                self._toBionlp()

    def _toBionlp(self):
        entityFormat = '{}\t{} {} {}\t{}'
        eventOneArg = '{}\t{}:{} {}:{}'
        eventTwoArgs = '{}\t{}:{} {}:{} {}:{}'
        '''
        entitiesFormated = [entityFormat.format(t) for t in self.entities.values()]
        eventsFormated = [eventOneArg.format(e) for e in self.events.values() 
                          if len(e) == 2]
        eventsFormated += [eventTwoArg.format(e) for e in self.events.values() 
                           if len(e) == 3]

        merged = entitiesFormated + eventsFormated
        res = '\n'.join(merged)
        print res
        '''

    def parse_annotation(self,annotation):
        annotation = annotation.strip()
        if len(annotation) == 0:
            return ()
        args = annotation.split('|')
        args = [arg.split(' ') for arg in args]
        args = [(int(a[0]),int(a[1]),int(a[2])) for a in args]
        return args

    def add_entities(self,entities,entityRole):
        for t in entities:
            self.add_entity(t,entityRole)
                
    def add_entity(self,entity,entityRole):
        if not self.entities.has_key(entity):
            tIdx = 'T'+str(self.entityIdx)
            self.entityIdx += 1
            text = self.abstract[entity[0]:entity[1]]
            self.entities[entity] = (tIdx,entityRole)+entity+(text,)

    def add_events(self,events,eventType):
        for e in events:
            self.add_event(e,eventType)

    def add_event(self,event,eventType):
        if not self.events.has_key(event):
            eIdx = 'E'+str(self.eventIdx)
            self.eventIdx += 1
            self.events[event] = (eIdx,eventType)+event

    def get_positions(self,oldIndices):
        return [self.get_position(i) for i in oldIndices]
        
    def get_position(self,oldIndex):
        base = self.startPoints[oldIndex[0]-1]
        sen = self.sens[oldIndex[0]-1]
        start = oldIndex[1]
        length = oldIndex[2]

        for i,c in enumerate(list(sen)):
            if i < start:
                if c == ' ':
                    start += 1
                continue
            
            if c == ' ':
                length += 1

            if i-start >= length:
                break

        start = base + start
        end = start+length
        return (start,end)
        