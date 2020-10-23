

class Foo:
    def __init(self):
        pass

    def bar(self, x):
        return x+1

    def indir(self, r, v):
#        p = eval(r, globals(), __class__.__dict__)
        p = self.__class__.__dict__[r]
        print(p)
        return p(self, v)
