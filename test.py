import sys
import os

from .annotate import *
from .readers import *
from .writers import *
from .evaluation import *

import unittest


class TestEntity(unittest.TestCase):
    def setUp(self):
        self.entity = Entity('Gene', 0, 3, 'BAD')

    def test_category(self):
        self.assertEqual('Gene', self.entity.category)

    def test_start(self):
        self.assertEqual(0, self.entity.start)

    def test_end(self):
        self.assertEqual(3, self.entity.end)

    def test_text(self):
        self.assertEqual('BAD', self.entity.text)

    def test_text_length(self):
        self.assertTrue(len(self.entity.text) == self.entity.end - self.entity.start)

    def test_same_start_end(self):
        self.assertRaises(Entity.EntityIndexError, Entity, 'Gene', 0, 0, 'BAD')

    def test_negative_index(self):
        self.assertRaises(Entity.EntityIndexError, Entity, 'Gene', -1, 0, 'BAD')
        self.assertRaises(Entity.EntityIndexError, Entity, 'Gene', 0, -1, 'BAD')
        self.assertRaises(Entity.EntityIndexError, Entity, 'Gene', -1, -1, 'BAD')

    def test_negative_interval(self):
        self.assertRaises(Entity.EntityIndexError, Entity, 'Gene', 10, 5, 'BAD')

    def test_wrong_length(self):
        self.assertRaises(Entity.EntityIndexError, Entity, 'Gene', 10, 12, 'BAD')


class TestEvent(unittest.TestCase):
    def setUp(self):
        self.arguments = [Node('Agent', Entity('Gene', 0, 3, 'BAD')),
                          Node('Theme', Entity('Gene', 11, 14, 'BAD')),
                          Node('Trigger', Entity('Trigger', 4, 10, 'target'))]

    def test_simple_event(self):
        Relation('Target', self.arguments)

    def test_nested_event(self):
        event = Relation('Target', self.arguments)
        Relation('Regulation', [Node('Theme', event),
                                Node('Trigger', Entity('Trigger', 20, 28, 'regulate'))])


class TestNode(unittest.TestCase):
    def test_node_entity(self):
        Node('Theme', Entity('Gene', 0, 3, 'BAD'))

    def test_node_event(self):
        arguments = [Node('Agent', Entity('Gene', 0, 3, 'BAD')),
                     Node('Theme', Entity('Gene', 11, 14, 'BAD')),
                     Node('Trigger', Entity('Trigger', 4, 10, 'target'))]
        Node('Theme', Relation('Target', arguments)).indent_print()


    def test_node_nested_event(self):
        arguments = [Node('Agent', Entity('Gene', 0, 3, 'BAD')),
                     Node('Theme', Entity('Gene', 11, 14, 'BAD')),
                     Node('Trigger', Entity('Trigger', 4, 10, 'target'))]

        arguments = [Node('Theme', Relation('Target', arguments)),
                     Node('Trigger', Entity('Trigger', 20, 28, 'regulate'))]

        Node('Root', Relation('Regulation', arguments))

    def test_node_invalid_value(self):
        self.assertRaises(TypeError, Node, 123)


class TestAnnotation(unittest.TestCase):
    def setUp(self):
        self.annotation = Annotation()
        self.annotation.text = 'BAD target BAD cancer regulate'

    def test_add_entity(self):
        self.annotation.add_entity('Gene', 0, 3, 'BAD')

    def test_add_event(self):
        arguments = [Node('Agent', Entity('Gene', 0, 3, 'BAD')),
                     Node('Theme', Entity('Gene', 11, 14, 'BAD')),
                     Node('Trigger', Entity('Trigger', 4, 10, 'target'))]
        self.annotation.add_relation('Target', arguments)

    def test_get_entity_category(self):
        entity = self.annotation.add_entity('Gene', 0, 3, 'BAD')
        self.annotation.add_entity('Protein', 0, 3, 'BAD')
        self.annotation.add_entity('Disease', 15, 21, 'cancer')
        self.assertEqual(self.annotation.get_entity_category('Gene'), [entity])

    def test_get_entity_category_complement(self):
        self.annotation.add_entity('Gene', 0, 3, 'BAD')
        entity = self.annotation.add_entity('Protein', 0, 3, 'BAD')
        self.assertEqual(self.annotation.get_entity_category('Gene', True), [entity])

    def test_get_event_category(self):
        arguments = [Node('Agent', Entity('Gene', 0, 3, 'BAD')),
                     Node('Theme', Entity('Gene', 11, 14, 'BAD')),
                     Node('Trigger', Entity('Trigger', 4, 10, 'target'))]
        event = self.annotation.add_relation('Target', arguments)
        self.assertEqual(self.annotation.get_relation_category('Target'), [event])

    def test_get_event_category_complement(self):
        arguments = [Node('Agent', Entity('Gene', 0, 3, 'BAD')),
                     Node('Theme', Entity('Gene', 11, 14, 'BAD')),
                     Node('Trigger', Entity('Trigger', 4, 10, 'target'))]
        self.annotation.add_relation('Target', arguments)

        arguments = [Node('Agent', Entity('Gene', 0, 3, 'BAD')),
                     Node('Theme', Entity('Gene', 11, 14, 'BAD')),
                     Node('Trigger', Entity('Trigger', 22, 30, 'regulate'))]
        event = self.annotation.add_relation('Regulation', arguments)
        self.assertEqual(self.annotation.get_relation_category('Target', True), [event])

    def test_remove_included(self):
        entity = self.annotation.add_entity('Gene', 0, 3, 'BAD')
        self.annotation.add_entity('Protein', 1, 2, 'A')
        self.annotation.add_entity('Disease', 15, 21, 'cancer')
        self.annotation.remove_included()
        self.assertEqual(self.annotation.get_entity_category('Gene'), [entity])
        self.assertEqual(self.annotation.get_entity_category('Protein'), [])

    def test_remove_overlap(self):
        entity = self.annotation.add_entity('Gene', 0, 3, 'BAD')
        self.annotation.add_entity('Protein', 1, 4, 'AD ')
        disease_entity = self.annotation.add_entity('Disease', 15, 21, 'cancer')
        self.annotation.remove_overlap('Gene', 'Protein')
        self.assertEqual(self.annotation.get_entity_category('Gene'), [entity])
        self.assertEqual(self.annotation.get_entity_category('Protein'), [])

        self.annotation.remove_overlap('Gene')
        self.assertEqual(self.annotation.get_entity_category('Gene'), [entity])
        self.assertEqual(self.annotation.get_entity_category('Disease'), [disease_entity])


class TestReader(unittest.TestCase):
    def setUp(self):
        self.base_path = os.path.dirname(__file__)
        self.test_file = os.path.join(self.base_path, 'examples/17438130.ann')
        self.output_file = os.path.join(self.base_path, 'output/17438130.ann')
        self.rlims_file = os.path.join(self.base_path, 'examples/rlims.normal')
        self.verbose_file = os.path.join(self.base_path, 'examples/rlims.verbose')

    def test_annreader(self):
        parser = AnnParser()
        annotation = parser.parse_file(self.test_file)
        print(Node('Root', annotation.relations[0]).indent_print())

    def test_entity_handler(self):
        def handler(entity, fields):
            if len(fields) == 0:
                return
            gene_id = fields[0]
            entity.property['gid'] = gene_id

        parser = AnnParser(handler)
        annotation = parser.parse_file(self.test_file)
        print(annotation.get_entity_with_property('gid', '12345'))

    def test_rlims_reader(self):
        parser = RlimsParser()
        annotation = parser.parse_file(self.rlims_file)

    def test_rlims_verbose_reader(self):
        parser = RlimsVerboseReader()
        res = parser.parse_file(self.verbose_file)
        from pprint import pprint
        # pprint(res)
        annotations = parser.to_ann(res)
        print(annotations[0].dumps())
        # print(len(annotations), annotations.get('956179'))
        '''
        for pmid, annotation in annotations.items():
            # if pmid != '19035289':
            #     continue
            print(pmid)
            for relation in annotation.relations:
                relation.indent_print()
            # print(annotation)
        '''

class TestWriter(unittest.TestCase):
    def setUp(self):
        self.base_path = os.path.dirname(__file__)
        self.test_file = os.path.join(self.base_path, 'examples/17438130.ann')
        self.output_file = os.path.join(self.base_path, 'output/17438130.ann')
        self.rlims_file = os.path.join(self.base_path, 'examples/rlims.normal')


    def test_annwriter(self):
        parser = AnnParser()
        annotation = parser.parse_file(self.test_file)

        writer = AnnWriter()
        writer.write(self.output_file, annotation)


class TestEvaluation(unittest.TestCase):
    def setUp(self):
        parser = AnnParser()
        self.base_path = os.path.dirname(__file__)
        self.test_file = os.path.join(self.base_path, 'examples/17438130.ann')
        self.user_annotation = parser.parse_file(self.test_file)
        self.gold_annotation = parser.parse_file(self.test_file)

    def test_evaluation(self):
        Evaluation.evaluate({'17438130': self.user_annotation},
                            {'17438130': self.gold_annotation},
                            entity_category=['Gene'])


if __name__ == '__main__':
    unittest.main()
