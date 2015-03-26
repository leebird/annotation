import json
from .utils import RandomGenerator


class Entity(object):
    # template to print the entity
    template = '{0}_{1}_{2}_{3}'

    class EntityIndexError(Exception):

        ZERO_INTERVAL = 0
        NEGATIVE_INTERVAL = 1
        NEGATIVE_INDEX = 2
        INEQUAL_LENGTH = 3
        UNMATCHED_TEXT = 4

        # exception messages
        MESSAGES = {
            ZERO_INTERVAL: 'Zero interval of the text span.',
            NEGATIVE_INTERVAL: 'Negative interval of the text span.',
            NEGATIVE_INDEX: 'Negative index of the text span.',
            INEQUAL_LENGTH: 'Interval length and text length are not equal.',
            UNMATCHED_TEXT: 'Document text and entity text are not matched.'
        }

        def __init__(self, value, msg=''):
            self.value = value
            self.msg = msg

        def __str__(self):
            if self.value in self.MESSAGES:
                return repr(self.MESSAGES[self.value] + ' msg: ' + self.msg)
            else:
                return repr('Unknown error')

    def __init__(self, category, start, end, text, id_=None, sanity_check=True):
        """A text span that refers to an entity

        :param category: entity category, e.g., gene
        :type category: str
        :param start: entity starting position in text
        :type start: int
        :param end: entity ending position in text
        :type end: int
        :param text: entity text
        :type text: str
        :return: None
        :rtype: None
        """
        self.category = category
        self.start = start
        self.end = end
        self.text = text
        self.id_ = id_
        self.property = {}
        self.sanity_check = sanity_check

        if self.sanity_check:
            # test if start/end is negative
            if self.start < 0 or self.end < 0:
                raise self.EntityIndexError(self.EntityIndexError.NEGATIVE_INDEX)

            # test if start equals end, which means the entity has 0 length
            if self.start == self.end:
                raise self.EntityIndexError(self.EntityIndexError.ZERO_INTERVAL)

            # test if start is larger than end, which is invalid for indices of text span
            if self.start > self.end:
                raise self.EntityIndexError(self.EntityIndexError.NEGATIVE_INTERVAL)

            if self.end - self.start != len(self.text):
                raise self.EntityIndexError(self.EntityIndexError.INEQUAL_LENGTH,
                                            ' %s %s %s' % (self.text, self.start, self.end))

    def __str__(self):
        return self.template.format(self.category, self.start, self.end, self.text)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        """ also compare property?
        """
        if isinstance(other, self.__class__):
            return (self.category == other.category and
                    self.start == other.start and
                    self.end == other.end and
                    self.text == other.text and
                    self.id_ == other.id_)
        else:
            return False

    def pack(self):
        packed = {
            'category': self.category,
            'start': self.start,
            'end': self.end,
            'text': self.text,
            'property': self.property
        }
        if self.id_ is not None:
            packed['id'] = self.id_

        return packed


class Relation(object):
    # template to print the relation
    template = '{category}'

    def __init__(self, category, arguments=None, id_=None):
        """ An relation structure with trigger and arguments
        :param category: relation type
        :type category: str
        :param arguments: a list of node objects, including the trigger if applicable
        :type arguments: list
        :return: None
        :rtype: None
        """
        self.category = category
        if arguments is None:
            self.arguments = []
        else:
            self.arguments = arguments
        self.id_ = id_
        self.property = {}

    def __str__(self):
        return self.template.format(category=self.category)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.category == other.category and
                    set(self.arguments) == set(other.arguments))
        else:
            return False

    def indent_print(self):
        print(Node('Root', self).indent_print())

    def add_argument(self, role, argument):
        """
        add new argument
        :param argument: an argument is an entity or relation
        :type argument: Entity | Relation
        :param role: semantic category, e.g., agent
        :type role: str
        :return: None
        :rtype: None
        """
        self.arguments.append(Node(role, argument))

    def pack(self):
        packed = {
            'category': self.category,
            'argument_set': [arg.pack() for arg in self.arguments],
            'property': self.property
        }
        if self.id_ is not None:
            packed['id'] = self.id_
        return packed


class Node(object):
    def __init__(self, role, value):
        """
        the argument must be an entity or another relation.
        :param category: the semantic category of the argument, e.g., agent
        :type category: str
        :param value: the actual entity or relation
        :type value: Entity | Relation
        :return: None
        :rtype: None
        """
        self.value = value
        self.role = role

        if (not self.is_leaf()) and (not self.is_tree()):
            raise TypeError('Value must be an entity or relation: ' + str(value))

    def is_leaf(self):
        return isinstance(self.value, Entity)

    def is_tree(self):
        return isinstance(self.value, Relation)

    def indent_print(self, indent=0):
        if self.is_leaf():
            return ' ' * indent + self.role + ': ' + str(self.value)
        else:
            return ' ' * indent + self.role + ': ' + str(self.value) + '\n' + \
                   '\n'.join([n.indent_print(indent + 2) for n in self.value.arguments])

    def pack(self):
        return self.role, self.value.id_


class Annotation(object):
    template = '{0} entities, {1} relations'
    random_trial_limit = 10

    def __init__(self, text_sanity_check=True):
        """
        annotation storing text, entities and relations
        :return: None
        :rtype: None
        """
        self.entities = []
        self.relations = []
        self.property = {}
        self.filepath = ''
        self.doc_id = ''
        self.text = ''
        self.id_map = {}
        self.text_sanity_check = text_sanity_check

    def __str__(self):
        return self.template.format(len(self.entities), len(self.relations))

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def make_argument(category, value):
        return Node(category, value)

    def random_id(self):
        for _ in range(self.random_trial_limit):
            rid = RandomGenerator.random_id()
            if rid not in self.id_map:
                return rid
        raise RuntimeError('random trial limit exceeded')

    def add_entity(self, category, start, end, text, id_=None, sanity_check=True):
        """
        add a new entity
        :param category: entity category, e.g., Gene
        :type category: str
        :param start: entity start position
        :type start: int
        :param end: entity end position
        :type end: int
        :param text: the associated text
        :type text: str
        :return: the created entity
        :rtype: Entity
        """
        if id_ is not None and id_ in self.id_map:
            raise KeyError('entity id already exists')
        if id_ is None:
            id_ = 'T' + self.random_id()

        if self.text_sanity_check and sanity_check:
            if self.text[start:end] != text:
                raise Entity.EntityIndexError(Entity.EntityIndexError.UNMATCHED_TEXT,
                                              self.filepath + ' ' + self.doc_id + ' ' 
                                              + text + ' | ' + self.text[start:end] +
                                              (' %s %s' % (start, end)))

        entity = Entity(category, start, end, text, id_, sanity_check)
        self.entities.append(entity)
        self.id_map[id_] = entity
        return entity

    def add_entities(self, entities):
        """
        add a list of new entities
        :param entities: a list of new entities
        :type entities: list
        :return: None
        :rtype: None
        """
        # TODO: how to deal with duplicate/overlap
        self.entities += entities

    def get_entity_category(self, category, complement=False):
        """
        get a list of entities of the same category
        :param category: entity category
        :type category: str
        :param complement: set True to get all other categories but the input one
        :type complement: bool
        :return: a list of entities of the input category
        :rtype: list
        """
        if complement:
            return [t for t in self.entities if t.category != category]
        else:
            return [t for t in self.entities if t.category == category]

    def get_entity_with_property(self, key, value):
        return [t for t in self.entities if value is not None and t.property.get(key) == value]

    def add_relation(self, category, arguments=None, id_=None):
        """
        add a new relation
        :param category: relation category, e.g., Regulation
        :type category: str
        :param trigger: the relation trigger
        :type trigger: Entity
        :param arguments: a list of relation arguments
        :type arguments: list
        :return: the created relation
        :rtype: Relation
        """

        if id_ is not None and id_ in self.id_map:
            raise KeyError('relation id already exists')
        if id_ is None:
            id_ = 'R' + self.random_id()

        relation = Relation(category, arguments, id_)
        self.relations.append(relation)
        self.id_map[id_] = relation
        return relation

    def get_relation_with_property(self, key, value):
        return [t for t in self.relations if t.property.has(key, value)]

    def get_relation_category(self, category, complement=False):
        """
        get a list of relations of the same category
        :param category: relation category
        :type category: str
        :param complement: set True to get all other categories but the input one
        :type complement: bool
        :return: a list of relations of the input category
        :rtype: list
        """
        if complement:
            return [e for e in self.relations if e.category != category]
        else:
            return [e for e in self.relations if e.category == category]

    def get_relation_no_trigger(self):
        triggered = []
        for relation in self.relations:
            trigger = [arg for arg in relation.arguments if arg.role == 'Trigger']
            if len(trigger) == 0:
                triggered.append(relation)
        return triggered

    def get_relation_with_trigger(self):
        triggered = []
        for relation in self.relations:
            trigger = [arg for arg in relation.arguments if arg.role == 'Trigger']
            if len(trigger) > 0:
                triggered.append(relation)
        return triggered

    def has_entity_annotation(self, category, start, end, text):
        """ check if same <category, start, end, text> entity annotation exists
        """
        for entity in self.entities:
            if category == entity.category and \
                            start == entity.start and \
                            end == entity.end and \
                            text == entity.text:
                return entity
        return None

    def has_relation_annotation(self, category, arguments):
        """ check if same <category, arguments> relation annotation exists
        """
        for relation in self.relations:
            if category == relation.category and arguments == relation.arguments:
                return relation
        return None

    def remove_entity(self, entity):
        self.entities.remove(entity)

    def remove_relation(self, relation):
        self.relations.remove(relation)

    def remove_included(self):
        """
        remove overlapping entities
        if two entities are overlapping with each other,
        remove the inner (included) one
        :return: None
        :rtype: None
        """
        entities = self.entities
        indices = []
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if e1 == e2:
                    continue
                '''
                e1: 0-5, e2: 4-6
                e1: 4-6, e2: 0-5
                e1: 0-5, e2: 1-3
                '''
                if e1.start < e2.end and e1.end > e2.start:
                    if e1.start > e2.start and e1.end < e2.end:
                        indices.append(i)
                    elif e1.start < e2.start and e1.end > e2.end:
                        indices.append(j)
        self.entities = [e for i, e in enumerate(self.entities) if i not in indices]

    def remove_overlap(self, keep=None, remove=None):
        """
        remove overlapping entities of some category
        :param keep: the entity category to keep. If it is None,
        then compare the to-be-removed category to all other categories.
        :type keep: str | None
        :param remove: the entity category to remove
        :type remove: str
        :return: None
        :rtype: None
        """

        if keep is None and remove is None:
            # removed any overlapped entities
            # TODO: this branch's result is not clear
            entities_keep = self.entities[:]
            entities_removed = self.entities[:]
        elif keep is None:
            # remove entities of removing type overlapped with any other kinds of entities
            entities_keep = self.get_entity_category(remove, complement=True)
            entities_removed = self.get_entity_category(remove)
        elif remove is None:
            # remove entities of any other kinds overlapped with the keeping type of entities
            entities_keep = self.get_entity_category(keep)
            entities_removed = self.get_entity_category(keep, complement=True)
        else:
            entities_keep = self.get_entity_category(keep)
            entities_removed = self.get_entity_category(remove)

        for k in entities_keep:
            for r in entities_removed:
                if k == r:
                    continue
                if k.start < r.end and k.end > r.start:
                    self.entities.remove(r)

    def pack(self):
        packed = {
            'doc_id': self.doc_id,
            'text': self.text,
            'property': self.property,
            'entity_set': [entity.pack() for entity in self.entities],
            'relation_set': [relation.pack() for relation in self.relations]
        }
        return packed

    def dumps(self, format='json'):
        """ dump annotation into json object
        :param annotation: the annotation to be dumped
        :type annotation: Annotation
        :param format: the format the annotation dumped to
        :type format: str
        :return: the dumped object
        :rtype: str
        """
        if format == 'json':
            return json.dumps(self.pack())

    @classmethod
    def loads(cls, data, format='json'):
        """load annotation from json object
        """
        annotation = Annotation()
        if format == 'json':
            packed = json.loads(data)
            annotation.text = packed.get('text')
            annotation.property = packed.get('property')
            annotation.doc_id = packed.get('doc_id')
            entities = packed.get('entity_set')
            relations = packed.get('relation_set')

            for entity in entities:
                sanity_check = entity.get('property').get('sanity_check')
                category = entity.get('category')
                start = entity.get('start')
                end = entity.get('end')
                text = entity.get('text')
                id_ = entity.get('id')

                if sanity_check:
                    ent = annotation.add_entity(category, start, end, text, id_)
                else:
                    ent = annotation.add_entity(category, start, end, text, id_, False)

            for relation in relations:
                category = relation.get('category')
                property = relation.get('property')

                id_ = relation.get('id')
                rel = annotation.add_relation(category, id_=id_)
                rel.property = property

            for relation in relations:
                arguments = relation.get('argument_set')
                id_ = relation.get('id')
                rel = annotation.id_map.get(id_)

                for arg in arguments:
                    arg_category = arg[0]
                    arg_id = arg[1]
                    actual_arg = annotation.id_map.get(arg_id)
                    rel.add_argument(arg_category, actual_arg)

        return annotation