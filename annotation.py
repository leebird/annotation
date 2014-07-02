class Entity:    
    def __init__(self,tid,typing,start,end,text):
        self.id = tid
        self.type = typing
        self.start = start
        self.end = end
        self.text = text

    def __str__(self):
        return '{}_{}_{}_{}_{}'.format(self.id,self.type,
                                       self.start,self.end,self.text)

    def __repr__(self):
        return self.__str__()

class Event:
    def __init__(self,tid,typing,triggerId,args):
        self.id = tid
        self.type = typing
        self.triggerId = triggerId
        self.args = args

    def __str__(self):
        return '{}_{}_{}_{}'.format(self.id,self.type,
                                    self.triggerId,self.args)

    def __repr__(self):
        return self.__str__()

        
class Relation:
    def __init__(self,rid,typing,arg1,arg2):
        self.id = rid
        self.type = typing
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return '{}_{}_{}_{}'.format(self.id,self.type,
                                    self.arg1,self.arg2)

    def __repr__(self):
        return self.__str__()
