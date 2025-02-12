

class Test:
    def __init__(self):
        self.test1 = "test1"
        self.test2 = "test2"
        self.dict1 = {"data": {1:"1", 2:"2", 3:"3"}}

objs = [Test(), Test(), Test()]
obj1 = objs[0]
obj1.test1 = "test10"
print(f"{obj1.test1 = }, {objs[0].test1 = }") 
obj2 = objs[1]
obj2.dict1["data"][1] = "10"
print(f"{obj2.dict1 = }, {objs[1].dict1 = }")       