# -*- coding: utf-8 -*-
import os
import codecs
import re
import json
from .annotate import *


class BionlpWriter(object):
    entity_format = u'{0}\t{1} {2} {3}\t{4}\n'
    event_format = u'{0}\t{1}:{2} {3}\n'
    relation_format = u'{0}\t{1} {2}\n'
    modification_format = u'{0}\t{1}\n'
    equiv_format = u'*\tEquiv {0}\n'
    
    def __init__(self):
        pass

    @staticmethod
    def has_trigger(relation):
        trigger = [arg for arg in relation.arguments if arg.role == 'Trigger']
        return len(trigger) > 0

    @staticmethod
    def get_trigger(relation):
        print('hahahaha')
        print(relation.arguments)
        trigger = [arg for arg in relation.arguments if arg.role == 'Trigger']
        return trigger[0].value if len(trigger) > 0 else None
    
    def entity_line(self, entity):
        """
        generate a line for an entity according to BioNLP format
        T1  Gene 0 3    BAD
        :param entity: an entity
        :type entity: Entity
        :return: a line containing entity information
        :rtype: str
        """
        entity_id = entity.id_
        if entity_id is None:
            return ''

        return self.entity_format.format(entity_id,
                                         entity.category,
                                         entity.start,
                                         entity.end,
                                         entity.text)

    def event_line(self, event):
        """
        generate a line for an event according to BioNLP format
        :param event: an event
        :type event: Relation
        :return: a line containing event information
        :rtype: str
        """
        args = [a.role + ':' + a.value.id_ for a in event.arguments]
        args = ' '.join(args).strip()
        event_id = event.id_

        if len(args) == 0 or event_id is None:
            return ''
        
        return self.event_format.format(event.id_,
                                        event.category,
                                        self.get_trigger(event).id_,
                                        args)

    def relation_line(self, relation):
        """
        generate a line for an relation according to BioNLP format
        :param relation: an relation (an event without trigger word)
        :type relation: Relation
        :return: a line containing relation information
        :rtype: str
        """
        args = [a.role + ':' + a.value.id_ for a in relation.arguments]
        args = ' '.join(args).strip()

        relation_id = relation.id_
        if relation_id is None:
            return ''

        return self.relation_format.format(relation.id_,
                                           relation.category,
                                           args)

    def modification_line(self, mod_id, mod_event):
        return self.modification_format.format(mod_id, mod_event)

    def bionlp_index(self, annotation):
        """add T1, E1 and R1-like indices to entities and events
        :return: None
        :rtype: None
        """

        def reindex(candidates, prefix):
            """
            reindex candidates with defined prefix
            :param candidates: a list of candidates (entities, events or relations)
            :type candidates: list
            :param prefix: the prefix for the candidate's id, e.g., 'T' for entity
            :type prefix: str
            :return: None
            :rtype: None
            """
            candidate_id_pattern = re.compile(prefix + r'([0-9]+)')
            existed_indices = []
            unindexed_candidates = []
            for candidate in candidates:
                candidate_id = candidate.id_
                if candidate_id is None:
                    unindexed_candidates.append(candidate)
                else:
                    match = candidate_id_pattern.match(candidate_id)
                    if match is None:
                        unindexed_candidates.append(candidate)
                    else:
                        candidate_number = int(match.group(1))
                        existed_indices.append(candidate_number)

            if len(existed_indices) > 0:
                existed_indices.sort()
                next_index = existed_indices.pop(-1) + 1
            else:
                next_index = 1

            for candidate in unindexed_candidates:
                candidate.id_ = prefix + str(next_index)
                next_index += 1

        reindex(annotation.entities, 'T')
        reindex(annotation.get_relation_with_trigger(), 'E')
        reindex(annotation.get_relation_no_trigger(), 'R')


class AnnWriter(BionlpWriter):
    def __init__(self):
        super(AnnWriter, self).__init__()

    def write(self, filepath, annotation):
        f = codecs.open(filepath, 'w+', 'utf-8')
        self.bionlp_index(annotation)
        modifications = []
        
        for t in annotation.entities:
            line = self.entity_line(t)
            f.write(line)

        for e in annotation.relations:
            if e.property.get('negated') is not None:
                modifications.append('Negation '+e.property.get('id'))
            if self.has_trigger(e):
                line = self.event_line(e)
            else:
                line = self.relation_line(e)
            f.write(line)
        
        # write equive lines
        for rel, element_groups in annotation.property.items():
            if rel == 'Equiv':
                for eg in element_groups:
                    line = self.equiv_format.format(' '.join(eg))
                    f.write(line)

        for i,mod_event in enumerate(modifications):
            mod_id = 'M'+str(i+1)
            line = self.modification_line(mod_id, mod_event)
            f.write(line)

        f.close()


class A1A2Writer(BionlpWriter):
    def __init__(self):
        super(A1A2Writer, self).__init__()

    def write(self, a1path, a1file, a2path, a2file, annotation):
        triggerId = []

        entities = annotation['T']
        events = annotation['E']

        filepath = os.path.join(a2path, a2file)
        f = codecs.open(filepath, 'w+', 'utf-8')

        for k, e in events.iteritems():
            if e.triggerId not in triggerId:
                triggerId.append(e.triggerId)
                trigger = entities[e.triggerId]
                line = self.entity_line(trigger)
                f.write(line)

            line = self.event_line(e)
            if line is not None:
                f.write(line)

        f.close()

        filepath = os.path.join(a1path, a1file)
        f = codecs.open(filepath, 'w+', 'utf-8')

        for k, t in entities.iteritems():
            if t.id not in triggerId:
                line = self.entity_line(t)
                f.write(line)
        f.close()


class HtmlWriter:
    def __init(self):
        pass
