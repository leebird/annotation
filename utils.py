__author__ = 'leebird'
import re
import codecs
import os
import random
import string


class TextProcessor(object):
    # in text there may be {not_tag} <not_tag>
    # may be a more strict pattern for bionex tags
    pattern_bracket = re.compile(r'<[^<>]*?>')
    pattern_brace = re.compile(r'\{[^{}]*?\}')
    pattern_open_bracket = re.compile(r'<([^<>/]*?)>')
    pattern_close_bracket = re.compile(r'</([^<>/]*?)>')

    def __init__(self):
        pass

    @classmethod
    def remove_bracket(cls, text):
        return re.sub(cls.pattern_bracket, '', text)

    @classmethod
    def remove_brace(cls, text):
        return re.sub(cls.pattern_brace, '', text)

    @classmethod
    def remove_tags(cls, text):
        return cls.remove_bracket(cls.remove_brace(text))


class FileProcessor(object):
    @staticmethod
    def read_file(filepath):
        if os.path.isfile(filepath):
            f = codecs.open(filepath, 'r', 'utf-8')
            text = f.read()
            f.close()
            return text

    @staticmethod
    def open_file(filepath):
        if os.path.isfile(filepath):
            f = codecs.open(filepath, 'r', 'utf-8')
            return f

    @staticmethod
    def write_file(filepath, content, flag='w'):
        f = codecs.open(filepath, flag, 'utf-8')
        f.write(content)
        f.close()


class RandomGenerator(object):
    @staticmethod
    def random_id(length=10):
        # http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
        # generate a random id
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))