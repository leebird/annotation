# -*- coding: utf-8 -*-
import sys
import itertools
from pprint import pprint as pp
from .annotate import *
from .utils import *


class Parser(object):
    def __init__(self):
        self.annotation = Annotation()

    def parse(self, text):
        raise NotImplementedError('Parser.parse()')

    def parse_file(self, filepath):
        raise NotImplementedError('Parser.parse_file()')

    def parse_folder(self, path, suffix):
        res = {}

        for root, _, files in os.walk(path):
            for f in files:
                if not f.endswith(suffix):
                    continue
                docid = f[:-len(suffix)]
                filepath = os.path.join(root, f)
                anno = self.parse_file(filepath)
                res[docid] = anno

        return res


class AnnParser(Parser):
    def __init__(self, entity_handler=None, event_handler=None, relation_handler=None):
        super(AnnParser, self).__init__()
        self.entity_handler = entity_handler
        self.event_handler = event_handler
        self.relation_handler = relation_handler

    def parse_entity(self, line, annotation):
        fields = line.split('\t')
        try:
            info = fields[1].split(' ')
            tid = fields[0]
            text = fields[2]
            category = info[0]
            start = int(info[1])
            end = int(info[2])
            entity = annotation.add_entity(category, start, end, text, tid)

            if self.entity_handler is not None:
                # handle appended information in entity line
                self.entity_handler(entity, fields[3:])

        except Entity.EntityIndexError as e:
            print(e)
            print('entity index error ' + line, file=sys.stderr)

    def parse_event(self, line, annotation):
        fields = line.split('\t')
        eid = fields[0]
        info = fields[1].split(' ')
        category = info[0].split(':')
        trigger_id = category[1]
        category_text = category[0]

        arguments = []
        for arg in info[1:]:
            arg_category, arg_entity_id = arg.split(':')
            entity = annotation.id_map.get(arg_entity_id)
            if entity is None:
                print('Can\'t find entity by id: ' + arg, file=sys.stderr)
                continue
            arguments.append(Node(arg_category, entity))

        trigger = annotation.id_map.get(trigger_id)
        if trigger is None:
            print('Can\'t find entity by id: ' + trigger_id, file=sys.stderr)
        arguments.append(Node('Trigger', trigger))

        event = annotation.add_relation(category_text, arguments, eid)

        if self.event_handler is not None:
            # handle appended information in entity line
            self.event_handler(event, fields[2:])

    def parse_relation(self, line, annotation):
        fields = line.split('\t')
        rid = fields[0]
        info = fields[1].split(' ')
        category_text = info[0]

        arguments = []
        for arg in info[1:]:
            arg_category, arg_entity_id = arg.split(':')
            entity = annotation.id_map.get(arg_entity_id)
            if entity is None:
                print('Can\'t find entity by id: ' + arg, file=sys.stderr)
                continue
            arguments.append(Node(arg_category, entity))

        relation = annotation.add_relation(category_text, arguments, rid)

        if self.relation_handler is not None:
            # handle appended information in entity line
            self.relation_handler(relation, fields[2:])

    def parse_equiv(self, line, annotation):
        """ parse equiv relation, e.g., Equiv T3 T4
        :param line: 
        :type line: 
        :param annotation: 
        :type annotation: 
        :return: None
        :rtype: None
        """
        tokens = line.split('\t')
        relation, arg1, arg2 = tokens[1].split(' ')
        values = annotation.property.get(relation)
        if values is not None:
            values.append((arg1, arg2))
        else:
            annotation.property.add(relation, [(arg1, arg2)])

    def parse_modification(self, line, annotation):
        tokens = line.split('\t')
        # mod_id, e.g., M1, M2, is not used now
        mod_id = tokens[0]
        modification, eid = tokens[1].split(' ')
        event = annotation.id_map.get(eid)
        if event is not None:
            event.property[modification] = True

    def parse_file(self, filepath):
        annotation = Annotation(text_sanity_check=False)
        annotation.filepath = filepath
        f = FileProcessor.open_file(filepath)

        if f is None:
            return annotation

        for line in f:
            line = line.strip('\r\n')
            if line.startswith('T'):
                self.parse_entity(line, annotation)

        # reset file pointer
        f.seek(0)

        for line in f:
            line = line.strip()
            if line.startswith('E'):
                self.parse_event(line, annotation)
            elif line.startswith('R'):
                self.parse_relation(line, annotation)
            elif line.startswith('*'):
                self.parse_equiv(line, annotation)
                # raise Exception('can not parse: '+line)
            elif line.startswith('M'):
                self.parse_modification(line, annotation)

        f.close()
        return annotation

    def parse_folder(self, path, suffix):
        res = {}

        for root, _, files in os.walk(path):
            for f in files:
                if not f.endswith(suffix):
                    continue
                docid = f[:-len(suffix)]
                filepath = os.path.join(root, f)
                anno = self.parse_file(filepath)
                res[docid] = anno

        return res


class SGMLParser(Parser):
    def __init__(self, mapping=None, tag_handler=None):
        """
        set mapping from tag name to entity type
        if <pro> means Protein, then a mapping from
        'pro' to 'Protein' should be set to have
        the entity typed 'Protein' in the output
        """
        super(SGMLParser, self).__init__()
        if mapping is not None:
            self.mapping = mapping
        else:
            self.mapping = {}

        self.tag_handler = tag_handler

    @staticmethod
    def get_open_bracket(text):
        return TextProcessor.pattern_open_bracket.finditer(text)

    @staticmethod
    def get_close_bracket(text):
        return TextProcessor.pattern_close_bracket.finditer(text)

    @staticmethod
    def is_close(tag):
        return tag.startswith('</')

    @staticmethod
    def get_text_snippet(text, tags):
        """
        get text snippets between each two tags
        entity text will be between an open-tag and a close-tag
        others are normal text
        """
        snippets = {}
        length = len(text)
        start = 0
        for tag in tags:
            end = tag.start()
            snippets[(start, end)] = text[start:end]
            start = tag.end()
        snippets[(start, length)] = text[start:length]
        return snippets

    @staticmethod
    def get_entity_by_index(snippets, start, end):
        """get entity by its tags' positions
        """
        entity_text, entity_start, entity_end = '', -1, -1
        missing_end = False
        current_pos = 0

        """
        sort indices from text start to text end
        """
        indices = sorted(snippets.keys(), key=lambda a: a[0])

        for pos in indices:
            text = snippets[pos]
            if pos[0] == start and pos[1] == end:
                entity_text += text
                entity_start = current_pos
                entity_end = current_pos + len(text)
                break
            elif pos[0] == start:
                entity_text += text
                entity_start = current_pos
                missing_end = True
            elif pos[1] == end:
                entity_text += text
                entity_end = current_pos + len(text)
                break
            elif missing_end:
                entity_text += text

            current_pos += len(text)

        return (entity_text, entity_start, entity_end)

    def parse_file(self, filepath):
        text = FileProcessor.read_file(filepath)
        anno = self.parse(text)
        return anno

    def parse(self, text):
        annotation = Annotation()
        open_tags = self.get_open_bracket(text)
        close_tags = self.get_close_bracket(text)
        tags = list(open_tags) + list(close_tags)
        ordered_tags = sorted(tags, key=lambda a: a.start())

        snippets = self.get_text_snippet(text, ordered_tags)

        openTagStack = []
        closeTagStack = []

        for tag in ordered_tags:
            tag_text = tag.group(1)
            tag_full = tag.group(0)
            if self.is_close(tag_full):
                start_tag = openTagStack.pop()
                start_tag_text = start_tag.group(1)

                # a tag handler to extract attrs or other stuff
                if self.tag_handler is not None:
                    tag_info = self.tag_handler(start_tag_text)
                    if 'tag' in tag_info:
                        start_tag_text = tag_info['tag']

                """
                open-tag and close-tag should have the same tag name
                if not skip this pair and continue
                if this happens, at least two entities are skip
                """
                if start_tag_text != tag_text:
                    print('different open and close tags', start_tag_text, tag_text, file=sys.stderr)
                    continue

                start = start_tag.end()
                end = tag.start()
                entity_text, start, end = self.get_entity_by_index(snippets, start, end)

                if self.tag_handler is not None and 'category' in tag_info:
                    category = tag_info['category']
                else:
                    try:
                        category = self.mapping[start_tag_text]
                    except KeyError:
                        category = start_tag_text

                annotation.add_entity(category, start, end, entity_text)
            else:
                openTagStack.append(tag)

        textpured = TextProcessor.remove_tags(text)
        annotation.text = textpured
        return annotation


class RlimsParser(Parser):
    def __init__(self):
        super(RlimsParser, self).__init__()

        # seperator used to divide result for each PMID
        self.separator = '{NP_1}PMID'

        # line starters used in result blocks
        self.hd_output = 'OUTPUT '
        self.hd_trigger = 'PTM ='
        self.hd_inducer = 'Inducer ='
        self.hd_kinase = 'Kinase ='
        self.hd_substrate = 'Substrate ='
        self.hd_site = 'Site ='
        self.hd_norm = 'NORM='
        self.hd_synonym = 'SYNONYM='

        # regex to extract information from lines in result block
        # {NP_1}PMID{/NP_1} - {CP_2}19035116{/CP_2}
        self.regex_pmid = re.compile(r'PMID\{/NP_1\}.*?\{.*?\}[^0-9]*?([0-9]*?)[^0-9]*?\{/.*?\}')

        # PTM = ({NP_P_12};phosphorylated)
        self.regex_trigger = re.compile(r'\(\{(.*?)\};(.*?)\)')

        # Substrate = ({NP_P_12}<p>p27</p>{/NP_P_12};-)
        self.regex_arg = re.compile(r'\{(.*?)\}(.*?)\{/(.*?)\}')

        # Site = ({NP_P_12}10{/NP_P_12};{NP_P_12}Ser{/NP_P_12};UNK)
        self.regex_amino = re.compile(r'\(\{(.*?)\}(.*?)\{/(.*?)\};')
        self.regex_site = re.compile(r';\{(.*?)\}(.*?)\{/(.*?)\};')
        self.regex_site_other = re.compile(r';\{(.*?)\}(.*?)\{/(.*?)\}\)$')

        # tagged phrase in text
        # {VP_act_71}To gain{/VP_act_71} {NP_72}further{/NP_72}
        self.regex_tagged = re.compile(r'(\{([^\{\}]*?)\})(.*?)(\{/(\2)\})')

        # status used when reading rlims result files
        # e.g., there may be two substrates, but the second one won't
        # start with hd_substrate
        self.status = 0
        self.mask = {
            11: 'kinase',
            12: 'substrate',
            13: 'site',
            14: 'trigger',
            15: 'inducer'
        }

    def split(self, text):
        """ split the whole text into result blocks
        """
        blocks = text.split(self.separator)
        blocks = [self.separator + b for b in blocks[1:]]
        return blocks

    def init_output(self):
        output = {'trigger': [],
                  'kinase': [],
                  'inducer': [],
                  'substrate': [],
                  'site': []}
        return output

    def _parse(self, blocks):
        res = {}
        for b in blocks:
            lines = b.split('\n')
            # empty line is used to seperate outputs & sentences
            if len(lines) == 0:
                continue

            match = self.regex_pmid.search(lines[0])
            if match:
                self.pmid = match.group(1)
            else:
                # self.pmid = 'unknown'
                print('unknown pmid ' + lines[0], file=sys.stderr)
                continue

            # if self.pmid != '6202705':
            # continue

            res[self.pmid] = self.parse_block(lines[1:])
            sens = res[self.pmid]['sentence']
            tag_index, abstract = self.index_tag(sens)
            res[self.pmid]['tag_indices'] = tag_index
            res[self.pmid]['text'] = abstract

        return res

    def parse_block(self, lines):
        res = {'sentence': [], 'output': [], 'norm': []}
        for l in lines:
            self.process_line(l, res)
        return res

    def process_line(self, l, res):
        if l.startswith(self.hd_output):
            self.status = 1
            output = self.init_output()
            res['output'].append(output)
        elif l.startswith(self.hd_norm):
            self.status = 2
            res['norm'].append([l])
        elif l.startswith(self.hd_synonym):
            self.status = 3
            res['norm'][-1].append(l)
        elif l.startswith(self.hd_kinase):
            self.status = 11
        elif l.startswith(self.hd_substrate):
            self.status = 12
        elif l.startswith(self.hd_site):
            self.status = 13
        elif l.startswith(self.hd_trigger):
            self.status = 14
        elif l.startswith(self.hd_inducer):
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

    def parse_line(self, line):
        res = None
        if self.status == 14:
            match = self.regex_trigger.search(line)
            if match:
                tag = match.group(1)
                text = match.group(2)
                text = TextProcessor.remove_tags(text)
                res = (tag, text)
        elif self.status == 13:
            tag = None
            site = None
            amino = None
            tag_other = None
            site_other = None
            
            # find site, e.g., 100
            match = self.regex_site.search(line)
            if match:
                tag = match.group(1)
                site = match.group(2)
                site = TextProcessor.remove_tags(site)
            
            # find amino, e.g., Ser
            match = self.regex_amino.search(line)
            if match:
                amino = match.group(2)
                
            # find other site, e.g., domains
            match = self.regex_site_other.search(line)
            if match:
                if site_other is None:
                    site_other = match.group(2)
                    site_other = TextProcessor.remove_tags(site_other)
                if tag_other is None:
                    tag_other = match.group(1)
            
            is_site_other = True if tag is None else False
            tag = tag_other if tag is None else tag
            site = site_other if site is None else site
            
            if tag is not None and site is not None:
                res = (tag, site, amino, is_site_other)

        elif self.status == 11 or self.status == 12 \
                or self.status == 15:
            match = self.regex_arg.search(line)
            if match:
                tag = match.group(1)
                text = match.group(2)
                text = TextProcessor.remove_tags(text)
                res = (tag, text)
        return res

    def parse_file(self, filepath):
        f = FileProcessor.open_file(filepath)
        text = f.read()
        f.close()
        blocks = self.split(text)
        pmid2tuples = self._parse(blocks)
        res = {'filepath': filepath, 'pmid2tuples': pmid2tuples}
        return res

    def index_tag(self, tagged_sentences):
        tag_index = {}
        sens = [TextProcessor.remove_bracket(s) for s in tagged_sentences]
        braced = ' '.join(sens)
        # remove_tags is too broad for bionex tags, see comments in utils.py
        # sens = [TextProcessor.remove_tags(s) for s in tagged_sentences]
        # text = ' '.join(sens)
        match = self.regex_tagged.search(braced)
        while match:
            # there is a potential bug here, now handled by backref in
            # regex_tagged. Because re.search starts from positon 0 in 
            # each search, when there is a {not_tag} {open_tag} {close_tag} 
            # string in text, it cound be matched as a open_tag, while the
            # actual open_tag is contained in the phrase
            match = self.regex_tagged.search(braced)
            tag = match.group(2)
            open_tag = match.group(1)
            close_tag = match.group(4)
            phrase = match.group(3)
            start = match.start(1)
            end = start + len(phrase)
            tag_index[tag] = (start, end, phrase)
            braced = braced.replace(open_tag, '')
            braced = braced.replace(close_tag, '')
            match = self.regex_tagged.search(braced)
        return tag_index, braced


class RlimsVerboseReader(RlimsParser):
    def __init__(self):
        super(RlimsVerboseReader, self).__init__()
        self.hd_method = '\tMethod='
        self.regex_method = re.compile(r'\[(.*?)\]')
        self.is_method = False
        self.regex_open_tag = re.compile(r'\{(.*?)\}')
        self.regex_close_tag = re.compile(r'\{/(.*?)\}')
        self.annotation = Annotation()

    def init_output(self):
        output = {'trigger': [],
                  'kinase': [],
                  'inducer': [],
                  'substrate': [],
                  'site': [],
                  'trigger_med': [],
                  'kinase_med': [],
                  'inducer_med': [],
                  'substrate_med': [],
                  'site_med': []}
        return output

    def parse_line(self, line):
        if self.is_method:
            # Method=rule:1.4.2.1.2 (substrate) for phrase=[{NP_P_12}<pp>Ser10</pp> 
            # -phosphorylated <p>p27</p> and <p>p27</p>{/NP_P_12}\r20..22|<p>p27</p>]
            match = self.regex_method.search(line)
            if match:
                med = match.group(1)
            else:
                return None

            tokens = med.split('\r\r')

            res = []
            for t in tokens:
                subtokens = t.split('\r')
                length = len(t)

                if length == 0:
                    return None

                phrase = TextProcessor.remove_tags(subtokens[0])
                match = self.regex_close_tag.search(subtokens[0])
                if match:
                    tag = match.group(1)
                else:
                    match = self.regex_open_tag.search(subtokens[0])
                    if match:
                        tag = match.group(1)
                    else:
                        print('NP Phrase not found ' + t.replace('\r', '\n'), file=sys.stderr)
                        continue

                for st in subtokens[1:]:
                    # 6..27|<Bppf><p>EGF</p> -dependent substrate</Bppf>
                    elements = st.split('|')
                    if len(elements) < 2:
                        continue
                    position = elements[0].split('..')
                    variances = elements[1:]
                    variances = [TextProcessor.remove_tags(v) for v in variances]
                    start = int(position[0])
                    end = int(position[1])
                    res.append((tag, phrase, start, end, variances))
                if len(res) == 0:
                    res.append((tag, phrase, -1, -1, [phrase]))
            return res
        else:
            return super(RlimsVerboseReader, self).parse_line(line)

    def process_line(self, l, res):
        if l.startswith(self.hd_method):
            self.is_method = True
            tokens = self.parse_line(l)
            needle = self.mask[self.status] + '_med'
            if tokens is not None:
                res['output'][-1][needle] += tokens
        elif l.startswith('\t'):
            pass
        else:
            self.is_method = False
            super(RlimsVerboseReader, self).process_line(l, res)

    @classmethod
    def to_ann(cls, parsed):
        annotations = {}

        filepath = parsed.get('filepath')
        pmid2tuples = parsed.get('pmid2tuples')
        for doc_id, v in pmid2tuples.items():

            # create new Annotation for each pmid
            annotation = Annotation()

            output = v['output']
            sentences = v['sentence']
            tag_index = v['tag_indices']

            # remote_tags is too broad for bionex tags
            # sentences = [TextProcessor.remove_tags(s) for s in sentences]
            # abstract = ' '.join(sentences)
            # print(abstract)
            abstract = v['text']
            # import pprint
            # pprint.pprint(tag_index)

            annotation.text = abstract
            annotation.filepath = filepath
            annotation.doc_id = doc_id

            annotation_set = set()
            for o in output:
                o = cls.fake_method(o, 'trigger')
                o = cls.fake_method(o, 'kinase')
                o = cls.fake_method(o, 'substrate')
                o = cls.fake_method(o, 'site')

                trigger = o['trigger']
                trigger_med = o['trigger_med']
                kinase = o['kinase']
                kinase_med = o['kinase_med']
                substrate = o['substrate']
                substrate_med = o['substrate_med']
                site = o['site']
                site_med = o['site_med']

                index_trigger = cls.reindex(trigger, trigger_med, tag_index)
                index_kinase = cls.reindex(kinase, kinase_med, tag_index)
                index_substrate = cls.reindex(substrate, substrate_med, tag_index)
                index_site_combine = cls.reindex(site, site_med, tag_index, is_site=True)
                index_site = [t for t in index_site_combine if not t[3]]
                index_site_other = [t for t in index_site_combine if t[3]]
                
                # print(trigger, trigger_med, index_trigger, sep="\n")
                # print()

                """
                indicesTri = self.reindex_method(triMed,tagIdx)
                indicesSub = self.reindex_method(subMed,tagIdx)
                indicesSite = self.reindex_method(siteMed,tagIdx)
                """

                # if no substrate, continue
                if len(index_substrate) == 0:
                    continue

                # ensure the annotation is unique
                trigger_id = tuple(index_trigger)
                kinase_id = tuple(index_kinase)
                substrate_id = tuple(index_substrate)
                site_id = tuple(index_site)
                site_other_id = tuple(index_site_other)
                if (trigger_id, kinase_id, substrate_id, site_id, site_other_id) in annotation_set:
                    continue
                annotation_set.add((trigger_id, kinase_id, substrate_id, site_id, site_other_id))

                triggers = cls.add_entities(index_trigger, 'Trigger', annotation)
                kinases = cls.add_entities(index_kinase, 'Protein', annotation)
                substrates = cls.add_entities(index_substrate, 'Protein', annotation)
                sites = cls.add_entities(index_site, 'Site', annotation)
                sites_other = cls.add_entities(index_site_other, 'SiteOther', annotation)
                
                args = {'Kinase': kinases, 'Substrate': substrates, 
                        'Site': sites, 'SiteOther':sites_other,
                        'Trigger': triggers}
                
                cls.add_relations(args, 'Phosphorylation', annotation)

            if len(annotation.relations) > 0:
                # only store it when it has relations
                annotations[doc_id] = annotation

        return annotations

    @classmethod
    def fake_method(cls, output, needle):
        """ add method lines if there is none
        """
        if len(output[needle + '_med']) == 0:
            sites = output[needle]
            fake = []
            for s in sites:
                fake.append((s[0], s[1], -1, -1, [s[1]]))
            output[needle + '_med'] = fake
        return output

    @classmethod
    def add_entities(cls, indices, entity_category, annotation):
        """ create and add new entities
        indices format:
        [(start,end,text),...]
        """
        res = []
        for i in indices:
            start = i[0]
            end = i[1]
            text = i[2]
            entity = annotation.has_entity_annotation(entity_category, start, end, text)
            if entity is None:
                entity = annotation.add_entity(entity_category, start, end, text)
            res.append(entity)
            """
            if not self.entities.has_key((start,end)):
                tid = 'T' + str(self.entityIdx)
                self.entityIdx += 1
                entity = Entity(tid,entityType,start,end,text)
                self.entities[(start,end)] = entity
            res.append(self.entities[(start,end)])
            """

        return res

    @classmethod
    def add_relations(cls, args, relation_category, annotation):
        relation = annotation.add_relation(relation_category)

        for role, entities in args.items():
            for entity in entities:
                relation.add_argument(role, entity)

    @classmethod
    def reindex(cls, annos, meds, tag_index, is_site=False):
        """ update position index for various situations
        1. position in method line is present
        2. position is -1
        3. the extracted span not matched with the argument
        """
        res = set()
        for anno, med in itertools.product(annos, meds):
            # check the phrase tags, they should be the same
            if anno[0] != med[0]:
                continue

            # check the annotations, they should be the same
            if not is_site and anno[1] != med[-1][-1]:
                continue

            # get information from annotation line and method line
            tag = anno[0]
            
            # if it's site other
            is_site_other = anno[3] if is_site else False
            
            """ get argument from method line, instead of annotation line
            this can fix the site case
            """
            # argument = a[1]

            argument = med[-1][0]

            phrase = med[1]
            in_start = med[2]
            in_end = med[3] + 1
            tag_start, tag_end, phrase = tag_index[tag]
            start, end = -1, -1

            if in_start == -1:
                """ search argument (trigger, kinase, substrate, site in result block) 
                in phrase (text in tag) if there is no position information 
                in the method line and it's not site.
                RLIMS-P normalize site so that we can simply search
                in the phrase. E.g., the phrase may be serine-100, but
                RLIMS-P normalized it to Ser-100
                """

                if not is_site:
                    in_start = phrase.find(argument)
                    if in_start > -1:
                        start = tag_start + in_start
                        end = start + len(argument)

                """ if it's not site or can't find the arugment, 
                take the phrase as argument
                """
                if in_start == -1:
                    start = tag_start
                    end = tag_end
                    argument = phrase

            else:
                """ recount position if there is position information
                in the method line
                """
                in_start, in_end = cls.recount(phrase, in_start, in_end)
                extracted = phrase[in_start:in_end]
                if extracted != argument:
                    """ search argument in the phrase if the position
                    is not matched with the argument
                    """
                    in_start = phrase.find(argument)
                    if in_start != -1:
                        start = tag_start + in_start
                        end = start + len(argument)
                    else:
                        # we really can't find the argument
                        continue
                else:
                    start = tag_start + in_start
                    end = tag_start + in_end
            
            if is_site:
                res.add((start, end, argument, is_site_other))
            else:
                res.add((start, end, argument))
                
        return res

    @classmethod
    def recount(cls, text, start, end):
        """ update index based on actual string, including space
        RLIMS-P verbose output file's original index excludes
        the space.
        """
        for i, c in enumerate(list(text)):
            if c == ' ' and i <= start:
                start += 1
            if c == ' ' and i < end:
                end += 1
        return start, end


class MedlineParser(Parser):
    mapHead = {'PMID-': 'pmid',
               'TI  -': 'title',
               'AB  -': 'abstract',
               'DP  -': 'date',
               'AU  -': 'author',
               'TA  -': 'journal',
               '     ': 'previous'}

    def __init__(self):
        super(MedlineParser, self).__init__()
        self.abstracts = {}

    def parse(self, text):
        lines = text.strip().split('\n')
        return self.iterparse(lines)

    def iterparse(self, iterator):
        currpmid = None
        needle = None
        self.abstracts = {}
        for line in iterator:
            line = line.rstrip()
            if len(line) == 0:
                pass

            head = line[:5]
            linetext = line[5:].strip()
            if len(linetext) == 0:
                continue

            if head in self.mapHead:
                if self.mapHead[head] == 'previous' and needle is not None:
                    if needle == 'abstract':
                        linetext = ' ' + linetext
                    self.abstracts[currpmid][needle] += linetext
                else:
                    needle = self.mapHead[head]
                    if needle == 'pmid':
                        currpmid = linetext
                        self.abstracts[currpmid] = {}
                    else:
                        self.abstracts[currpmid][needle] = linetext
            else:
                needle = None

        return self.abstracts
